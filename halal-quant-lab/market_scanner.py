"""Signal board: every halal US stock ($10B+), halal ETF and major crypto coin, with a verdict.

    python market_scanner.py      # writes reports/signal_board/signals.csv

Indicators (the ones that tested best, see reports/tv/INDICATORS.md and reports/exits/REPORT.md):
  trend      ML Adaptive SuperTrend (AlgoAlpha) - green / red, days in trend, stop line
  momentum   Squeeze Momentum (LazyBear) - bright green / dark green / red / maroon
  ML         Lorentzian Classification (jdehorty) - green arrow in the last 5 days, or bias
  structure  Market structure (last break of structure up or down, 5-bar swings)
Verdict (the user's tested system: green arrow + bright green squeeze, exit on the red arrow):
  STRONG BUY  green arrow in the last 3 days + bright green squeeze + Lorentzian arrow (last 5 days)
  BUY         green arrow in the last 3 days + bright green squeeze
  HOLD        uptrend (green) - keep if you own it, stop at the SuperTrend line
  SELL        red arrow in the last 3 days - exit if you own it
  AVOID       downtrend (red)
Per asset it also reports how this system did on that asset's own history vs buy & hold.
Not financial advice. Shariah status of crypto is debated; verify stocks with a Shariah screener.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.metrics import stats
from lab.single import run_position

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "signal_board"
HIST_START = "2016-01-01"

ETFS = {"SPUS": "SP Funds S&P 500 Sharia ETF", "HLAL": "Wahed FTSE USA Shariah ETF",
        "UMMA": "Wahed Dow Jones Islamic World ex-US ETF", "SPRE": "SP Funds Global REIT Sharia ETF",
        "SPSK": "SP Funds Global Sukuk ETF", "SPTE": "SP Funds Global Technology ETF",
        "SPWO": "SP Funds World ex-US ETF"}
CRYPTO = {"BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana", "BNB-USD": "BNB",
          "XRP-USD": "XRP", "ADA-USD": "Cardano", "AVAX-USD": "Avalanche", "DOT-USD": "Polkadot",
          "LINK-USD": "Chainlink", "LTC-USD": "Litecoin", "TRX-USD": "TRON", "XLM-USD": "Stellar",
          "ATOM-USD": "Cosmos", "NEAR-USD": "NEAR Protocol", "HBAR-USD": "Hedera"}


def analyse(args):
    tk, df, kind = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if len(df) < 300:
        return None
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    vol = tv.atr(h, l, c, 10)
    a = tv._kmeans_atr(vol, 100, 0.75, 0.5, 0.25)
    st = (tv.supertrend(h, l, c, a, 3.0) == 1).astype(float)
    _, mom = tv.squeeze(o, h, l, c)
    lpos, pred = tv.lorentzian(o, h, l, c)
    trend_s = tv.smc_state(h, l, c, 5)[0]
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip_up = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    flip_dn = np.r_[False, (st[1:] == 0) & (st[:-1] == 1)]
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]

    # SuperTrend line (stop level) for the latest bar
    src = (h + l) / 2
    lo, up = src - 3 * a, src + 3 * a
    plo = pup = np.nan
    for t in range(len(c)):
        if np.isnan(a[t]):
            continue
        if not np.isnan(plo):
            lo[t] = lo[t] if (lo[t] > plo or c[t - 1] < plo) else plo
            up[t] = up[t] if (up[t] < pup or c[t - 1] > pup) else pup
        plo, pup = lo[t], up[t]
    line = lo[-1] if st[-1] == 1 else up[-1]

    run = 1
    while run < len(st) and st[-1 - run] == st[-1]:
        run += 1
    fresh_up = flip_up[-3:].any() and st[-1] == 1
    fresh_dn = flip_dn[-3:].any() and st[-1] == 0
    entry_bright = bool(bright[-3:][flip_up[-3:]].any()) if fresh_up else False
    lor5 = bool(larrow[-6:].any())
    if fresh_up and entry_bright and lor5:
        verdict = "STRONG BUY"
    elif fresh_up and entry_bright:
        verdict = "BUY"
    elif st[-1] == 1:
        verdict = "HOLD"
    elif fresh_dn:
        verdict = "SELL"
    else:
        verdict = "AVOID"
    sq = "bright green" if bright[-1] else "dark green" if m[-1] > 0 else "red" if m[-1] < m[-2] else "maroon"
    lor = "green arrow" if lor5 else "bullish" if pred[-1] > 0 else "bearish" if pred[-1] < 0 else "neutral"
    score = (40 * st[-1] + (20 if bright[-1] else 10 if m[-1] > 0 else 0)
             + (20 if lor5 else 10 if pred[-1] > 0 else 0) + (20 if trend_s[-1] == 1 else 0))
    reasons = {
        "STRONG BUY": "Fresh green arrow, bright green squeeze and a Lorentzian green arrow.",
        "BUY": "Fresh green arrow with bright green squeeze momentum.",
        "HOLD": f"Uptrend for {run} days. Keep if you own it; sell on a close below the stop.",
        "SELL": "Red arrow in the last 3 days. Exit if you own it.",
        "AVOID": f"Downtrend for {run} days. Wait for a green arrow with bright green squeeze.",
    }

    # This system on the asset's own history (enter: arrow + bright squeeze; exit: red arrow)
    pos = np.zeros(len(c))
    for t in range(1, len(c)):
        pos[t] = (1 if st[t] == 1 else 0) if pos[t - 1] else (1 if flip_up[t] and bright[t] else 0)
    cost = 0.001 if kind == "Crypto" else 0.0005
    r, p = run_position(o, c, pos, cost)
    rs = pd.Series(r, index=df.index).loc[HIST_START:]
    bh = df.Close.pct_change().loc[HIST_START:]
    year = 365 if kind == "Crypto" else 252
    s_sys, s_bh = stats(rs, year=year), stats(bh, year=year)
    n_tr = int(((p[1:] == 1) & (p[:-1] == 0))[df.index[1:] >= HIST_START].sum())
    return {
        "symbol": tk.replace("-USD", ""), "kind": kind, "verdict": verdict, "score": int(score),
        "close": round(float(c[-1]), 6), "change_1d": round(float(c[-1] / c[-2] - 1), 4),
        "trend": "up" if st[-1] == 1 else "down", "days_in_trend": int(run),
        "stop": round(float(line), 6), "stop_distance": round(float(c[-1] / line - 1), 4),
        "squeeze": sq, "lorentzian": lor, "structure": "bullish" if trend_s[-1] == 1 else "bearish",
        "reason": reasons[verdict],
        "hist_from": str(max(df.index[0], pd.Timestamp(HIST_START)).date()),
        "system_cagr": round(float(s_sys["cagr"]), 4), "system_max_dd": round(float(s_sys["max_dd"]), 4),
        "hold_cagr": round(float(s_bh["cagr"]), 4), "hold_max_dd": round(float(s_bh["max_dd"]), 4),
        "trades": n_tr, "as_of": str(df.index[-1].date()),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scr = pd.read_csv(ROOT / "reports" / "broad_screen.csv")
    us = scr[scr.compliant & (scr.marketCap >= 10e9)]
    names = dict(zip(us.ticker, us.name)) | ETFS | CRYPTO
    sectors = dict(zip(us.ticker, us.sector))
    kinds = {t: "US stock" for t in us.ticker} | {t: "Halal ETF" for t in ETFS} | {t: "Crypto" for t in CRYPTO}
    raw = yf.download(list(kinds), period="12y", auto_adjust=True, progress=False, threads=True, group_by="column")
    jobs = [(t, pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close")}), k)
            for t, k in kinds.items() if t in raw["Close"]]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        rows = [r for r in ex.map(analyse, jobs) if r]
    df = pd.DataFrame(rows)
    df.insert(1, "name", [names.get(s if k != "Crypto" else s + "-USD", s) for s, k in zip(df.symbol, df.kind)])
    df.insert(3, "sector", [sectors.get(s, "Crypto" if k == "Crypto" else "ETF") for s, k in zip(df.symbol, df.kind)])
    order = {"STRONG BUY": 0, "BUY": 1, "SELL": 2, "HOLD": 3, "AVOID": 4}
    df = df.sort_values(["verdict", "score"], key=lambda s: s.map(order) if s.name == "verdict" else -s)
    df.to_csv(OUT / "signals.csv", index=False)
    print(df.verdict.value_counts().to_string())
    print(df.head(12)[["symbol", "kind", "verdict", "score", "close", "stop", "squeeze", "lorentzian"]].to_string())


if __name__ == "__main__":
    main()
