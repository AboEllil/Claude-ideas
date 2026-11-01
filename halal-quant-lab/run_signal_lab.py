"""Signal lab: which filters make the user's signals more accurate AND more profitable?

    python run_signal_lab.py

Markets (daily bars): US halal stocks (top 100 + 150 sampled mid caps), halal EGX stocks, halal crypto.
Base system (V0): AlgoAlpha ML Adaptive SuperTrend green arrow + Squeeze momentum bright green;
every version exits on the red arrow. Signals are decided at the close and traded at the NEXT close.
Train = 2016-2020 (choices are made here), Test = 2021-today (judged here, never used to choose).

Versions
  V0 arrow + bright squeeze (the user's rule)            V6 V0 + volume >= 1.5x its 20-day average
  V1 V0 + Lorentzian arrow (last 5 days)                  V7 V0 + weekly SuperTrend also green
  V2 3 of 4: arrow(3d), bright squeeze, Lorentzian(5d),   V8 V0 + squeeze built >= 6 of last 20 days
     order-block retest(5d); SuperTrend green                    and ADX(14) > 20
  V3 V0 + order-block retest (last 5 days)                V9 V0, then buy the first dip to within 1 ATR
  V4 V0 + market above its 200-day average                       of the SuperTrend line (10 days max)
  V5 V0 + stock beat its market over 126 days             V10 V0 + the 2 filters that helped most in TRAIN
Settings sweep (V0): SuperTrend factor 2-4, ATR 7/10/14, Squeeze length 14/20 - best in TRAIN, shown in TEST.
"""
import os
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.egx import halal_egx
from lab.metrics import stats
from lab.universe import DATA

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "signal_lab"
TRAIN, TEST = ("2016", "2020"), ("2021", "2100")
COST = {"US": 0.0005, "EGX": 0.0025, "Crypto": 0.001}
MIN_VALUE = {"US": 5e6, "EGX": 1e6, "Crypto": 5e6}
FILTERS = ["lor", "ob", "mkt", "rs", "vol", "weekly", "sqz"]
SWEEP = [(f, a, s) for f in (2.0, 2.5, 3.0, 3.5, 4.0) for a in (7, 10, 14) for s in (14, 20)]


def hold_until_red(entry, st):
    pos = np.zeros(len(st))
    for t in range(1, len(st)):
        pos[t] = (1.0 if st[t] == 1 else 0.0) if pos[t - 1] else (1.0 if entry[t] and st[t] == 1 else 0.0)
    return pos


def recent(x, n):
    return pd.Series(x.astype(float)).rolling(n, min_periods=1).max().to_numpy() > 0


