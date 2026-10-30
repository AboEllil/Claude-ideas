"""v2: institutional-style multi-factor portfolio (long-only, unlevered, halal).

Built from the research round (see reports/RESEARCH_NOTES.md):
  * Signals from published, out-of-sample-tested literature only - each one is
    winsorised, z-scored cross-sectionally (optionally within sector) and
    averaged into ONE composite score, instead of voting rules.
  * Diversified holdings (top ~30) with rank bands to cut turnover,
    inverse-volatility weights, name and sector caps.
  * Slow, partial risk overlays (never 100% cash on one signal).

Signals (all from daily OHLCV):
  mom        12-1 momentum scaled by 126d volatility      (Barroso & Santa-Clara 2015)
  resid      12-1 residual momentum vs SPY / resid vol    (Blitz, Huij & Martens 2011)
  high52     close / 52-week high                         (George & Hwang 2004)
  overnight  12-1 sum of overnight (close->open) returns  (Lou, Polk & Skouras 2019)
  lowvol     minus 252d volatility                        (Blitz & van Vliet 2007)
  ear        earnings-reaction drift: 3-day excess return
             around detected announcement days, last 60d  (Chan, Jegadeesh & Lakonishok 1996)
"""
import numpy as np
import pandas as pd

from . import indicators as ind

SIGNALS = ("mom", "resid", "high52", "overnight", "lowvol", "ear")


class FactorData:
    def __init__(self, px, tickers, sectors):
        raw_c = px["Close"][tickers]
        self.alive = raw_c.notna()
        self.C = raw_c.ffill()
        self.O = px["Open"][tickers].ffill()
        self.H = px["High"][tickers].ffill()
        self.V = px["Volume"][tickers]
        self.spy = px["Close"]["SPY"].ffill()
        self.r = raw_c.pct_change(fill_method=None)
        self.r_spy = self.spy.pct_change()
        self.sectors = pd.Series(sectors).reindex(tickers).fillna("Other")
        self._raw = {}

    def raw(self, name):
        if name not in self._raw:
            self._raw[name] = getattr(self, "_" + name)().where(self.alive)
        return self._raw[name]

    def _mom(self):
        return ind.momentum(self.C, 252, 21) / ind.realized_vol(self.C, 126)

    def _resid(self):
        cov = self.r.rolling(252, min_periods=200).cov(self.r_spy)
        beta = cov.div(self.r_spy.rolling(252, min_periods=200).var(), axis=0)
        e = self.r - beta.mul(self.r_spy, axis=0)
        s = e.rolling(231, min_periods=180).sum().shift(21)          # t-252 .. t-21
        return s / (e.rolling(252, min_periods=200).std() * np.sqrt(231))

    def _high52(self):
        return self.C / self.H.rolling(252, min_periods=200).max()

    def _overnight(self):
        on = np.log(self.O / self.C.shift(1))
        return on.rolling(231, min_periods=180).sum().shift(21)

    def _lowvol(self):
        return -ind.realized_vol(self.C, 252)

    def _ear(self):
        # Earnings days detected from price: big overnight gap on heavy volume.
        gap = (self.O / self.C.shift(1) - 1).abs()
        gap_sd = (self.r.rolling(60, min_periods=40).std()).shift(1)
        vol_x = self.V / self.V.rolling(50, min_periods=40).mean().shift(1)
        event = (gap > 2 * gap_sd) & (vol_x > 2.5)
        ex3 = (self.C.shift(-1) / self.C.shift(2) - 1).sub(self.spy.shift(-1) / self.spy.shift(2) - 1, axis=0)
        # The 3-day window ends at t+1, so the value is known only from t+1 on.
        val = ex3.where(event).shift(1)
        return val.ffill(limit=60).fillna(0)


def zscore(df, sectors=None, clip=0.05):
    lo, hi = df.quantile(clip, axis=1), df.quantile(1 - clip, axis=1)
    x = df.clip(lo, hi, axis=0)
    if sectors is not None:
        x = x - x.T.groupby(sectors).transform("mean").T
    return x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1), axis=0)


def composite(D: FactorData, weights: dict, sector_neutral=False):
    sec = D.sectors if sector_neutral else None
    parts = [w * zscore(D.raw(k), sec).fillna(0) for k, w in weights.items() if w]
    score = sum(parts) / sum(abs(w) for w in weights.values() if w)
    return score.where(D.alive & D.raw("lowvol").notna())


