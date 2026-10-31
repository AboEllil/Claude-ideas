"""Risk-managed daily confluence strategy: ATR sizing, 1-2% risk per trade, chandelier stops,
RVOL footprint test, monthly-return reality check and dividend purification.

    python run_halal_alpha.py
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yfinance as yf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab import risk_engine  # noqa: E402
from lab.data import load_prices  # noqa: E402
from lab.metrics import drawdown, stats  # noqa: E402
from run_tv import PERIODS, START, market_ok  # noqa: E402
from run_tv_rotation import rotate, signals  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "alpha"

VARIANTS = {
    "Confluence rotation (previous best, no stops)": None,
    "A  risk 1%, 3xATR trailing stop": dict(risk=0.01, k=3.0),
    "B  risk 2%, 3xATR trailing stop": dict(risk=0.02, k=3.0),
    "C  risk 1% + RVOL >= 1.5 footprint": dict(risk=0.01, k=3.0, rvol_min=1.5),
    "D  risk 1%, 2xATR (tighter) stop": dict(risk=0.01, k=2.0),
}


def monthly(r):
    m = (1 + r).resample("ME").prod() - 1
    return {"median": m.median(), "best": m.max(), "worst": m.min(),
            "ge10": (m >= 0.10).mean(), "ge25": (m >= 0.25).mean(), "pos": (m > 0).mean()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rank = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(rank.index)[:100]
    px = load_prices(tickers)
    mkt = market_ok(px["Close"]["SPY"].ffill())
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    sig = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for tk, df in ex.map(signals, jobs):
            sig[tk] = df
    md = [f"# Risk-managed halal confluence strategy (daily)\n\nGenerated {pd.Timestamp.now():%Y-%m-%d}. "
          "Signals: our Confluence strategy without the market filter (see `reports/tv/REPORT.md`). "
          "Long-only, no leverage, next-open execution, 5 bps per side, cash earns 0%.\n"
          "Cells: CAGR / Sharpe / max drawdown.\n"]
    curves = {}
    for label, tks in (("Top 20", tickers[:20]), ("Ranks 21-100", tickers[20:])):
        sl = slice("2009-01-01", None)
        O, H, L, C, V = (px[f][tks].loc[sl] for f in ("Open", "High", "Low", "Close", "Volume"))
        on = pd.DataFrame({t: sig[t]["cf_nm"] for t in tks}).reindex(C.index)
        rets = C.pct_change(fill_method=None)
        res = {"Buy & hold (equal weight)": rotate(rets.notna().astype(float), rets, cap=1.0)}
        inv = {"Buy & hold (equal weight)": 1.0}
        ntr = {}
        for name, kw in VARIANTS.items():
            if kw is None:
                res[name] = rotate(on, rets)
                inv[name] = float(np.minimum(on.fillna(0).sum(axis=1) * 0.10, 1).loc[START:].mean())
            else:
                r, invested, trs = risk_engine.run(O, H, L, C, V, on, **kw)
                res[name], inv[name] = r, float(invested.loc[START:].mean())
                ntr[name] = trs
        if "SPUS" in px["Close"]:
            res["SPUS (halal ETF, since 2020)"] = px["Close"]["SPUS"].pct_change().dropna()
        res = {k: v.loc[START:] for k, v in res.items()}
        md += [f"## {label}", "", "| Strategy | " + " | ".join(PERIODS) + " | Avg invested | Trades | Win rate |",
               "|---|---|---|---|---|---|---|"]
        for n, r in res.items():
            cells = " | ".join(f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / "
                               f"{stats(r.loc[a:b])['max_dd']:.0%}" for a, b in PERIODS.values())
            trs = ntr.get(n)
            md.append(f"| {n} | {cells} | {inv.get(n, 1.0):.0%} | {len(trs) if trs else ''} | "
                      f"{f'{np.mean(np.array(trs) > 0):.0%}' if trs else ''} |")
        md += ["", "### Monthly returns - reality check vs a 25-50%/month target", "",
               "| Strategy | Median month | Best month | Worst month | Months >= +10% | Months >= +25% | Up months |",
               "|---|---|---|---|---|---|---|"]
        for n, r in res.items():
            m = monthly(r)
            md.append(f"| {n} | {m['median']:.1%} | {m['best']:.1%} | {m['worst']:.1%} | {m['ge10']:.0%} | "
                      f"{m['ge25']:.0%} | {m['pos']:.0%} |")
        md.append("")
        curves[label] = res

    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    cols = ["#9ca3af", "#93c5fd", "#2563eb", "#16a34a", "#f59e0b", "#a855f7", "#ef4444"]
    for k, (label, res) in enumerate(curves.items()):
        for (n, r), col in zip(res.items(), cols):
            axes[0, k].plot((1 + r).cumprod(), color=col, lw=2 if n.startswith("A ") else 1.1, label=n)
            axes[1, k].plot(drawdown(r), color=col, lw=1)
        axes[0, k].set_yscale("log")
        axes[0, k].set_title(label, loc="left")
        axes[1, k].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        for a in axes[:, k]:
            a.grid(alpha=0.25)
            a.spines[["top", "right"]].set_visible(False)
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "risk_managed.png", dpi=130)
    plt.close(fig)
    md.append("![risk managed](risk_managed.png)\n")

    print("purification ...")
    pur = risk_engine.purification(tickers[:20], yf.Ticker)
    pur.to_csv(OUT / "purification_top20.csv")
    md += ["## Estimated dividend purification (top 20)",
           "Purify = dividend received x (interest income / total revenue), the main non-permissible income source "
           "of screened companies. Estimate only - use your screener's reported purification ratio when available.",
           "", "| Ticker | Dividend yield | Non-permissible income share | Purify per $10,000 held, per year |",
           "|---|---|---|---|"]
    for t, r in pur.iterrows():
        fmt = lambda x, f: "n/a" if pd.isna(x) else f.format(x)  # noqa: E731
        md.append(f"| {t} | {fmt(r.dividend_yield, '{:.2%}')} | {fmt(r.interest_income_pct_revenue, '{:.2%}')} | "
                  f"{fmt(r.purify_per_10k_invested_usd, '${:.2f}')} |")
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
