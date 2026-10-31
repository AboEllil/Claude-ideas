"""TradingView indicator strategies vs our confluence strategy on halal stocks.

    python run_tv.py

Universe: top 20 of reports/top100_halal.csv (the request), plus ranks 21-100 as an
out-of-sample robustness check. Daily bars, decisions at close, trades next open,
5 bps per side. Long-only. Each stock is an equal sleeve of the portfolio (cash when flat).
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
from lab.single import run_strategy  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "tv"
START = "2010-01-01"
PERIODS = {"2010-2018": ("2010", "2018"), "2019-today": ("2019", "2100"), "2010-today": ("2010", "2100")}


def buy_hold(o, h, l, c):
    return np.ones(len(c))


STRATS = {
    "Buy & hold": (buy_hold, {}),
    "Lorentzian Classification (TV)": (tv.lorentzian, {}),
    "Lorentzian, fixed labels": (tv.lorentzian, {"fixed": True}),
    "ML Adaptive SuperTrend (TV)": (tv.adaptive_supertrend, {}),
    "Squeeze Momentum (TV)": (tv.squeeze_strategy, {}),
    "Smart Money Concepts (OB/FVG)": (tv.smc_strategy, {}),
    "CONFLUENCE (ours)": (tv.confluence, {"mkt": True}),
    "  ablation: no ML veto": (tv.confluence, {"mkt": True, "use_ml": False}),
    "  ablation: no squeeze": (tv.confluence, {"mkt": True, "use_squeeze": False}),
    "  ablation: no SMC": (tv.confluence, {"mkt": True, "use_smc": False}),
    "  ablation: no market filter": (tv.confluence, {"mkt": True, "use_market": False}),
}


def market_ok(spy):
    bad = (spy < spy.rolling(210).mean()) & (spy / spy.shift(252) - 1 < 0)
    return (~bad).astype(float)


def one_stock(args):
    tk, df, mkt = args
    out = {}
    for name, (fn, kw) in STRATS.items():
        kw = dict(kw)
        if kw.pop("mkt", False):
            kw["mkt_ok"] = mkt
        r, expo, trs = run_strategy(df, fn, START, **kw)
        out[name] = (r, expo, trs)
    return tk, out


def portfolio(results, name, tickers):
    R = pd.DataFrame({t: results[t][name][0] for t in tickers if t in results})
    return R.mean(axis=1).fillna(0)


def fmt(r):
    s = stats(r)
    return f"{s['cagr']:.1%} / {s['sharpe']:.2f} / {s['max_dd']:.0%}"


def table(results, tickers, title):
    lines = [f"### {title}", "", "| Strategy | " + " | ".join(PERIODS) + " | Time in market | Trades/stock/yr | Win rate |",
             "|---|---|---|---|---|---|---|"]
    years = (pd.Timestamp.now() - pd.Timestamp(START)).days / 365.25
    port = {}
    for name in STRATS:
        p = portfolio(results, name, tickers)
        port[name] = p
        expo = np.mean([results[t][name][1] for t in tickers if t in results])
        trs = [x for t in tickers if t in results for x in results[t][name][2]]
        n_tr = len(trs) / max(len(tickers), 1) / years
        win = f"{np.mean(np.array(trs) > 0):.0%}" if trs and name != "Buy & hold" else ""
        cells = " | ".join(fmt(p.loc[a:b]) for a, b in PERIODS.values())
        bold = "**" if name.startswith("CONF") else ""
        lines.append(f"| {bold}{name.strip()}{bold} | {cells} | {expo:.0%} | "
                     f"{'' if name == 'Buy & hold' else f'{n_tr:.1f}'} | {win} |")
    return "\n".join(lines), port


def chart(port, path, title):
    keep = ["Buy & hold", "Lorentzian Classification (TV)", "ML Adaptive SuperTrend (TV)", "Squeeze Momentum (TV)",
            "Smart Money Concepts (OB/FVG)", "CONFLUENCE (ours)"]
    colors = ["#9ca3af", "#a855f7", "#16a34a", "#f59e0b", "#ef4444", "#2563eb"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    for n, col in zip(keep, colors):
        r = port[n]
        lw = 2.4 if n.startswith("CONF") else 1.3
        a1.plot((1 + r).cumprod(), label=n, color=col, lw=lw)
        a2.plot(drawdown(r), color=col, lw=lw * 0.7)
    a1.set_yscale("log")
    a1.set_title(title, loc="left")
    a1.set_ylabel("Growth of $1")
    a2.set_ylabel("Drawdown")
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    for a in (a1, a2):
        a.grid(alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    a1.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ranking = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(ranking.index)
    top20, rest = tickers[:20], tickers[20:100]
    px = load_prices(tickers)
    mkt = market_ok(px["Close"]["SPY"].ffill())
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    results = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i, (tk, out) in enumerate(ex.map(one_stock, jobs), 1):
            results[tk] = out
            if i % 10 == 0:
                print(f"  {i}/{len(jobs)} stocks done", flush=True)

    t20, port20 = table(results, top20, "Top 20 halal stocks (the request)")
    t80, port80 = table(results, rest, "Ranks 21-100 (robustness check - not used in any design decision)")
    chart(port20, OUT / "top20.png", "Top 20 halal stocks: TradingView strategies vs ours (2010-today)")
    chart(port80, OUT / "rest80.png", "Ranks 21-100: same strategies, unseen stocks (2010-today)")

    per = ["| Stock | Buy & hold | Lorentzian | SuperTrend | Squeeze | SMC | CONFLUENCE |", "|---|---|---|---|---|---|---|"]
    cols = ["Buy & hold", "Lorentzian Classification (TV)", "ML Adaptive SuperTrend (TV)", "Squeeze Momentum (TV)",
            "Smart Money Concepts (OB/FVG)", "CONFLUENCE (ours)"]
    wins = 0
    for t in top20:
        sh = [stats(results[t][c][0])["sharpe"] for c in cols]
        wins += sh[-1] > sh[0]
        per.append(f"| {t} | " + " | ".join(f"{x:.2f}" for x in sh) + " |")

    md = f"""# TradingView indicators vs our strategy on halal stocks

