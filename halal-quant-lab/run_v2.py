"""v2 research: institutional-style multi-factor portfolio with pre-registered tests.

    python run_v2.py

Discipline (from the research round, see reports/RESEARCH_NOTES.md):
  * A small, fixed list of variants decided BEFORE looking at results
    (published parameters, no random search).
  * Selection uses 2006-2018 only. 2019-today is a true holdout, reported once.
  * The benchmark that matters is the equal-weight halal universe (same stock
    pool, monthly rebalanced, same costs) - it carries the same survivorship bias.
  * Sharpe difference vs that benchmark gets a block-bootstrap confidence interval.
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab.data import load_prices  # noqa: E402
from lab.factor import FactorData, build_targets, exposure_series, rebalance_dates, simulate  # noqa: E402
from lab.metrics import deflated_sharpe, drawdown, stats, yearly  # noqa: E402
from lab.universe import DATA, halal_tickers  # noqa: E402

OUT = Path(__file__).resolve().parent / "reports" / "v2"
START, SPLIT = "2006-03-01", "2019-01-01"
COST = 0.0005

CORE = dict(mom=1, resid=1, high52=1, lowvol=1)
FULL = dict(CORE, overnight=1, ear=1)
BASE = dict(top_n=30, sell_pct=0.4, weighting="invvol", name_cap=0.06, sector_cap=0.30)

VARIANTS = {
    "A  momentum only, top10 equal (v1-style)": dict(BASE, weights=dict(mom=1), top_n=10, sell_pct=0.08,
                                                     weighting="equal", name_cap=0.2, sector_cap=1.0),
    "B  core: mom+resid+52wk+lowvol": dict(BASE, weights=CORE),
    "C  core + overnight": dict(BASE, weights=dict(CORE, overnight=1)),
    "D  core + earnings drift": dict(BASE, weights=dict(CORE, ear=1)),
    "E  full (core + overnight + earnings)": dict(BASE, weights=FULL),
    "F  full, sector-neutral scores": dict(BASE, weights=FULL, sector_neutral=True),
    "G  full, buy 4 days before month-end": dict(BASE, weights=FULL, month_end_offset=4),
    "H  full + slow trend overlay (50% floor)": dict(BASE, weights=FULL, trend_overlay=True),
    "I  full + vol target 15%": dict(BASE, weights=FULL, vol_target=0.15),
    "J  full + trend + vol target": dict(BASE, weights=FULL, trend_overlay=True, vol_target=0.15),
    "K  full, top 20": dict(BASE, weights=FULL, top_n=20, sell_pct=0.3),
    "L  full, top 40": dict(BASE, weights=FULL, top_n=40, sell_pct=0.5),
    "M  full, equal weight": dict(BASE, weights=FULL, weighting="equal"),
    "N  momentum family only (mom+resid+52wk+overnight)": dict(BASE, weights=dict(mom=1, resid=1, high52=1, overnight=1)),
}


def boot_sharpe_diff(a, b, n=2000, block=21, seed=0):
    """95% CI of Sharpe(a) - Sharpe(b) with a stationary-ish block bootstrap."""
    rng = np.random.default_rng(seed)
    x, y = a.to_numpy(), b.to_numpy()
    T = len(x)
    out = []
    for _ in range(n):
        starts = rng.integers(0, T - block, T // block + 1)
        ix = (starts[:, None] + np.arange(block)).ravel()[:T]
        sa = x[ix].mean() / x[ix].std() * np.sqrt(252)
        sb = y[ix].mean() / y[ix].std() * np.sqrt(252)
        out.append(sa - sb)
    return np.percentile(out, [2.5, 97.5])


def ew_benchmark(D):
    idx = D.C.index
    targets = {}
    for t in rebalance_dates(idx):
        if t < 300:
            continue
        ok = D.alive.iloc[t].to_numpy() & D.raw("lowvol").iloc[t].notna().to_numpy()
        w = np.zeros(len(ok))
        w[ok] = 1 / ok.sum()
        targets[t] = w
    r, _, _ = simulate(D, targets, pd.Series(1.0, index=idx), COST)
    return r


def pct(x):
    return f"{x:.1%}"


def row(name, r, to=None):
    s = stats(r)
    return (f"| {name} | {pct(s['cagr'])} | {s['sharpe']:.2f} | {pct(s['max_dd'])} | {pct(s['vol'])} |"
            + (f" {to:.1f}x |" if to is not None else " |"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tickers, _ = halal_tickers()
    px = load_prices(tickers)
    tickers = [t for t in tickers if px["Close"][t].notna().sum() > 300]
    sectors = {k: v["sector"] for k, v in json.loads((DATA / "fundamentals.json").read_text()).items()}
    D = FactorData(px, tickers, sectors)
    ew_daily = D.r.mean(axis=1)

    print("benchmarks ...")
    ew = ew_benchmark(D).loc[START:]
    spy = px["Close"]["SPY"].pct_change().loc[START:].fillna(0)

    results, turnover, holdings = {}, {}, {}
    for name, cfg in VARIANTS.items():
        print(" ", name)
        targets = build_targets(D, cfg)
        r, to, w = simulate(D, targets, exposure_series(D, cfg, ew_daily), COST)
        results[name], turnover[name], holdings[name] = r.loc[START:], to, w

    periods = {"2006-2011 (GFC)": ("2006", "2011"), "2012-2018": ("2012", "2018"),
               "2019-today HOLDOUT": ("2019", "2100")}
    lines = []
    for name, r in list(results.items()) + [("EW halal universe", ew), ("SPY", spy)]:
        cells = []
        for a, b in periods.values():
            s = stats(r.loc[a:b])
            cells.append(f"{pct(s['cagr'])} / {s['sharpe']:.2f} / {pct(s['max_dd'])}")
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {turnover.get(name, 0):.1f}x |")

    # Selection on 2006-2018 only: best Sharpe; ties broken by drawdown.
    train = {n: stats(r.loc[:"2018"]) for n, r in results.items()}
    chosen = max(train, key=lambda n: (round(train[n]["sharpe"], 2), train[n]["max_dd"]))
    rc = results[chosen]
    hold = rc.loc[SPLIT:]
    ci_full = boot_sharpe_diff(rc, ew.reindex(rc.index).fillna(0))
    ci_hold = boot_sharpe_diff(hold, ew.loc[SPLIT:])
    all_sh = [stats(r.loc[:"2018"])["sharpe"] for r in results.values()]
    dsr = deflated_sharpe(rc.loc[:"2018"], all_sh)

    # Ablation: what each signal adds on top of the others (full model minus one).
    abl = []
    full_cfg = VARIANTS["E  full (core + overnight + earnings)"]
    base_s = {k: stats(results["E  full (core + overnight + earnings)"].loc[a:b])["sharpe"]
              for k, (a, b) in periods.items()}
    for sig in FULL:
        cfg = dict(full_cfg, weights={k: v for k, v in FULL.items() if k != sig})
        r, _, _ = simulate(D, build_targets(D, cfg), exposure_series(D, cfg, ew_daily), COST)
        r = r.loc[START:]
        diffs = [base_s[k] - stats(r.loc[a:b])["sharpe"] for k, (a, b) in periods.items()]
        abl.append(f"| {sig} | " + " | ".join(f"{d:+.2f}" for d in diffs) + " |")

    # Charts
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    series = {f"v2: {chosen.split('  ')[1]}": (rc, "#2563eb", 2.2), "EW halal universe": (ew, "#16a34a", 1.2),
              "SPY": (spy, "#9ca3af", 1.2)}
    for lab_, (r, c, lw) in series.items():
        a1.plot((1 + r).cumprod(), label=lab_, color=c, lw=lw)
        a2.plot(drawdown(r), color=c, lw=lw * 0.8)
    for a in (a1, a2):
        a.axvline(pd.Timestamp(SPLIT), color="#ef4444", ls="--", lw=1)
        a.grid(alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    a1.text(pd.Timestamp(SPLIT), a1.get_ylim()[1] * 0.6, "  holdout starts", color="#ef4444", fontsize=9)
    a1.set_yscale("log")
    a1.set_ylabel("Growth of $1")
    a1.set_title("v2 multi-factor vs benchmarks (selected on 2006-2018, holdout after the red line)", loc="left")
    a1.legend(frameon=False, fontsize=9)
    a2.set_ylabel("Drawdown")
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    fig.tight_layout()
    fig.savefig(OUT / "equity_v2.png", dpi=130)
    plt.close(fig)

    yr = pd.DataFrame({"v2": yearly(rc), "EW halal": yearly(ew), "SPY": yearly(spy)})
    w = holdings[chosen]
    w = w[w > 0].sort_values(ascending=False)
    pd.DataFrame({"weight": w.round(4), "sector": D.sectors[w.index]}).to_csv(OUT / "current_holdings.csv")
    json.dump(VARIANTS[chosen], open(OUT / "chosen_config.json", "w"), indent=1)

    s_c, s_e, s_s = stats(hold), stats(ew.loc[SPLIT:]), stats(spy.loc[SPLIT:])
    md = f"""# v2 Multi-Factor Results

