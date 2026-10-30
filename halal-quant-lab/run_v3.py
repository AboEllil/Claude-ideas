"""v3: survivorship-free halal multi-asset experiments (pre-registered by the debate round).

    python run_v3.py

Uses only real fund/ETF histories, so there is no survivorship bias:
  US equity    AMAGX (Amana Growth, Shariah mutual fund) -> SPUS from 2020
  Intl equity  AMDWX (Amana Developing World)            -> UMMA from 2022
  REITs        SPRE (2021+)
  Gold         IAU (physically backed; Shariah status debated - ask a scholar)
  Sukuk        SPSK (2020+); before that the defensive asset is 0% cash
               (T-bills/money markets are interest-based, so not used)

Experiments and pass rules were fixed BEFORE running (see reports/RESEARCH_NOTES.md).
"""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import yfinance as yf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lab.allocation import (dual_momentum_targets, overlay_exposure, overlay_targets,  # noqa: E402
                            simulate_weights, splice, static_targets)
from lab.metrics import drawdown, stats, yearly  # noqa: E402
from lab.universe import DATA  # noqa: E402

OUT = Path(__file__).resolve().parent / "reports" / "v3"
TICKERS = ["AMAGX", "AMANX", "AMDWX", "SPUS", "HLAL", "UMMA", "SPRE", "IAU", "SPSK", "SPY"]
START = "2006-03-01"


def load():
    cache = DATA / "funds.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    px = yf.download(TICKERS, start="2005-01-01", auto_adjust=True, progress=False)["Close"]
    DATA.mkdir(exist_ok=True)
    px.to_pickle(cache)
    return px


def s3(r):
    s = stats(r)
    return s["cagr"], s["sharpe"], s["max_dd"]


