"""Improvement 1: volatility-scaled risk budget (pre-registered).

    python run_improvement1.py

Rule   : risk per NEW trade = 1% x min(1, 20% / sigma_SPY), sigma_SPY = 42-day annualised
         volatility of SPY daily returns up to the signal day's close. Open positions untouched.
Pass   : on ranks 21-100, max drawdown improves AND Sharpe drops by no more than 0.05,
         in BOTH 2010-2018 and 2019-today.
Everything else identical to variant A in run_halal_alpha.py.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import risk_engine
from lab.data import load_prices
from lab.metrics import stats
from run_tv import START, market_ok
from run_tv_rotation import signals

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "alpha"
HALVES = {"2010-2018": ("2010", "2018"), "2019-today": ("2019", "2100")}
STRESS = {"2011 Aug-Oct": ("2011-08", "2011-10"), "2015-16 selloff": ("2015-08", "2016-02"),
          "2018 Q4": ("2018-10", "2018-12"), "2020 Covid crash": ("2020-02-15", "2020-04-30"),
          "2022 bear": ("2022-01", "2022-10"), "2025 Apr tariff shock": ("2025-02-15", "2025-05-15")}


def main():
    rank = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(rank.index)[:100]
    px = load_prices(tickers)
    spy = px["Close"]["SPY"].ffill()
    sigma = spy.pct_change().rolling(42).std() * np.sqrt(252)
    scale = (0.20 / sigma).clip(upper=1.0)
    mkt = market_ok(spy)
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        sig = dict(ex.map(signals, jobs))

    md = ["", "---", "", "# Improvement 1: volatility-scaled risk budget (pre-registered)", "",
          "Risk per new trade = 1% x min(1, 20% / SPY 42-day volatility). Open positions untouched. "
          "Pass = on ranks 21-100, max drawdown better AND Sharpe no more than 0.05 lower, in both halves.", "",
          f"Average risk multiplier since 2010: {scale.loc[START:].mean():.2f} "
          f"(below 1 on {(scale.loc[START:] < 1).mean():.0%} of days; minimum {scale.loc[START:].min():.2f} in "
          f"{scale.loc[START:].idxmin():%b %Y}).", ""]
    verdict = None
    for label, tks in (("Top 20", tickers[:20]), ("Ranks 21-100", tickers[20:])):
        sl = slice("2009-01-01", None)
        O, H, L, C, V = (px[f][tks].loc[sl] for f in ("Open", "High", "Low", "Close", "Volume"))
        on = pd.DataFrame({t: sig[t]["cf_nm"] for t in tks}).reindex(C.index)
        res = {}
        for name, kw in (("A  risk 1% (baseline)", {}), ("A + vol-scaled risk", {"risk_scale": scale})):
            r, inv, trs = risk_engine.run(O, H, L, C, V, on, risk=0.01, k=3.0, **kw)
            res[name] = (r.loc[START:], float(inv.loc[START:].mean()), trs)
        md += [f"## {label}", "", "| Strategy | 2010-2018 | 2019-today | 2010-today | Worst month | Avg invested |",
               "|---|---|---|---|---|---|"]
        for n, (r, inv, _) in res.items():
            cells = [f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / "
                     f"{stats(r.loc[a:b])['max_dd']:.0%}" for a, b in list(HALVES.values()) + [("2010", "2100")]]
            wm = ((1 + r).resample("ME").prod() - 1).min()
            md.append(f"| {n} | " + " | ".join(cells) + f" | {wm:.1%} | {inv:.0%} |")
        md += ["", "Stress periods (total return / max drawdown inside the window):", "",
               "| Period | " + " | ".join(res) + " |", "|---|---|---|"]
        for p, (a, b) in STRESS.items():
            cells = []
            for r, _, _ in res.values():
                x = r.loc[a:b]
                cells.append(f"{(1 + x).prod() - 1:.1%} / {stats(x)['max_dd']:.0%}" if len(x) > 20 else "n/a")
            md.append(f"| {p} | " + " | ".join(cells) + " |")
        md.append("")
        if label == "Ranks 21-100":
            base, new = res["A  risk 1% (baseline)"][0], res["A + vol-scaled risk"][0]
            ok, notes = True, []
            for h, (a, b) in HALVES.items():
                sb, sn = stats(base.loc[a:b]), stats(new.loc[a:b])
                good = sn["max_dd"] > sb["max_dd"] and sn["sharpe"] >= sb["sharpe"] - 0.05
                ok &= good
                notes.append(f"{h}: drawdown {sb['max_dd']:.1%} -> {sn['max_dd']:.1%}, "
                             f"Sharpe {sb['sharpe']:.2f} -> {sn['sharpe']:.2f} ({'ok' if good else 'fails'})")
            verdict = (ok, notes)
    ok, notes = verdict
    md += [f"## Verdict: **{'PASS' if ok else 'FAIL'}**", ""] + [f"- {n}" for n in notes] + [""]
    with open(OUT / "REPORT.md", "a") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
