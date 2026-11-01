"""Test ~25 popular TradingView community indicators as long-only daily strategies.

    python run_indicators.py

Same setup as run_tv.py: daily bars 2010-today, decisions at the close, trades at the next open,
5 bps per side, default script settings. Two portfolio views per indicator:
  sleeves  - each stock gets 1/N of capital, cash when its signal is off (pure signal quality)
  rotation - capital spread equally over stocks whose signal is ON, max 10% each (no idle cash)
Universes: top 20 halal stocks and ranks 21-100 (the fairer test).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import tv, tv2
from lab.data import load_prices
from lab.metrics import stats
from lab.single import run_position, trades
from run_tv_rotation import rotate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "tv"
START = "2010-01-01"

STRATS = {"Buy & hold": (lambda o, h, l, c: np.ones(len(c)), False, "benchmark")}
STRATS.update(tv2.STRATEGIES)
STRATS.update({
    "ML Adaptive SuperTrend (AlgoAlpha)": (lambda o, h, l, c: tv.adaptive_supertrend(o, h, l, c)[0], False, "trend"),
    "Squeeze Momentum (LazyBear)": (lambda o, h, l, c: tv.squeeze_strategy(o, h, l, c)[0], False, "breakout"),
    "Smart Money Concepts (LuxAlgo)": (lambda o, h, l, c: tv.smc_strategy(o, h, l, c)[0], False, "smart money"),
    "Lorentzian Classification (jdehorty)": (lambda o, h, l, c: tv.lorentzian(o, h, l, c)[0], False, "machine learning"),
})


def one(args):
    tk, df = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df["Volume"].fillna(0).to_numpy(float)
    m = df.index >= START
    out = {}
    for name, (fn, needs_v, _) in STRATS.items():
        pos = fn(o, h, l, c, v) if needs_v else fn(o, h, l, c)
        pos = np.nan_to_num(np.asarray(pos, float))
        r, p = run_position(o, c, pos)
        out[name] = (pd.Series(r[m], index=df.index[m]), float(p[m].mean()) if m.any() else 0.0,
                     trades(o[m], c[m], p[m]) if m.any() else [], pd.Series(pos, index=df.index))
    return tk, out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tickers = list(pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0).index[:100])
    px = load_prices(tickers)
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close", "Volume")})) for t in tickers]
    res = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i, (tk, out) in enumerate(ex.map(one, jobs), 1):
            res[tk] = out
            if i % 20 == 0:
                print(f"  {i}/100 stocks", flush=True)
    rets = px["Close"][tickers].pct_change(fill_method=None).loc["2009-01-01":]
    years = (pd.Timestamp.now() - pd.Timestamp(START)).days / 365.25
    rows = []
    for name, (_, _, fam) in STRATS.items():
        row = {"Indicator": name, "Type": fam}
        for uni, tks in (("top20", tickers[:20]), ("r80", tickers[20:])):
            sleeves = pd.DataFrame({t: res[t][name][0] for t in tks}).mean(axis=1).fillna(0)
            on = pd.DataFrame({t: res[t][name][3] for t in tks})
            rot = rotate(on if name != "Buy & hold" else rets[tks].notna().astype(float), rets[tks],
                         cap=0.10 if name != "Buy & hold" else 1.0).loc[START:]
            s, sr = stats(sleeves), stats(rot)
            trs = [x for t in tks for x in res[t][name][2]]
            row[f"{uni}_sleeve"] = (s["cagr"], s["sharpe"], s["max_dd"])
            row[f"{uni}_rot"] = (sr["cagr"], sr["sharpe"], sr["max_dd"])
            row[f"{uni}_expo"] = np.mean([res[t][name][1] for t in tks])
            row[f"{uni}_trades"] = len(trs) / len(tks) / years
            row[f"{uni}_win"] = np.mean(np.array(trs) > 0) if trs else np.nan
            if uni == "r80":
                bh = {t: stats(res[t]["Buy & hold"][0])["sharpe"] for t in tks}
                row["r80_beats"] = sum(stats(res[t][name][0])["sharpe"] > bh[t] for t in tks)
        rows.append(row)
    df = pd.DataFrame(rows)
    df["rank_key"] = df.r80_rot.apply(lambda x: x[1])
    bh = df[df.Indicator == "Buy & hold"].iloc[0]
    df = pd.concat([df[df.Indicator == "Buy & hold"],
                    df[df.Indicator != "Buy & hold"].sort_values("rank_key", ascending=False)])

    def f3(x):
        return f"{x[0]:.1%} / {x[1]:.2f} / {x[2]:.0%}"

    md = ["# 24 TradingView community indicators tested on halal stocks", "",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Daily bars {START[:4]}-today, default settings, signals at the close, "
          "orders at the next open, 5 bps per side, long-only. Cells: **CAGR / Sharpe / max drawdown**. "
          "Sorted by Sharpe of the rotation portfolio on ranks 21-100 (the fairer universe).", "",
          "| # | Indicator | Type | Ranks 21-100 rotation | Ranks 21-100 sleeves | Top 20 rotation | In market | Trades/stock/yr | Win rate | Beats B&H Sharpe (of 80 stocks) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for i, (_, r) in enumerate(df.iterrows()):
        n = "" if r.Indicator == "Buy & hold" else i
        b = "**" if r.Indicator == "Buy & hold" else ""
        md.append(f"| {n} | {b}{r.Indicator}{b} | {r.Type} | {f3(r.r80_rot)} | {f3(r.r80_sleeve)} | {f3(r.top20_rot)} | "
                  f"{r.r80_expo:.0%} | {'' if r.Indicator == 'Buy & hold' else f'{r.r80_trades:.1f}'} | "
                  f"{'' if pd.isna(r.r80_win) or r.Indicator == 'Buy & hold' else f'{r.r80_win:.0%}'} | "
                  f"{'' if r.Indicator == 'Buy & hold' else int(r.r80_beats)} |")
    md += ["", "Not testable as buy/sell rules (drawing or session tools): ICT Killzones, Sessions (LuxAlgo), Swing High/Low "
           "(Patternsmart), Support/Resistance (ChartPrime, LonesomeTheBlue channels), Breakout Probability (Zeiierman), "
           "RelativeValue. Paid/locked (code not public): LuxAlgo Signals & Overlays, LuxAlgo Price Action Concepts. "
           "Covered by another test: Smart Money Concepts (AlgoAlpha), ICT Concepts (LuxAlgo), Buyside & Sellside "
           "Liquidity (LuxAlgo), CM_Ultimate_MA_MTF, Order Block Detector.", ""]
    (OUT / "INDICATORS.md").write_text("\n".join(md) + "\n")
    df.drop(columns=["rank_key"]).to_csv(OUT / "indicators.csv", index=False)
    print("\n".join(md))
    _ = bh


if __name__ == "__main__":
    main()
