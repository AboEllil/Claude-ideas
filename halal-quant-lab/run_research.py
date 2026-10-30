"""Halal quant lab - full research pipeline.

    python run_research.py                     # default: 400 rotation + 400 swing configs
    python run_research.py --n-rotation 1000 --n-swing 1000 --seed 11
    python run_research.py --refresh           # re-download fundamentals and prices

Writes everything to reports/ (REPORT.md, charts, CSVs).
"""
import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab import engine  # noqa: E402
from lab.data import load_prices  # noqa: E402
from lab.metrics import deflated_sharpe, drawdown, stats, yearly  # noqa: E402
from lab.search import SWING_CONCEPTS, describe, run_many, walk_forward  # noqa: E402
from lab.signals import Features  # noqa: E402
from lab.universe import halal_tickers  # noqa: E402

OUT = Path(__file__).resolve().parent / "reports"
COLORS = {"Walk-forward strategy": "#2563eb", "SPY": "#9ca3af", "Halal universe (equal weight)": "#16a34a",
          "SPUS": "#f59e0b", "HLAL": "#a855f7", "QQQ": "#64748b"}


def pct(x):
    return "n/a" if x is None or not np.isfinite(x) else f"{x:.1%}"


def df_md(df, fmt):
    cols = [str(c) for c in df.columns]
    lines = ["| | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for i, row in df.iterrows():
        lines.append(f"| {i} | " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def stats_table(series: dict, trades=None):
    rows = []
    for name, r in series.items():
        s = stats(r)
        rows.append(f"| {name} | {r.index[0]:%Y-%m-%d} | {pct(s['cagr'])} | {pct(s['vol'])} | "
                    f"{s['sharpe']:.2f} | {s['sortino']:.2f} | {pct(s['max_dd'])} | {s['calmar']:.2f} |")
    head = ("| Series | From | CAGR | Volatility | Sharpe | Sortino | Max drawdown | Calmar |\n"
            "|---|---|---|---|---|---|---|---|\n")
    return head + "\n".join(rows)


def plot_equity(series: dict, path, title, log=True):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    for name, r in series.items():
        c = COLORS.get(name, None)
        lw = 2.2 if name == "Walk-forward strategy" else 1.2
        a1.plot((1 + r).cumprod(), label=name, color=c, lw=lw)
        a2.plot(drawdown(r), color=c, lw=lw * 0.8)
    if log:
        a1.set_yscale("log")
    a1.set_title(title, loc="left", fontsize=12)
    a1.set_ylabel("Growth of $1")
    a2.set_ylabel("Drawdown")
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    for a in (a1, a2):
        a.grid(alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    a1.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def concept_importance(cfgs, table):
    """Average full-period Sharpe of configs that USE a concept vs those that don't."""
    rows = []
    sh = table["sharpe"]
    for i_fam, keys, get in (
        ("rotation", ("w_mom", "w_short", "w_lowvol", "w_strength", "w_dip"), lambda c, k: c[k]),
        ("swing", SWING_CONCEPTS, lambda c, k: c["w"][k]),
    ):
        ids = [i for i, c in enumerate(cfgs) if c["family"] == i_fam]
        for k in keys:
            on = [i for i in ids if get(cfgs[i], k)]
            off = [i for i in ids if not get(cfgs[i], k)]
            if on and off:
                rows.append((i_fam, k.replace("w_", ""), sh[on].mean(), sh[off].mean()))
        for flag in ("regime",):
            on = [i for i in ids if cfgs[i][flag]]
            off = [i for i in ids if not cfgs[i][flag]]
            if on and off:
                rows.append((i_fam, "market regime filter", sh[on].mean(), sh[off].mean()))
    lines = ["| Family | Concept | Avg Sharpe WITH | Avg Sharpe WITHOUT | Difference |", "|---|---|---|---|---|"]
    for fam, k, a, b in sorted(rows, key=lambda x: -(x[2] - x[3])):
        lines.append(f"| {fam} | {k} | {a:.2f} | {b:.2f} | {a - b:+.2f} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-rotation", type=int, default=400)
    ap.add_argument("--n-swing", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cost-bps", type=float, default=5, help="cost per side incl. slippage, basis points")
    ap.add_argument("--wf-start", type=int, default=2012, help="first out-of-sample year")
    ap.add_argument("--train-years", type=int, default=5)
    ap.add_argument("--top-k", type=int, default=3, help="configs blended each year")
    ap.add_argument("--max-dd", type=float, default=-0.35, help="reject configs with worse train drawdown")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    cost = a.cost_bps / 1e4

    print("1/5 screening halal universe ...")
    tickers, screen = halal_tickers(refresh=a.refresh)
    screen.to_csv(OUT / "universe_screen.csv", index=False)
    print(f"    {len(tickers)} of {len(screen)} candidates pass")

    print("2/5 loading prices ...")
    px = load_prices(tickers, refresh=a.refresh)
    tickers = [t for t in tickers if px["Close"][t].notna().sum() > 300]
    F = Features(px, tickers)

    print(f"3/5 backtesting {a.n_rotation + a.n_swing} strategy configs ...")
    cfgs, R, table = run_many(F, a.n_rotation, a.n_swing, cost, a.seed)
    start = F.C.index[260]                         # skip indicator warm-up year
    R = R.loc[start:]
    table = pd.DataFrame([{"id": i, "family": cfgs[i]["family"], "desc": table.loc[i, "desc"], **stats(R[i])}
                          for i in R.columns]).set_index("id")
    table.sort_values("sharpe", ascending=False).to_csv(OUT / "all_configs.csv")

    print("4/5 walk-forward selection ...")
    oos, picks = walk_forward(R, a.wf_start, a.train_years, a.top_k, a.max_dd)
    picks["chosen_desc"] = picks["chosen"].apply(lambda ids: " || ".join(describe(cfgs[i]) for i in ids))
    picks.to_csv(OUT / "walkforward_choices.csv", index=False)

    # Same yearly picks, but every trade costs 3x more - does the edge survive?
    chosen_ids = sorted({i for ids in picks["chosen"] for i in ids})
    R3 = pd.DataFrame({i: engine.run(F, cfgs[i], cost * 3)[0] for i in chosen_ids}).loc[start:]
    oos3 = pd.concat([R3.loc[R3.index.year == row.year, row.chosen].mean(axis=1) for row in picks.itertuples()])

    print("5/5 benchmarks, current signals and report ...")
    rets = px["Close"].pct_change(fill_method=None)
    idx = oos.index
    ew = rets[tickers].mean(axis=1).fillna(0)
    bench = {"Walk-forward strategy": oos,
             "Halal universe (equal weight)": ew.loc[idx],
             "SPY": rets["SPY"].loc[idx].fillna(0),
             "QQQ": rets["QQQ"].loc[idx].fillna(0)}
    etf = {}
    for e in ("SPUS", "HLAL"):
        first = px["Close"][e].first_valid_index()
        if first is not None:
            etf[e] = rets[e].loc[first:].dropna()

    since = max(etf["SPUS"].index[1] if "SPUS" in etf else idx[0], idx[0])
    recent = {k: v.loc[since:] for k, v in bench.items()} | {k: v.loc[since:] for k, v in etf.items()}
    plot_equity(bench, OUT / "equity_walkforward.png", f"Out-of-sample walk-forward vs benchmarks, {idx[0].year}-today")
    plot_equity(recent, OUT / "equity_vs_halal_etfs.png", "Since halal ETFs exist", log=False)

    best_id = table["sharpe"].idxmax()
    dsr = deflated_sharpe(R[best_id], table["sharpe"].values)

    # Current recommendation: winners of the most recent training window.
    last = picks.iloc[-1]
    current = []
    for i in last.chosen:
        _, holdings, _ = engine.run(F, cfgs[i], cost)
        for t, w in holdings.sort_values(ascending=False).items():
            current.append({"config": i, "ticker": t, "weight_in_config": round(float(w), 4)})
    cur = pd.DataFrame(current)
    cur.to_csv(OUT / "current_signals.csv", index=False)
    blend = (cur.groupby("ticker")["weight_in_config"].sum() / len(last.chosen)).sort_values(ascending=False) \
        if len(cur) else pd.Series(dtype=float)
    json.dump({str(i): cfgs[i] for i in last.chosen}, open(OUT / "current_configs.json", "w"), indent=1)

    yr = pd.DataFrame({k: yearly(v) for k, v in bench.items()})
    yr["Strategy minus SPY"] = yr["Walk-forward strategy"] - yr["SPY"]
    fam = table.groupby("family")[["cagr", "sharpe", "max_dd"]].median()
    top = table.sort_values("sharpe", ascending=False).head(15)
    s_oos, s_spy, s_ew = stats(oos), stats(bench["SPY"]), stats(bench["Halal universe (equal weight)"])

    md = f"""# Halal Quant Lab - Research Report

Generated {pd.Timestamp.now():%Y-%m-%d}. Data: Yahoo Finance daily bars, {F.C.index[0]:%Y-%m-%d} to {F.C.index[-1]:%Y-%m-%d}.
Costs: {a.cost_bps:g} bps per side (commission + slippage). Signals at close, trades next day.

> **Not financial advice.** Backtests describe the past. The universe is today's halal list, which
> includes only survivors (stocks that did well enough to still be large today). That inflates every
> number in this report, including the equal-weight universe benchmark - so compare the strategy
> against **that** benchmark, not just SPY.

## 1. Universe
{len(tickers)} of {len(screen)} candidate US large caps pass the AAOIFI-style screen (business activity +
debt/market cap < 30% + cash/market cap < 30%). Full list and rejection reasons: `universe_screen.csv`.

## 2. The honest number: walk-forward out-of-sample
{a.n_rotation + a.n_swing} strategy configs were generated ({a.n_rotation} rotation, {a.n_swing} swing confluence), each
combining several concepts (trend, momentum, relative strength, RSI pullbacks, Bollinger dips, Donchian
breakouts, volume/OBV accumulation, low volatility, ADX trend strength, SPY/VIX market regime).
Each year from {a.wf_start}, the top {a.top_k} configs by Sharpe over the **previous {a.train_years} years only**
(rejecting train drawdowns worse than {a.max_dd:.0%}) are blended equally and traded for that year.

{stats_table(bench)}

![walk-forward](equity_walkforward.png)

**Verdict:** the walk-forward strategy returned {pct(s_oos['cagr'])}/yr with a {pct(s_oos['max_dd'])} max drawdown,
vs SPY {pct(s_spy['cagr'])}/yr ({pct(s_spy['max_dd'])}) and the equal-weight halal universe {pct(s_ew['cagr'])}/yr
({pct(s_ew['max_dd'])}). Sharpe: strategy {s_oos['sharpe']:.2f}, SPY {s_spy['sharpe']:.2f}, halal EW {s_ew['sharpe']:.2f}.

**Cost stress test** (same picks, 3x costs = {a.cost_bps * 3:g} bps/side): CAGR {pct(stats(oos3)['cagr'])},
Sharpe {stats(oos3)['sharpe']:.2f}.

### Year by year
{df_md(yr, pct)}

## 3. Versus real halal ETFs (since {since:%Y-%m})
{stats_table(recent)}

![vs halal ETFs](equity_vs_halal_etfs.png)

## 4. What the search learned - which concepts helped?
Average full-period Sharpe of configs that used each concept vs configs that did not:

{concept_importance(cfgs, table)}

Median of all configs by family:

{df_md(fam, lambda v: f'{v:.2f}')}

## 5. In-sample leaderboard (overfit - do not trust these numbers)
The best of {len(table)} configs over the whole history. Picking the max of many tries is exactly how
overfitting happens. **Deflated Sharpe Ratio of #1: {dsr:.2f}** (probability its Sharpe is skill, not luck,
after accounting for {len(table)} trials; >0.95 is convincing).

| # | Family | CAGR | Sharpe | Max DD | Description |
|---|---|---|---|---|---|
""" + "\n".join(f"| {i} | {r.family} | {pct(r.cagr)} | {r.sharpe:.2f} | {pct(r.max_dd)} | {r.desc} |"
                for i, r in top.iterrows()) + f"""

## 6. Current strategy (chosen with data up to {F.C.index[-1]:%Y-%m-%d})
Configs selected by the latest walk-forward window ({int(last.year) - a.train_years}-{int(last.year) - 1}):

""" + "\n".join(f"- `#{i}` {describe(cfgs[i])}" for i in last.chosen) + """

Blended current holdings (share of portfolio):

""" + ("\n".join(f"- {t}: {w:.1%}" for t, w in blend.items()) or "- cash (no positions / regime filter off)") + """

Full parameters: `current_configs.json`. Per-config holdings: `current_signals.csv`.

## 7. Files
- `all_configs.csv` - every config with full-period stats
- `walkforward_choices.csv` - which configs were picked each year and how they did out-of-sample
- `universe_screen.csv` - halal screen results
"""
    (OUT / "REPORT.md").write_text(md)
    print(f"done -> {OUT / 'REPORT.md'}")
    print(f"walk-forward: CAGR {pct(s_oos['cagr'])}  Sharpe {s_oos['sharpe']:.2f}  MaxDD {pct(s_oos['max_dd'])}")
    print(f"SPY:          CAGR {pct(s_spy['cagr'])}  Sharpe {s_spy['sharpe']:.2f}  MaxDD {pct(s_spy['max_dd'])}")
    print(f"halal EW:     CAGR {pct(s_ew['cagr'])}  Sharpe {s_ew['sharpe']:.2f}  MaxDD {pct(s_ew['max_dd'])}")


if __name__ == "__main__":
    main()
