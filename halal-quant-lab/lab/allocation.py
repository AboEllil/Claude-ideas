"""Multi-asset halal allocation: overlays, static mixes and dual momentum.

Works on real, survivorship-free fund/ETF histories (Amana funds since 2005,
Shariah ETFs since 2019-2022), with proxies spliced in before an ETF existed.
Weights are decided at the close of day t and earn returns from day t+1.
"""
import numpy as np
import pandas as pd


def splice(r: pd.DataFrame, chain):
    """Daily returns of the first asset in `chain` that has data on each day."""
    out = r[chain[0]]
    for tk in chain[1:]:
        out = out.combine_first(r[tk])
    return out


def month_ends(index):
    s = pd.Series(np.arange(len(index)), index=index)
    return set(s.groupby(index.to_period("M")).max())


def simulate_weights(r: pd.DataFrame, targets: dict, cost=0.0005):
    """Drifting portfolio. `targets` maps day position -> weight Series (sum <= 1, rest is 0% cash)."""
    R = r.fillna(0).to_numpy()
    cols = list(r.columns)
    T = len(R)
    w = np.zeros(len(cols))
    eq, out, pending = 1.0, np.ones(T), None
    for t in range(1, T):
        pr = float(w @ R[t])
        eq *= 1 + pr
        if 1 + pr:
            w = w * (1 + R[t]) / (1 + pr)
        if pending is not None:
            eq *= 1 - cost * np.abs(pending - w).sum()
            w = pending
            pending = None
        out[t] = eq
        if t in targets:
            pending = targets[t].reindex(cols).fillna(0).to_numpy()
    return pd.Series(out, index=r.index).pct_change().fillna(0)


def overlay_exposure(r_equity: pd.Series, trend=True, vol_target=0.20, floor=0.5, min_expo=0.3):
    """Slow trend filter (below 10-month mean AND negative 12-month return -> floor)
    plus volatility target. Same rule as v2 `exposure_series`."""
    eq = (1 + r_equity.fillna(0)).cumprod()
    e = pd.Series(1.0, index=r_equity.index)
    if trend:
        bad = (eq < eq.rolling(210).mean()) & (eq / eq.shift(252) - 1 < 0)
        e = e.where(~bad, floor)
    if vol_target:
        rv = r_equity.rolling(42).std() * np.sqrt(252)
        e = e * (vol_target / rv).clip(upper=1).fillna(1)
    return e.clip(lower=min_expo)


def overlay_targets(r: pd.DataFrame, equity: str, defensive, expo: pd.Series, check_every=5, band=0.1):
    """Equity weight follows `expo` (updated weekly when it moves > band, and monthly);
    the freed weight goes to `defensive` (a column name) or stays as 0% cash (None)."""
    targets, cur = {}, None
    me = month_ends(r.index)
    for t in range(252, len(r)):
        x = expo.iloc[t]
        if cur is None or t in me or (t % check_every == 0 and abs(x - cur) > band):
            cur = x
            w = {equity: x}
            if defensive and not np.isnan(r[defensive].iloc[t]):
                w[defensive] = 1 - x
            targets[t] = pd.Series(w)
    return targets


def static_targets(r: pd.DataFrame, weights: dict, start=252):
    """Fixed weights rebalanced every January (assets without data yet -> 0% cash)."""
    targets = {}
    idx = r.index
    for t in sorted(month_ends(idx)):
        if t >= start and idx[t].month == 12:
            w = {k: v for k, v in weights.items() if not np.isnan(r[k].iloc[t])}
            targets[t] = pd.Series(w)
    return targets


def dual_momentum_targets(r: pd.DataFrame, risky, defensive, lookback=252, hold=2):
    """Monthly: rank available risky assets on trailing return, hold the top `hold`
    equally; any pick with a negative trailing return is replaced by `defensive`."""
    growth = (1 + r.fillna(0)).cumprod()
    targets = {}
    for t in sorted(month_ends(r.index)):
        if t < lookback + 21:
            continue
        avail = [a for a in risky if r[a].iloc[t - lookback:t].notna().all()]
        if not avail:
            continue
        mom = {a: growth[a].iloc[t] / growth[a].iloc[t - lookback] - 1 for a in avail}
        picks = sorted(mom, key=mom.get, reverse=True)[:hold]
        w = {}
        for a in picks:
            key = a if mom[a] > 0 else defensive
            if key and (key == a or not np.isnan(r[key].iloc[t])):
                w[key] = w.get(key, 0) + 1 / hold
        targets[t] = pd.Series(w)
    return targets