Generated {pd.Timestamp.now():%Y-%m-%d}. Daily bars {START[:4]}-today, signals at the close, orders at the next
open, 5 bps per side, long-only (sell signals = go to cash). Each stock is an equal slice of the portfolio.
Cells: **CAGR / Sharpe / max drawdown**.

> **Big caveat:** the top 20 were picked partly *because* they went up a lot in the last 5 years
> (hindsight). Buy & hold on them looks spectacular and any strategy that spends time in cash will
> trail it in return. Judge strategies on Sharpe and drawdown, and on the ranks 21-100 check.

## Results
{t20}

![top20](top20.png)

{t80}

![rest80](rest80.png)

## Sharpe ratio per stock (top 20, 2010-today)
Confluence beat buy & hold on Sharpe in {wins} of 20 stocks.

""" + "\n".join(per) + """

## How each indicator was implemented
See the docstring of `lab/tv.py` for the exact rules. Defaults from the published scripts:
- **Lorentzian Classification**: 5 features (RSI14, WT 10/11, CCI20, ADX20, RSI9), 8 neighbours, 2000 bars,
  volatility + regime + kernel filters, 4-bar holding. "Fixed labels" pairs features with the *next* 4 bars
  instead of the published backward-looking (and inverted) label.
- **ML Adaptive SuperTrend**: ATR10, factor 3, k-means on the last 100 ATR values (75/50/25% initial centroids).
- **Squeeze Momentum**: BB 20 / KC 20 x1.5; enter on squeeze release with positive rising momentum, exit when
  momentum turns down.
- **Smart Money Concepts**: 10-bar swing pivots, BOS/CHoCH, order block = lowest candle between the broken
  swing high and the break, FVG with auto threshold; buy a retest of the zone in bullish structure and the
  discount half; stop on a close below the zone or a bearish structure break.
- **Confluence (ours)**: SuperTrend regime + any of {SuperTrend flip, squeeze release, OB/FVG retest} as entry,
  Lorentzian (fixed) as a veto, market bear filter, exit on SuperTrend flip or bearish CHoCH.
"""
    (OUT / "REPORT.md").write_text(md)
    print(t20)
    print()
    print(t80)
    print("\n".join(per))


if __name__ == "__main__":
    main()