def supertrend_set(h, l, c, atr_len, factor):
    a = tv._kmeans_atr(tv.atr(h, l, c, atr_len), 100, 0.75, 0.5, 0.25)
    st = (tv.supertrend(h, l, c, a, factor) == 1).astype(float)
    src = (h + l) / 2
    lo = src - factor * a
    plo = np.nan
    for t in range(len(c)):
        if np.isnan(a[t]):
            continue
        if not np.isnan(plo):
            lo[t] = lo[t] if (lo[t] > plo or c[t - 1] < plo) else plo
        plo = lo[t]
    return st, lo


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
    b = bench.reindex(idx).ffill().to_numpy(float)
    st, line = supertrend_set(h, l, c, 10, 3.0)
    sq_on, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    lpos, _ = tv.lorentzian(o, h, l, c)
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]
    _, _, _, zb, zt, _, _ = tv.smc_state(h, l, c, 10, False)
    ob_touch = ~np.isnan(zb) & (l <= zt * 1.01) & (c >= zb)
    a14 = tv.atr(h, l, c, 14)
    value = pd.Series(c * v).rolling(20).median().to_numpy()
    liquid = value >= MIN_VALUE[market]
    vol_ratio = v / pd.Series(v).rolling(20).mean().shift(1).to_numpy()
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = tv.rma(tv.tr(h, l, c), 14)
    pdi, mdi = 100 * tv.rma(pdm, 14) / trs, 100 * tv.rma(mdm, 14) / trs
    adx = tv.rma(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
    bsma = pd.Series(b).rolling(200).mean().to_numpy()
    r126 = c / pd.Series(c).shift(126).to_numpy() - 1
    b126 = b / pd.Series(b).shift(126).to_numpy() - 1
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    if len(wk) > 120:
        wst = tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0]
        weekly = pd.Series(wst, index=wk.index).shift(1).reindex(idx, method="ffill").fillna(0).to_numpy() > 0.5
    else:
        weekly = np.zeros(len(c), bool)

    f = {"lor": recent(larrow, 5), "ob": recent(ob_touch, 5), "mkt": np.nan_to_num(b) > np.nan_to_num(bsma, nan=np.inf),
         "rs": np.nan_to_num(r126 - b126, nan=-1) > 0, "vol": np.nan_to_num(vol_ratio) >= 1.5, "weekly": weekly,
         "sqz": (pd.Series(sq_on.astype(float)).rolling(20).sum().to_numpy() >= 6) & (np.nan_to_num(adx) > 20)}
    base = flip & bright & liquid
    entries = {"V0": base, "V1": base & f["lor"], "V3": base & f["ob"], "V4": base & f["mkt"],
               "V5": base & f["rs"], "V6": base & f["vol"], "V7": base & f["weekly"], "V8": base & f["sqz"]}
    count = recent(flip, 3).astype(int) + bright + f["lor"] + f["ob"]
    entries["V2"] = (count >= 3) & (st == 1) & liquid
    # V9: after a V0 setup, buy the first dip to within 1 ATR of the SuperTrend line, within 10 days
    v9 = np.zeros(len(c), bool)
    armed = -1
    for t in range(len(c)):
        if base[t]:
            armed = t
        if armed >= 0 and t - armed <= 10 and st[t] == 1 and l[t] <= line[t] + a14[t]:
            v9[t], armed = True, -1
        elif armed >= 0 and (t - armed > 10 or st[t] == 0):
            armed = -1
    entries["V9"] = v9
    out = {k: hold_until_red(e, st) for k, e in entries.items()}
    out["_filters"] = f
    out["_base"] = base
    out["_st"] = st
    # settings sweep (V0 only)
    sweep = {}
    sq_cache = {}
    for fac, al, sl in SWEEP:
        st2, _ = supertrend_set(h, l, c, al, fac)
        if sl not in sq_cache:
            _, mm = tv.squeeze(o, h, l, c, length=sl)
            mm = np.nan_to_num(mm)
            sq_cache[sl] = (mm > 0) & np.r_[False, mm[1:] > mm[:-1]]
        fl = np.r_[False, (st2[1:] == 1) & (st2[:-1] == 0)]
        sweep[(fac, al, sl)] = hold_until_red(fl & sq_cache[sl] & liquid, st2)
    return tk, market, idx, c, out, sweep


def evaluate(pos_map, closes, market, period):
    """Portfolio (equal weight over holdings, max 10% each, trades at the next close) + trade stats."""
    P = pd.DataFrame(pos_map).reindex(closes.index).fillna(0).shift(1).fillna(0)       # executed next close
    R = closes.pct_change(fill_method=None).fillna(0)
    k = (P > 0).sum(axis=1).replace(0, np.nan)
    W = P.mul(np.minimum(1 / k, 0.10), axis=0).fillna(0)
    r = (W.shift(1) * R).sum(axis=1) - COST[market] * W.diff().abs().sum(axis=1).fillna(0)
    a, b = period
    r = r.loc[a:b]
    year = 365 if market == "Crypto" else 252
    s = stats(r, year=year)
    tr = []
    for t in P.columns:
        p = P[t].loc[a:b].to_numpy()
        c = closes[t].loc[a:b].to_numpy()
        i = 0
        while i < len(p):
            if p[i] > 0 and (i == 0 or p[i - 1] == 0):
                j = i
                while j + 1 < len(p) and p[j + 1] > 0:
                    j += 1
                e, x = c[i - 1] if i else c[i], c[j]
                if np.isfinite(e) and np.isfinite(x) and e > 0:
                    tr.append((x / e - 1 - 2 * COST[market], j - i + 1))
                i = j + 1
            else:
                i += 1
    rr = np.array([x for x, _ in tr]) if tr else np.array([0.0])
    gains, losses = rr[rr > 0].sum(), -rr[rr < 0].sum()
    yrs = max((r.index[-1] - r.index[0]).days / 365.25, 0.5) if len(r) else 1
    return {"trades_yr": len(tr) / yrs, "win": float((rr > 0).mean()) if tr else np.nan,
            "avg": float(rr.mean()) if tr else np.nan, "pf": gains / losses if losses > 0 else np.nan,
            "whipsaw": float(np.mean([(x < 0) and d <= 5 for x, d in tr])) if tr else np.nan,
            "cagr": s["cagr"], "sharpe": s["sharpe"], "max_dd": s["max_dd"], "n": len(tr)}