Generated {pd.Timestamp.now():%Y-%m-%d}. {len(tickers)} halal stocks, daily data to {D.C.index[-1]:%Y-%m-%d},
{COST * 1e4:g} bps/side costs, signals at close, trades next close.

## Selected strategy: {chosen}
Chosen **only** on 2006-2018 Sharpe out of {len(VARIANTS)} pre-registered variants
(deflated Sharpe on that period: {dsr:.2f}). 2019-today was not used for any decision.

### Holdout 2019-today (never seen during selection)
| Series | CAGR | Sharpe | Max DD | Volatility | Turnover/yr |
|---|---|---|---|---|---|
{row('v2 selected', hold, turnover[chosen])}
{row('EW halal universe', ew.loc[SPLIT:])}
{row('SPY', spy.loc[SPLIT:])}

Sharpe difference vs EW halal universe, 95% bootstrap CI: holdout [{ci_hold[0]:+.2f}, {ci_hold[1]:+.2f}],
full period [{ci_full[0]:+.2f}, {ci_full[1]:+.2f}]. If the interval contains 0, the edge is not statistically proven.

### Full period {START[:4]}-today
| Series | CAGR | Sharpe | Max DD | Volatility | Turnover/yr |
|---|---|---|---|---|---|
{row('v2 selected', rc, turnover[chosen])}
{row('EW halal universe', ew)}
{row('SPY', spy)}

