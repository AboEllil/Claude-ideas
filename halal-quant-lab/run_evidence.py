"""Test the evidence-based strategies from the user's research report against the user's own system.

    python run_evidence.py

Same assets, costs and conventions as run_signal_lab.py (decided at the close, traded at the next
close; liquid entries only). TRAIN = 2016-2020, TEST = 2021-today.
  S1  200-day rule: hold while close > 200-day SMA (time-series trend, the report's benchmark)
  S2  Swing trend stack: EMA50 > EMA200, ADX(14) > 20, close above the prior 20-day high -> buy;
      exit on a 3 x ATR trailing stop from the highest close or a close below EMA50
  S3  RSI(2) pullback: close > SMA200 and RSI(2) < 10 -> buy; exit on a close above SMA5 or after 10 days
  S4  Momentum rotation: month-end, if the market is above its 200-day SMA, hold the top N by
      12-1 month return (US 10, EGX 8, crypto 5); otherwise cash
  U0  User's system: AlgoAlpha green arrow + bright squeeze, exit on the red arrow
  U1  U0 + weekly SuperTrend green
  U2  U1 + market regime: market above its 200-day SMA AND breadth (share of the market's assets above
      their 50-day SMA) > 50% at the signal
Also: the Ramadan effect on EGX (equal-weight halal EGX index, Ramadan days vs the rest).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from hijri_converter import Hijri

from lab import tv
from run_signal_lab import MIN_VALUE, TEST, TRAIN, evaluate, hold_until_red, load, supertrend_set

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "evidence"
TOPN = {"US": 10, "EGX": 8, "Crypto": 5}


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def analyse(args):
    tk, df, market, bench = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if market == "EGX":
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 400:
        return None
    idx = df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df["Volume"].fillna(0).to_numpy(float)
    liquid = pd.Series(c * v).rolling(20).median().to_numpy() >= MIN_VALUE[market]
    cs = pd.Series(c)
    sma200, sma50, sma5 = (cs.rolling(n).mean().to_numpy() for n in (200, 50, 5))
    e50, e200 = ema(c, 50), ema(c, 200)
    a14 = tv.atr(h, l, c, 14)
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    adx = tv.rma(100 * np.abs(tv.rma(pdm, 14) - tv.rma(mdm, 14)) / (tv.rma(pdm, 14) + tv.rma(mdm, 14)), 14)
    rsi2 = tv.rsi(c, 2)
    don20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    T = len(c)

    s1 = np.nan_to_num((c > sma200).astype(float))
    s2 = np.zeros(T)
    hi = 0.0
    for t in range(1, T):
        if s2[t - 1]:
            hi = max(hi, c[t])
            s2[t] = 0 if (c[t] < hi - 3 * a14[t] or c[t] < e50[t]) else 1
        elif liquid[t] and e50[t] > e200[t] and adx[t] > 20 and c[t] > don20[t]:
            s2[t], hi = 1, c[t]
    s3 = np.zeros(T)
    held = 0
    for t in range(1, T):
        if s3[t - 1]:
            held += 1
            s3[t] = 0 if (c[t] > sma5[t] or held >= 10) else 1
        elif liquid[t] and c[t] > sma200[t] and rsi2[t] < 10:
            s3[t], held = 1, 0
    st, _ = supertrend_set(h, l, c, 10, 3.0)
    _, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    if len(wk) > 120:
        wst = tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0]
        weekly = pd.Series(wst, index=wk.index).shift(1).reindex(idx, method="ffill").fillna(0).to_numpy() > 0.5
    else:
        weekly = np.zeros(T, bool)
    base = flip & bright & liquid
    mom121 = (cs.shift(21) / cs.shift(252) - 1).to_numpy()
    return {"tk": tk, "market": market, "idx": idx, "c": c, "S1": s1, "S2": s2, "S3": s3,
            "U0": hold_until_red(base, st), "U1": hold_until_red(base & weekly, st),
            "_entry_u1": base & weekly, "_st": st, "_above50": np.nan_to_num((c > sma50).astype(float)),
            "_mom": mom121, "_liquid": liquid}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = load()
    bench = {}
    for _, _, mk, b in jobs:
        bench.setdefault(mk, b)
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        res = [r for r in ex.map(analyse, jobs, chunksize=4) if r]
    md = ["# Strategies from the research report vs the user's system\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Same assets and costs as the signal lab; max 10% per position. "
          "TRAIN 2016-2020 / TEST 2021-today.\n"]
    names = {"S1": "S1 200-day rule", "S2": "S2 swing trend stack (EMA, ADX, Donchian, 3xATR)",
             "S3": "S3 RSI(2) pullback", "S4": "S4 momentum rotation (monthly)", "U0": "U0 your system",
             "U1": "U1 your system + weekly green", "U2": "U2 U1 + market & breadth regime"}
    for mk in ("US", "EGX", "Crypto"):
        rs = [r for r in res if r["market"] == mk]
        closes = pd.DataFrame({r["tk"]: pd.Series(r["c"], index=r["idx"]) for r in rs}).sort_index()
        b = bench[mk].reindex(closes.index).ffill()
        mkt_up = b > b.rolling(200).mean()
        breadth = pd.DataFrame({r["tk"]: pd.Series(r["_above50"], index=r["idx"]) for r in rs}).reindex(closes.index).mean(axis=1)
        regime = (mkt_up & (breadth > 0.5))
        pos = {k: {r["tk"]: pd.Series(r[k], index=r["idx"]) for r in rs} for k in ("S1", "S2", "S3", "U0", "U1")}
        pos["U2"] = {}
        for r in rs:
            reg = regime.reindex(r["idx"]).fillna(False).to_numpy()
            pos["U2"][r["tk"]] = pd.Series(hold_until_red(r["_entry_u1"] & reg, r["_st"]), index=r["idx"])
        # S4 momentum rotation
        momf = pd.DataFrame({r["tk"]: pd.Series(np.where(r["_liquid"], r["_mom"], np.nan), index=r["idx"]) for r in rs}).reindex(closes.index)
        month_end = closes.index.to_series().groupby(closes.index.to_period("M")).max()
        S4 = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)
        current = []
        for d in closes.index:
            if d in set(month_end):
                current = list(momf.loc[d].dropna().nlargest(TOPN[mk]).index) if bool(mkt_up.loc[d]) else []
            if current:
                S4.loc[d, current] = 1.0
        pos["S4"] = {t: S4[t] for t in S4.columns}
        bh = {t: pd.Series(1.0, index=closes.index).where(closes[t].notna(), 0.0) for t in closes.columns}
        md += [f"## {mk} ({len(rs)} assets)", "",
               "| Strategy | TEST win | TEST avg trade | TEST PF | TEST CAGR | TEST Sharpe | TEST max DD | TRAIN PF | TRAIN CAGR | TRAIN Sharpe | TRAIN max DD | TEST trades/yr |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in ("U0", "U1", "U2", "S1", "S2", "S3", "S4"):
            te, tr = evaluate(pos[k], closes, mk, TEST), evaluate(pos[k], closes, mk, TRAIN)
            md.append(f"| {names[k]} | {te['win']:.0%} | {te['avg']:+.1%} | {te['pf']:.2f} | {te['cagr']:.1%} | "
                      f"{te['sharpe']:.2f} | {te['max_dd']:.0%} | {tr['pf']:.2f} | {tr['cagr']:.1%} | {tr['sharpe']:.2f} | "
                      f"{tr['max_dd']:.0%} | {te['trades_yr']:.0f} |")
        bte, btr = evaluate(bh, closes, mk, TEST), evaluate(bh, closes, mk, TRAIN)
        md.append(f"| Buy & hold (equal weight) | | | | {bte['cagr']:.1%} | {bte['sharpe']:.2f} | {bte['max_dd']:.0%} | | "
                  f"{btr['cagr']:.1%} | {btr['sharpe']:.2f} | {btr['max_dd']:.0%} | |")
        md.append("")
        if mk == "EGX":
            idxr = closes.pct_change(fill_method=None).clip(-0.5, 0.5).mean(axis=1).loc["2010":]
            ram = pd.Series(False, index=idxr.index)
            for y in range(1431, 1449):
                try:
                    s, e = Hijri(y, 9, 1).to_gregorian(), Hijri(y, 10, 1).to_gregorian()
                except Exception:
                    continue
                ram |= (idxr.index >= pd.Timestamp(s.isoformat())) & (idxr.index < pd.Timestamp(e.isoformat()))
            r_in, r_out = idxr[ram], idxr[~ram]
            t = (r_in.mean() - r_out.mean()) / np.sqrt(r_in.var() / len(r_in) + r_out.var() / len(r_out))
            yrs = idxr.groupby(idxr.index.year)
            win = sum(1 for y, g in yrs if ram[g.index].any() and g[ram[g.index]].mean() > g[~ram[g.index]].mean())
            n_y = sum(1 for y, g in yrs if ram[g.index].any())
            md += ["### Ramadan effect (equal-weight halal EGX index, 2010-today)", "",
                   f"Average daily return in Ramadan {r_in.mean():+.3%} vs {r_out.mean():+.3%} on other days "
                   f"(t-stat {t:.2f}); Ramadan beat the rest of the year in {win} of {n_y} years.", ""]
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