def load():
    rank = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    mid = pd.read_csv(ROOT / "reports" / "universe" / "midcap_screen.csv")
    mid = mid[mid.compliant & (mid.industry != "Aerospace & Defense")]
    random.seed(1)
    us = list(rank.index[:100]) + random.sample(sorted(mid.ticker), 150)
    import json
    crypto = [c["symbol"] for c in json.loads((ROOT / "reports" / "universe" / "crypto_list.json").read_text())]
    cache = DATA / "lab_prices.pkl"
    if cache.exists():
        px = pd.read_pickle(cache)
    else:
        raw = yf.download(us + crypto + ["SPY"], start="2014-01-01", auto_adjust=True, progress=False, threads=True,
                          group_by="column")
        px = {f: raw[f] for f in ("Open", "High", "Low", "Close", "Volume")}
        pd.to_pickle(px, cache)
    egx = pd.read_pickle(DATA / "egx_prices.pkl")
    egx_t = [t + ".CA" for t in halal_egx() if t + ".CA" in egx["Close"]]
    egx_index = (1 + egx["Close"][egx_t].pct_change(fill_method=None).clip(-0.5, 0.5).mean(axis=1).fillna(0)).cumprod()
    jobs = []
    for t in us:
        if t in px["Close"]:
            jobs.append((t, pd.DataFrame({f: px[f][t] for f in px}), "US", px["Close"]["SPY"].ffill()))
    for t in crypto:
        if t in px["Close"]:
            jobs.append((t, pd.DataFrame({f: px[f][t] for f in px}), "Crypto", px["Close"]["BTC-USD"].ffill()))
    for t in egx_t:
        jobs.append((t, pd.DataFrame({f: egx[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}), "EGX", egx_index))
    return jobs


def fmt_row(name, s):
    return (f"| {name} | {s['trades_yr']:.0f} | {s['win']:.0%} | {s['avg']:+.1%} | {s['pf']:.2f} | {s['whipsaw']:.0%} | "
            f"{s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} |")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = load()
    print(f"{len(jobs)} assets")
    res = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i, r in enumerate(ex.map(analyse, jobs, chunksize=4), 1):
            if r:
                res.append(r)
            if i % 50 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    md = ["# Signal lab: more accurate AND more profitable signals\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Exit for every version: AlgoAlpha red arrow. Trades at the next "
          "close, costs per side US 0.05% / EGX 0.25% / crypto 0.10%, max 10% per position, liquid assets only. "
          "**Choices are made on TRAIN (2016-2020); TEST (2021-today) is the honest result.**\n",
          "Columns: trades per year, win rate, average trade, profit factor (gains / losses), whipsaw (losing trades "
          "closed within 5 days), portfolio CAGR, Sharpe, max drawdown.\n"]
    names = {"V0": "V0 arrow + bright squeeze (yours)", "V1": "V1 + Lorentzian arrow", "V2": "V2 3 of 4 (arrow, squeeze, Lorentzian, OB)",
             "V3": "V3 + order-block retest", "V4": "V4 + market uptrend", "V5": "V5 + stronger than market",
             "V6": "V6 + volume surge", "V7": "V7 + weekly trend green", "V8": "V8 + real squeeze + ADX>20",
             "V9": "V9 + buy the pullback", "V10": "V10 V0 + best 2 filters (from train)"}
    summary = {}
    for market in ("US", "EGX", "Crypto"):
        rs = [r for r in res if r[1] == market]
        if not rs:
            continue
        closes = pd.DataFrame({r[0]: pd.Series(r[3], index=r[2]) for r in rs}).sort_index()
        pos = {vname: {r[0]: pd.Series(r[4][vname], index=r[2]) for r in rs} for vname in names if vname != "V10"}
        # V10: rank single filters by TRAIN profit factor x CAGR improvement over V0, keep the best 2
        base_tr = evaluate(pos["V0"], closes, market, TRAIN)
        gains = {}
        for fl in FILTERS:
            pm = {r[0]: pd.Series(hold_until_red(r[4]["_base"] & r[4]["_filters"][fl], r[4]["_st"]), index=r[2]) for r in rs}
            s = evaluate(pm, closes, market, TRAIN)
            gains[fl] = (s["sharpe"] - base_tr["sharpe"]) if s["n"] >= 30 else -9
        best2 = sorted(gains, key=gains.get, reverse=True)[:2]
        pos["V10"] = {r[0]: pd.Series(hold_until_red(r[4]["_base"] & r[4]["_filters"][best2[0]] & r[4]["_filters"][best2[1]],
                                                     r[4]["_st"]), index=r[2]) for r in rs}
        bh = {t: pd.Series(1.0, index=closes.index).where(closes[t].notna(), 0.0) for t in closes.columns}
        md += [f"## {market} ({len(rs)} assets)", "",
               f"V10 uses the two filters with the best TRAIN Sharpe gain: **{best2[0]} + {best2[1]}**.", "",
               "| Version (TEST 2021-today) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |",
               "|---|---|---|---|---|---|---|---|---|"]
        rows = {}
        for vname, label in names.items():
            rows[vname] = (evaluate(pos[vname], closes, market, TEST), evaluate(pos[vname], closes, market, TRAIN))
            md.append(fmt_row(label, rows[vname][0]))
        b_te = evaluate(bh, closes, market, TEST)
        md.append(f"| Buy & hold (equal weight) | | | | | | {b_te['cagr']:.1%} | {b_te['sharpe']:.2f} | {b_te['max_dd']:.0%} |")
        md += ["", "Same versions in TRAIN (2016-2020), for consistency:", "",
               "| Version (TRAIN) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |",
               "|---|---|---|---|---|---|---|---|---|"]
        md += [fmt_row(names[vn], rows[vn][1]) for vn in names]
        # settings sweep
        sw_train = {}
        for key in SWEEP:
            pm = {r[0]: pd.Series(r[5][key], index=r[2]) for r in rs}
            sw_train[key] = (evaluate(pm, closes, market, TRAIN), pm)
        best = max(sw_train, key=lambda k: sw_train[k][0]["sharpe"] if sw_train[k][0]["n"] >= 30 else -9)
        top5 = sorted(sw_train, key=lambda k: -sw_train[k][0]["sharpe"])[:5]
        md += ["", "### Settings sweep (V0 rule), chosen on TRAIN Sharpe", "",
               "| Settings (factor / ATR / squeeze) | TRAIN Sharpe | TEST trades/yr | TEST win | TEST PF | TEST CAGR | TEST Sharpe | TEST Max DD |",
               "|---|---|---|---|---|---|---|---|"]
        for key in [(3.0, 10, 20)] + [k for k in top5 if k != (3.0, 10, 20)]:
            te = evaluate(sw_train[key][1], closes, market, TEST)
            tag = " (default)" if key == (3.0, 10, 20) else " **(best in train)**" if key == best else ""
            md.append(f"| {key[0]:g} / {key[1]} / {key[2]}{tag} | {sw_train[key][0]['sharpe']:.2f} | {te['trades_yr']:.0f} | "
                      f"{te['win']:.0%} | {te['pf']:.2f} | {te['cagr']:.1%} | {te['sharpe']:.2f} | {te['max_dd']:.0%} |")
        md.append("")
        summary[market] = (rows, best2, best)
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
