"""Backtest the 'scan all EGX stocks for a fresh green arrow' method.

    python run_egx.py

Green arrow = ML Adaptive SuperTrend (AlgoAlpha) flips bullish on the daily chart.
Entries (decided at the close, held from the next close):
  E0 arrow only | E1 arrow + Squeeze momentum > 0 | E2 arrow + Lorentzian bullish | E3 arrow + both
Exits: X1 hold until the SuperTrend turns red | X2 sell after 3 days | X3 sell after 5 days
Portfolio: every qualifying signal is bought; capital split equally over open positions, max 10% each
(rest in cash). Liquidity filter: 20-day median traded value >= EGP 1 million on the signal day.
Costs: 0.25% per side (brokerage + EGX fees + stamp duty, approximate).
Results in EGP and in USD (converted with the daily USD/EGP rate).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import tv
from lab.egx import halal_egx
from lab.metrics import stats
from lab.universe import DATA

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "egx"
COST, CAP, MIN_VALUE = 0.0025, 0.10, 1_000_000
PERIODS = {"2016-2020": ("2016", "2020"), "2021-today": ("2021", "2100"), "2016-today": ("2016", "2100")}
ENTRIES = {"E0 arrow only": (False, False), "E1 arrow + squeeze": (True, False),
           "E2 arrow + Lorentzian": (False, True), "E3 arrow + both": (True, True)}
EXITS = {"X1 until red": None, "X2 3 days": 3, "X3 5 days": 5}


def clean(df):
    """Drop impossible daily moves (data errors): EGX price limits are well below +-50%."""
    r = df.Close.pct_change()
    bad = r.abs() > 0.5
    return df[~bad]


def stock_signals(args):
    tk, df = args
    df = clean(df.dropna(subset=["Open", "High", "Low", "Close"]))
    if len(df) < 300:
        return tk, None
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    st = tv.adaptive_supertrend(o, h, l, c)[0]
    _, mom = tv.squeeze(o, h, l, c)
    pred = tv.lorentzian(o, h, l, c)[1]
    value = (df.Close * df.Volume.fillna(0)).rolling(20).median().to_numpy()
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    out = {}
    for en, (use_sq, use_ml) in ENTRIES.items():
        ok = flip & (value >= MIN_VALUE)
        if use_sq:
            ok &= np.nan_to_num(mom) > 0
        if use_ml:
            ok &= pred > 0
        for ex, n in EXITS.items():
            pos = np.zeros(len(c))
            left = 0
            for t in range(len(c)):
                if pos[t - 1] if t else 0:
                    if n is None:
                        pos[t] = 1 if st[t] == 1 else 0
                    else:
                        left -= 1
                        pos[t] = 1 if left > 0 else 0
                if ok[t] and pos[t] == 0:
                    pos[t], left = 1, (n or 0)
            out[f"{en} | {ex}"] = pos
    out["_liquid"] = (value >= MIN_VALUE).astype(float)
    return tk, pd.DataFrame(out, index=df.index)


def simulate(on: pd.DataFrame, rets: pd.DataFrame, cap=CAP, cost=COST):
    """Equal weight over active names (max `cap` each), decided at close t, held from close t+1."""
    a = on.reindex(rets.index).fillna(0).to_numpy() > 0.5
    R = rets.fillna(0).to_numpy()
    T, N = R.shape
    w = np.zeros(N)
    eq, out, pending, prev = 1.0, np.ones(T), None, None
    n_trades = 0
    for t in range(1, T):
        pr = float(w @ R[t])
        eq *= 1 + pr
        if 1 + pr:
            w = w * (1 + R[t]) / (1 + pr)
        if pending is not None:
            eq *= 1 - cost * np.abs(pending - w).sum()
            w, pending = pending, None
        out[t] = eq
        cur = a[t]
        if prev is None or (cur != prev).any():
            if prev is not None:
                n_trades += int((cur & ~prev).sum())
            k = cur.sum()
            tgt = np.zeros(N)
            if k:
                tgt[cur] = min(1 / k, cap)
            pending, prev = tgt, cur.copy()
    return pd.Series(out, index=rets.index).pct_change().fillna(0), n_trades


def to_usd(r, fx):
    f = fx.reindex(r.index).ffill()
    return (1 + r) * (f.shift(1) / f) - 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    px = pd.read_pickle(DATA / "egx_prices.pkl")
    fx = px["Close"]["EGP=X"].ffill()
    tickers = [t + ".CA" for t in halal_egx() if t + ".CA" in px["Close"]]
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close", "Volume")})) for t in tickers]
    sig = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for tk, df in ex.map(stock_signals, jobs):
            if df is not None:
                sig[tk] = df
    tks = list(sig)
    close = pd.DataFrame({t: clean(pd.DataFrame({"Close": px["Close"][t]}).dropna()).Close for t in tks})
    rets = close.pct_change(fill_method=None).loc["2015-06-01":]
    liquid = pd.DataFrame({t: sig[t]["_liquid"] for t in tks})
    bh, _ = simulate(liquid, rets, cap=1.0)
    res = {"Buy & hold (equal weight, liquid halal EGX)": (bh, 0)}
    for name in [k for k in sig[tks[0]].columns if not k.startswith("_")]:
        on = pd.DataFrame({t: sig[t][name] for t in tks})
        res[name] = simulate(on, rets)
    years = (rets.index[-1] - pd.Timestamp("2016-01-01")).days / 365.25
    md = [f"# EGX: scanning all halal stocks for the green arrow (ML Adaptive SuperTrend)\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(tks)} halal EGX stocks on Yahoo, daily bars, "
          f"data to {rets.index[-1]:%Y-%m-%d}. Costs {COST:.2%} per side, max {CAP:.0%} per stock, "
          f"liquidity >= EGP {MIN_VALUE:,.0f}/day. Cells: CAGR / Sharpe / max drawdown.\n",
          "> 12 rule combinations were tested; the best one is partly luck. Look for rules that work in BOTH periods.\n",
          "| Strategy | EGP 2016-2020 | EGP 2021-today | EGP 2016-today | USD 2016-today | Trades/yr |",
          "|---|---|---|---|---|---|"]
    for n, (r, ntr) in res.items():
        r = r.loc["2016":]
        cells = [f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / {stats(r.loc[a:b])['max_dd']:.0%}"
                 for a, b in PERIODS.values()]
        u = stats(to_usd(r, fx))
        b = "**" if n.startswith("Buy") else ""
        md.append(f"| {b}{n}{b} | " + " | ".join(cells) + f" | {u['cagr']:.1%} / {u['sharpe']:.2f} / {u['max_dd']:.0%} | "
                  f"{'' if n.startswith('Buy') else f'{ntr / years:.0f}'} |")
    fxr = fx.loc["2016":]
    md += ["", f"USD/EGP went from {fxr.iloc[0]:.2f} to {fxr.iloc[-1]:.2f} over the period "
           f"({fxr.iloc[-1] / fxr.iloc[0] - 1:+.0%}), so EGP returns overstate real gains."]
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