![equity](equity_v2.png)

## All variants (CAGR / Sharpe / Max DD per period)
| Variant | {' | '.join(periods)} | Turnover/yr |
|---|---|---|---|---|
""" + "\n".join(lines) + f"""

## Ablation: Sharpe lost when removing one signal from the full model
Positive = the signal helps. A signal earns its place only if it helps in most periods.

| Signal removed | {' | '.join(periods)} |
|---|---|---|---|
""" + "\n".join(abl) + """

## Year by year (selected strategy)
| Year | v2 | EW halal | SPY |
|---|---|---|---|
""" + "\n".join(f"| {y} | {pct(a)} | {pct(b)} | {pct(c)} |" for y, (a, b, c) in yr.iterrows()) + """

## Current holdings
""" + "\n".join(f"- {t}: {v:.1%} ({D.sectors[t]})" for t, v in w.items()) + "\n"
    (OUT / "REPORT.md").write_text(md)
    print(f"chosen: {chosen}")
    print(f"holdout v2  CAGR {pct(s_c['cagr'])} Sharpe {s_c['sharpe']:.2f} DD {pct(s_c['max_dd'])}")
    print(f"holdout EW  CAGR {pct(s_e['cagr'])} Sharpe {s_e['sharpe']:.2f} DD {pct(s_e['max_dd'])}")
    print(f"holdout SPY CAGR {pct(s_s['cagr'])} Sharpe {s_s['sharpe']:.2f} DD {pct(s_s['max_dd'])}")
    print(f"CI vs EW holdout {ci_hold}, full {ci_full}")


if __name__ == "__main__":
    main()
