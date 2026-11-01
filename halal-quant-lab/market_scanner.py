"""Signal board: halal US stocks ($2B+), halal ETFs, top crypto coins and halal EGX stocks, with a verdict.

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
A buy signal on a thinly traded asset (20-day median traded value under $5M, or EGP 1M on EGX)
is downgraded to HOLD and flagged. Per asset it also reports how this system did on that asset's own
history vs buy & hold. Universe lists: reports/broad_screen.csv (large caps), reports/universe/
midcap_screen.csv and crypto_list.json (refresh with `python -m lab.expand`), lab/egx.py (EGX).
Not financial advice. Shariah status of crypto is debated; verify stocks with a Shariah screener.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import json

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.egx import halal_egx
from lab.metrics import stats
from lab.single import run_position

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "signal_board"
HIST_START = "2016-01-01"

ETFS = {"SPUS": "SP Funds S&P 500 Sharia ETF", "HLAL": "Wahed FTSE USA Shariah ETF",
        "UMMA": "Wahed Dow Jones Islamic World ex-US ETF", "SPRE": "SP Funds Global REIT Sharia ETF",
        "SPSK": "SP Funds Global Sukuk ETF", "SPTE": "SP Funds Global Technology ETF",
        "SPWO": "SP Funds World ex-US ETF"}
UNIVERSE = ROOT / "reports" / "universe"
# Restaurant / entertainment chains with large bar (alcohol) sales - excluded on top of the screen.
ALCOHOL_HEAVY = {"EAT", "DRI", "TXRH", "CAKE", "BJRI", "BLMN", "DIN", "PLAY", "CHUY", "RRGB", "KRUS", "FWRG",
                 "BH", "DENN", "CBRL", "STKS", "ARKR", "TAST", "NATH"}
COST = {"Crypto": 0.001, "EGX stock": 0.0025}
MIN_VALUE = {"EGX stock": 1_000_000}          # local currency per day; everything else uses $5M
CURRENCY = {"EGX stock": "EGP"}


def analyse(args):
    tk, df, kind = args
    vol_series = df["Volume"] if "Volume" in df else None
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if kind == "EGX stock":                                 # drop impossible daily moves (data errors)
        df = df[~(df.Close.pct_change().abs() > 0.5)]
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
    value = float((df.Close * (vol_series.reindex(df.index).fillna(0) if vol_series is not None else 0))
                  .rolling(20).median().iloc[-1]) if vol_series is not None else np.nan
    liquid = not (value < MIN_VALUE.get(kind, 5_000_000))
    if fresh_up and entry_bright and not liquid:
        verdict = "HOLD"
    elif fresh_up and entry_bright and lor5:
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
        "HOLD": (f"New buy signal, but thin trading (about {value / 1e6:.1f}M a day) makes it hard to buy and sell."
                 if fresh_up and entry_bright and not liquid else
                 f"Uptrend for {run} days. Keep if you own it; sell on a close below the stop."),
        "SELL": "Red arrow in the last 3 days. Exit if you own it.",
        "AVOID": f"Downtrend for {run} days. Wait for a green arrow with bright green squeeze.",
    }

    # This system on the asset's own history (enter: arrow + bright squeeze; exit: red arrow)
    pos = np.zeros(len(c))
    for t in range(1, len(c)):
        pos[t] = (1 if st[t] == 1 else 0) if pos[t - 1] else (1 if flip_up[t] and bright[t] else 0)
    cost = COST.get(kind, 0.0005)
    r, p = run_position(o, c, pos, cost)
    rs = pd.Series(r, index=df.index).loc[HIST_START:]
    bh = df.Close.pct_change().loc[HIST_START:]
    year = 365 if kind == "Crypto" else 252
    s_sys, s_bh = stats(rs, year=year), stats(bh, year=year)
    n_tr = int(((p[1:] == 1) & (p[:-1] == 0))[df.index[1:] >= HIST_START].sum())
    return {
        "symbol": tk, "kind": kind, "verdict": verdict, "score": int(score),
        "currency": CURRENCY.get(kind, "USD"), "traded_value_m": round(value / 1e6, 2) if value == value else None,
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
    mid = pd.read_csv(UNIVERSE / "midcap_screen.csv")
    # Defense contractors are not screened out by name among mid caps, so drop the whole industry.
    mid = mid[mid.compliant & ~mid.ticker.isin(us.ticker) & (mid.industry != "Aerospace & Defense")
              & ~mid.ticker.isin(ALCOHOL_HEAVY)]
    us = us[~us.ticker.isin(ALCOHOL_HEAVY)]
    crypto = {c["symbol"]: c["name"] for c in json.loads((UNIVERSE / "crypto_list.json").read_text())}
    egx = [t + ".CA" for t in halal_egx()]
    names = (dict(zip(us.ticker, us.name)) | dict(zip(mid.ticker, mid.name)) | ETFS | crypto
             | {t: t[:-3] + " (EGX)" for t in egx})
    sectors = dict(zip(us.ticker, us.sector)) | dict(zip(mid.ticker, mid.sector))
    size = {t: "Large cap" for t in us.ticker} | {t: "Mid cap" for t in mid.ticker}
    kinds = ({t: "US stock" for t in list(us.ticker) + list(mid.ticker)} | {t: "Halal ETF" for t in ETFS}
             | {t: "Crypto" for t in crypto} | {t: "EGX stock" for t in egx})
    raw = yf.download(list(kinds), period="12y", auto_adjust=True, progress=False, threads=True, group_by="column")
    jobs = [(t, pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}), k)
            for t, k in kinds.items() if t in raw["Close"]]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        rows = [r for r in ex.map(analyse, jobs) if r]
    df = pd.DataFrame(rows)
    df.insert(1, "name", [names.get(s, s) for s in df.symbol])
    df.insert(3, "sector", [sectors.get(s, {"Crypto": "Crypto", "Halal ETF": "ETF", "EGX stock": "Egypt"}.get(k, ""))
                            for s, k in zip(df.symbol, df.kind)])
    df.insert(4, "size", [size.get(s, "") for s in df.symbol])
    # Display symbols without Yahoo suffixes, keeping them unique
    short = df.symbol.str.replace(r"\.CA$", "", regex=True).str.replace(r"\d*-USD$", "", regex=True)
    dup = short.duplicated(keep=False)
    df["symbol"] = np.where(dup, df.symbol, short)
    order = {"STRONG BUY": 0, "BUY": 1, "SELL": 2, "HOLD": 3, "AVOID": 4}
    df = df.sort_values(["verdict", "score"], key=lambda s: s.map(order) if s.name == "verdict" else -s)
    df.to_csv(OUT / "signals.csv", index=False)
    print(df.verdict.value_counts().to_string())
    print(df.head(12)[["symbol", "kind", "verdict", "score", "close", "stop", "squeeze", "lorentzian"]].to_string())


if __name__ == "__main__":
    main()
