"""Second attempt: put idle cash to work by rotating capital into stocks whose signal is ON.

    python run_tv_rotation.py   (after run_tv.py)

Diagnosis from run_tv.py: every indicator strategy kept each stock's 1/N sleeve in cash
whenever that stock had no signal (time in market 3-57%), so portfolio returns were
small even when the signals were decent. Pre-declared fix (no parameters tuned):
  * Each day, hold equal weight in every stock whose signal is ON, capped at 10% per
    stock (so <10 active names leaves the rest in cash). Rebalance only when the set of
    active names changes. Decisions at close t, trades at close t+1, 5 bps per side.
Signals compared: ML Adaptive SuperTrend (TV) and our CONFLUENCE, plus buy & hold.
NOTE: this design was chosen AFTER seeing run_tv.py results on both universes, so the
ranks 21-100 check is no longer fully unseen; the 2010-2018 / 2019-today split still applies.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab import tv  # noqa: E402
from lab.data import load_prices  # noqa: E402
from lab.metrics import drawdown, stats  # noqa: E402
from run_tv import PERIODS, START, market_ok  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "tv"
CAP = 0.10
COST = 0.0005


def signals(args):
    tk, df, mkt = args
    df = df.dropna()
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    m = mkt.reindex(df.index).ffill().to_numpy(float)
    st = tv.adaptive_supertrend(o, h, l, c)[0]
    cf = tv.confluence(o, h, l, c, mkt_ok=m)[0]
    cf_nm = tv.confluence(o, h, l, c, mkt_ok=m, use_market=False)[0]
    return tk, pd.DataFrame({"st": st, "cf": cf, "cf_nm": cf_nm}, index=df.index)


def rotate(on: pd.DataFrame, rets: pd.DataFrame, cap=CAP):
    """Equal weight across active names (capped), held with drift until the active set changes."""
    on = on.reindex(rets.index).fillna(0).to_numpy() > 0.5
    R = rets.fillna(0).to_numpy()
    T, N = R.shape
    w = np.zeros(N)
    eq, out = 1.0, np.ones(T)
    pending, prev_set = None, None
    for t in range(1, T):
        pr = float(w @ R[t])
        eq *= 1 + pr
        if 1 + pr:
            w = w * (1 + R[t]) / (1 + pr)
        if pending is not None:
            eq *= 1 - COST * np.abs(pending - w).sum()
            w, pending = pending, None
        out[t] = eq
        cur = on[t]
        if prev_set is None or (cur != prev_set).any():
            k = cur.sum()
            tgt = np.zeros(N)
            if k:
                tgt[cur] = min(1 / k, cap)
            pending, prev_set = tgt, cur.copy()
    return pd.Series(out, index=rets.index).pct_change().fillna(0)


def main():
    ranking = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(ranking.index)[:100]
    px = load_prices(tickers)
    mkt = market_ok(px["Close"]["SPY"].ffill())
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    sig = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for tk, df in ex.map(signals, jobs):
            sig[tk] = df
    rets_all = px["Close"][tickers].pct_change(fill_method=None)

    md = ["", "## Second attempt: rotate capital into active signals (no idle sleeves)",
          f"Equal weight across all stocks whose signal is ON, max {CAP:.0%} per stock, rest in cash. "
          "Rules fixed before running; designed after seeing the first results (see `run_tv_rotation.py`).", ""]
    for label, tks in (("Top 20", tickers[:20]), ("Ranks 21-100", tickers[20:100])):
        rets = rets_all[tks].loc["2009-01-01":]
        series = {"Buy & hold (equal weight)": rotate(rets.notna().astype(float), rets, cap=1.0)}
        for key, name in (("st", "SuperTrend rotation"), ("cf", "CONFLUENCE rotation"),
                          ("cf_nm", "CONFLUENCE rotation, no market filter")):
            on = pd.DataFrame({t: sig[t][key] for t in tks})
            series[name] = rotate(on, rets)
        series = {k: v.loc[START:] for k, v in series.items()}
        md += [f"### {label}", "", "| Strategy | " + " | ".join(PERIODS) + " | Avg invested |", "|---|---|---|---|---|"]
        for n, r in series.items():
            cells = " | ".join(f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / "
                               f"{stats(r.loc[a:b])['max_dd']:.0%}" for a, b in PERIODS.values())
            if n.startswith("Buy"):
                inv = 1.0
            else:
                key = {"SuperTrend rotation": "st", "CONFLUENCE rotation": "cf"}.get(n, "cf_nm")
                on = pd.DataFrame({t: sig[t][key] for t in tks}).reindex(r.index).fillna(0)
                inv = float(np.minimum(on.sum(axis=1) * CAP, 1).mean())
            md.append(f"| {n} | {cells} | {inv:.0%} |")
        md.append("")
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
        for (n, r), col in zip(series.items(), ["#9ca3af", "#16a34a", "#2563eb", "#93c5fd"]):
            a1.plot((1 + r).cumprod(), label=n, color=col, lw=2 if "CONF" in n and "no" not in n else 1.3)
            a2.plot(drawdown(r), color=col, lw=1)
        a1.set_yscale("log")
        a1.set_title(f"{label}: capital rotation into active signals, 2010-today", loc="left")
        a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        for a in (a1, a2):
            a.grid(alpha=0.25)
            a.spines[["top", "right"]].set_visible(False)
        a1.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fname = "rotation_top20.png" if label == "Top 20" else "rotation_rest80.png"
        fig.savefig(OUT / fname, dpi=130)
        plt.close(fig)
        md.append(f"![{label}]({fname})\n")
    with open(OUT / "REPORT.md", "a") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