def cap_weights(w, sectors, name_cap, sector_cap, iters=50):
    """Water-fill weights under name and sector caps; leftover (if any) stays cash."""
    w = w / w.sum()
    for _ in range(iters):
        w = w.clip(upper=name_cap)
        sec_tot = w.groupby(sectors).sum()
        over = sec_tot[sec_tot > sector_cap + 1e-9]
        for s, tot in over.items():
            w[sectors == s] *= sector_cap / tot
        free = 1 - w.sum()
        room = (w < name_cap - 1e-9) & ~sectors.isin(over.index) & (w > 0)
        if free < 1e-6 or not room.any():
            break
        w[room] += free * w[room] / w[room].sum()
    return w


def rebalance_dates(index, offset_from_month_end=0):
    """Last trading day of each month, or `offset` trading days before it."""
    s = pd.Series(np.arange(len(index)), index=index)
    last = s.groupby(index.to_period("M")).max().to_numpy() - offset_from_month_end
    return set(last[last >= 0])


def build_targets(D: FactorData, cfg):
    score = composite(D, cfg["weights"], cfg.get("sector_neutral", False)).to_numpy()
    vol = ind.realized_vol(D.C, 63).to_numpy()
    tickers = D.C.columns
    T, N = score.shape
    targets, held = {}, np.zeros(N, bool)
    for t in sorted(rebalance_dates(D.C.index, cfg.get("month_end_offset", 0))):
        if t < 300:
            continue
        s = score[t]
        ok = ~np.isnan(s)
        if ok.sum() < cfg["top_n"]:
            continue
        rank = np.full(N, np.inf)
        order = np.where(ok)[0][np.argsort(-s[ok])]
        rank[order] = np.arange(len(order))
        n_ok = ok.sum()
        keep = held & (rank < cfg["sell_pct"] * n_ok)                 # band: keep until rank decays
        need = cfg["top_n"] - keep.sum()
        new = [j for j in order if not keep[j]][: max(need, 0)]
        sel = keep.copy()
        sel[new] = True
        held = sel
        idx = np.where(sel)[0]
        if cfg["weighting"] == "invvol":
            raw = 1 / np.nan_to_num(vol[t, idx], nan=np.nanmedian(vol[t]))
        else:
            raw = np.ones(len(idx))
        w = cap_weights(pd.Series(raw, index=tickers[idx]), D.sectors.iloc[idx],
                        cfg["name_cap"], cfg["sector_cap"])
        target = np.zeros(N)
        target[idx] = w.to_numpy()
        targets[t] = target
    return targets


def exposure_series(D: FactorData, cfg, ew_returns):
    """Daily equity exposure in [floor, 1] from slow trend + vol overlays (decided at close)."""
    idx = D.C.index
    expo = pd.Series(1.0, index=idx)
    if cfg.get("trend_overlay"):
        eq = (1 + ew_returns.fillna(0)).cumprod()
        bad = (eq < eq.rolling(210).mean()) & (eq / eq.shift(252) - 1 < 0)
        expo = expo.where(~bad, cfg.get("trend_floor", 0.5))
    if cfg.get("vol_target"):
        rv = ew_returns.rolling(42).std() * np.sqrt(252)
        expo = expo * (cfg["vol_target"] / rv).clip(upper=1.0).fillna(1.0)
    return expo.clip(lower=cfg.get("min_exposure", 0.3))


def simulate(D: FactorData, targets, exposure, cost=0.0005, check_every=5, band=0.1):
    """Weights decided at close t trade at close t+1; positions drift in between.
    Exposure changes are applied on rebalances, or every `check_every` days when the
    gap exceeds `band`, to avoid daily churn."""
    rets = np.nan_to_num(D.r.to_numpy(), nan=0.0)
    expo = exposure.to_numpy()
    T, N = rets.shape
    w, base, pending, eq = np.zeros(N), np.zeros(N), None, 1.0
    cur_expo = 1.0
    out, turnover = np.ones(T), 0.0
    for t in range(1, T):
        pr = float(w @ rets[t])
        eq *= 1 + pr
        if 1 + pr:
            w = w * (1 + rets[t]) / (1 + pr)
        if pending is not None:
            tc = np.abs(pending - w).sum()
            turnover += tc
            eq *= 1 - cost * tc
            w = pending
            pending = None
        out[t] = eq
        if t in targets:
            base = targets[t]
            cur_expo = expo[t]
            pending = base * cur_expo
        elif base.any() and t % check_every == 0 and abs(expo[t] - cur_expo) > band:
            # Rescale existing holdings toward the new exposure level.
            invested = w.sum()
            cur_expo = expo[t]
            pending = w / invested * cur_expo if invested > 0 else base * cur_expo
    r = pd.Series(out, index=D.C.index).pct_change().fillna(0)
    years = T / 252
    return r, turnover / years, pd.Series(w, index=D.C.columns)