def fmt(r):
    c, sh, dd = s3(r)
    return f"{c:.1%} / {sh:.2f} / {dd:.0%}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    px = load()
    raw = px.pct_change(fill_method=None)
    raw = raw.loc[raw.index >= px["IAU"].first_valid_index()]
    r = pd.DataFrame({
        "US": splice(raw, ["SPUS", "AMAGX"]),
        "INTL": splice(raw, ["UMMA", "AMDWX"]),
        "REIT": raw["SPRE"],
        "GOLD": raw["IAU"],
        "SUKUK": raw["SPSK"],
        "AMAGX": raw["AMAGX"],
        "SPUS": raw["SPUS"],
        "HLAL": raw["HLAL"],
        "SPY": raw["SPY"],
    })
    md = [f"# v3 Survivorship-free halal multi-asset tests\n\nGenerated {pd.Timestamp.now():%Y-%m-%d}. "
          f"Data to {r.index[-1]:%Y-%m-%d}. Cells are CAGR / Sharpe / Max drawdown. 5 bps per side costs.\n"]
    halves = {"2006-2012": ("2006", "2012"), "2013-today": ("2013", "2100"), "2006-today": (START, "2100")}

    # ---- Experiment 1: overlay on real halal funds ---------------------------------
    res1 = {}
    expo = overlay_exposure(r["AMAGX"])
    res1["AMAGX buy & hold"] = r["AMAGX"].fillna(0)
    res1["AMAGX + overlay, 0% cash"] = simulate_weights(r, overlay_targets(r, "AMAGX", None, expo))
    res1["AMAGX + overlay, freed weight in gold"] = simulate_weights(r, overlay_targets(r, "AMAGX", "GOLD", expo))
    rows = []
    for n, x in res1.items():
        rows.append(f"| {n} | " + " | ".join(fmt(x.loc[a:b]) for a, b in halves.values()) + " |")
    bh = res1["AMAGX buy & hold"]
    verdicts = []
    for n in list(res1)[1:]:
        ok = True
        for a, b in list(halves.values())[:2]:
            _, sh0, dd0 = s3(bh.loc[a:b])
            _, sh1, dd1 = s3(res1[n].loc[a:b])
            ok &= dd1 > dd0 and sh1 >= sh0 - 0.05
        _, sh0, dd0 = s3(bh.loc[START:])
        _, sh1, dd1 = s3(res1[n].loc[START:])
        ok &= (dd1 / dd0) <= 0.7 and sh1 >= sh0 - 0.05
        verdicts.append(f"- **{n}: {'PASS' if ok else 'FAIL'}** (drawdown {dd0:.0%} -> {dd1:.0%}, "
                        f"Sharpe {sh0:.2f} -> {sh1:.2f})")
    md += ["## Experiment 1 - risk overlay on a real Shariah fund (AMAGX, 2006-today)",
           "Rule: same slow trend filter + 20% vol target as v2. Pass = max drawdown at least 30% smaller "
           "and Sharpe no more than 0.05 lower, holding in both halves.\n",
           "| Strategy | " + " | ".join(halves) + " |", "|---|---|---|---|", *rows, "", *verdicts, ""]

    rows = []
    for eq in ("SPUS", "HLAL"):
        e = overlay_exposure(r[eq])
        for n, d in (("buy & hold", None), ("overlay, 0% cash", "cash"), ("overlay, sukuk", "SUKUK"),
                     ("overlay, gold", "GOLD")):
            x = r[eq].fillna(0) if d is None else simulate_weights(r, overlay_targets(r, eq, None if d == "cash" else d, e))
            rows.append(f"| {eq} {n} | {fmt(x.loc['2020-12':])} |")
    md += ["### Same overlay on Shariah ETFs, 2021-today (after one year of warm-up)",
           "| Strategy | 2021-today |", "|---|---|", *rows, ""]

    # ---- Experiment 2: static halal mix ---------------------------------------------
    bh_us = simulate_weights(r, static_targets(r, {"US": 1.0}, start=0))
    mix = simulate_weights(r, static_targets(r, {"US": 0.70, "GOLD": 0.15, "SUKUK": 0.15}, start=0))
    c0, sh0, dd0 = s3(bh_us.loc[START:])
    c1, sh1, dd1 = s3(mix.loc[START:])
    ok2 = sh1 >= sh0 + 0.1 and dd1 >= -0.35
    md += ["## Experiment 2 - static mix: 70% halal US equity, 15% gold, 15% sukuk (yearly rebalance)",
           "Before 2020 the sukuk slice is 0% cash. Pass = Sharpe at least +0.10 vs 100% equity and max drawdown "
           "no worse than -35%.\n",
           "| Strategy | " + " | ".join(halves) + " |", "|---|---|---|---|",
           f"| 100% halal US equity | " + " | ".join(fmt(bh_us.loc[a:b]) for a, b in halves.values()) + " |",
           f"| 70 / 15 / 15 mix | " + " | ".join(fmt(mix.loc[a:b]) for a, b in halves.values()) + " |", "",
           f"- **{'PASS' if ok2 else 'FAIL'}** (Sharpe {sh0:.2f} -> {sh1:.2f}, drawdown {dd0:.0%} -> {dd1:.0%})", ""]

    # ---- Experiment 3: dual momentum across halal assets ----------------------------
    dm = simulate_weights(r, dual_momentum_targets(r, ["US", "INTL", "REIT", "GOLD"], "SUKUK"))
    eras = {"2006-2019 (proxy era)": (START, "2019"), "2020-today (real ETFs)": ("2020", "2100")}
    ok3 = True
    for a, b in eras.values():
        ok3 &= s3(dm.loc[a:b])[1] >= s3(mix.loc[a:b])[1] + 0.1
    ok3 &= s3(dm.loc[START:])[2] >= s3(mix.loc[START:])[2]
    md += ["## Experiment 3 - dual momentum: US / international / REIT / gold, top 2 by 12-month return, "
           "negative momentum -> sukuk (0% cash before 2020)",
           "Fixed in advance: 12-month lookback, hold 2, monthly. Pass = Sharpe at least +0.10 vs experiment 2 "
           "in both eras and max drawdown no worse.\n",
           "| Strategy | " + " | ".join(eras) + " | 2006-today |", "|---|---|---|---|",
           f"| 70/15/15 mix | " + " | ".join(fmt(mix.loc[a:b]) for a, b in eras.values()) + f" | {fmt(mix.loc[START:])} |",
           f"| Dual momentum | " + " | ".join(fmt(dm.loc[a:b]) for a, b in eras.values()) + f" | {fmt(dm.loc[START:])} |",
           f"| SPY (reference) | " + " | ".join(fmt(r['SPY'].fillna(0).loc[a:b]) for a, b in eras.values())
           + f" | {fmt(r['SPY'].fillna(0).loc[START:])} |", "",
           f"- **{'PASS' if ok3 else 'FAIL'}**", ""]

    # ---- Chart ----------------------------------------------------------------------
    series = {"AMAGX buy & hold": (bh, "#9ca3af"), "AMAGX + overlay (gold)": (res1["AMAGX + overlay, freed weight in gold"], "#2563eb"),
              "70/15/15 mix": (mix, "#16a34a"), "Dual momentum": (dm, "#f59e0b"), "SPY": (r["SPY"].fillna(0), "#cbd5e1")}
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    for n, (x, c) in series.items():
        x = x.loc[START:]
        a1.plot((1 + x).cumprod(), label=n, color=c, lw=2 if "overlay" in n or "mix" in n else 1.2)
        a2.plot(drawdown(x), color=c, lw=1)
    a1.set_yscale("log")
    a1.set_title("Survivorship-free halal portfolios, 2006-today", loc="left")
    a1.set_ylabel("Growth of $1")
    a2.set_ylabel("Drawdown")
    a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    for a in (a1, a2):
        a.grid(alpha=0.25)
        a.spines[["top", "right"]].set_visible(False)
    a1.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "equity_v3.png", dpi=130)
    plt.close(fig)
    md.append("![v3](equity_v3.png)\n")

    yr = pd.DataFrame({n: yearly(x.loc[START:]) for n, (x, _) in series.items()})
    md += ["## Year by year", "| Year | " + " | ".join(yr.columns) + " |", "|---" * (len(yr.columns) + 1) + "|"]
    md += [f"| {y} | " + " | ".join(f"{v:.1%}" for v in row) + " |" for y, row in yr.iterrows()]
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:60]))


if __name__ == "__main__":
    main()
