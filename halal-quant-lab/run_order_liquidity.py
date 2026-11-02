"""Three pre-registered tests: the simple signal order, a liquidity (risk-on) filter and a whale-footprint filter.

    SEC_USER_AGENT="Name email" python run_order_liquidity.py

Signals and trades: the same as run_ml_signals2.py (dashboard rule + the user's arrow/squeeze rule; sell
half at +2 ATR, then stop at entry, else the rule's exit; costs; decided at the close, bought next close).
Two periods: 2016-2020 and 2021-today. Nothing here was tuned; every number below was fixed in advance.

A. SIMPLE ORDER (seen once on 2021-today data in ml_signals2 -> 2016-2020 is the untouched check)
   Fixed slots (US 10, EGX 8, crypto 5; 1/N of capital each). New signals fill free slots in this order:
   weekly SuperTrend green first, then the highest 60-day return. Baseline: random order (50 runs).
   PASS in a market: higher Sharpe AND higher CAGR than the random average in BOTH periods.
   Overall PASS: US and EGX both pass. (Crypto and 5 / 20 slots are reported only.)
B. LIQUIDITY FILTER - "risk-on" when at least 2 of 3 hold at the signal close:
   US dollar index (DX-Y.NYB) below its 100-day average; HYG/IEF ratio above its 100-day average
   (credit appetite - bond ETFs used only as a gauge, never traded); VIX below its 100-day average.
   New entries only when risk-on.
C. WHALE FOOTPRINT FILTER - Chaikin Money Flow (20 days) > 0.05 at the signal close
   (volume concentrated on closes near the day's high = accumulation).
   B and C PASS in a market if, in BOTH periods, the filtered signals have a win rate >= +3 points,
   a higher average trade, and a higher Sharpe in the equal-weight portfolio (max 10% each) than all
   signals. B passes overall if it passes in US and crypto (global liquidity matters most there);
   C passes overall if it passes in at least 2 of the 3 markets.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

import run_ml_signals2 as v2
from lab.metrics import stats
from lab.universe import DATA
from run_ml_signals import COST, MARKETS, trade_stats
from run_signal_lab import load

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "order_liquidity"
PERIODS = {"2016-2020": ("2016-01-01", "2020-12-31"), "2021-today": ("2021-01-01", "2100-01-01")}


def returns(trades, idx_map, closes, market, n_slots=None):
    """Daily portfolio returns. n_slots -> each position 1/N; else equal weight, max 10% each."""
    pos = {}
    for tk, g in trades.groupby("ticker"):
        p = np.zeros(len(idx_map[tk]))
        for _, e in g.iterrows():
            start, frac = int(e.t), 1.0
            for f, j in e.legs:
                p[start:j] = np.maximum(p[start:j], frac)
                start, frac = j, frac - f
        pos[tk] = pd.Series(p, index=idx_map[tk])
    if not pos:
        return pd.Series(0.0, index=closes.index)
    P = pd.DataFrame(pos).reindex(closes.index).fillna(0).shift(1).fillna(0)
    if n_slots:
        W = P / n_slots
    else:
        k = (P > 0).sum(axis=1).replace(0, np.nan)
        W = P.mul(np.minimum(1 / k, 0.10), axis=0).fillna(0)
    R = closes[P.columns].pct_change(fill_method=None).fillna(0)
    return (W.shift(1) * R).sum(axis=1) - COST[market] * W.diff().abs().sum(axis=1).fillna(0)


def pstats(r, market, period):
    a, b = PERIODS[period]
    return stats(r.loc[a:b], year=365 if market == "Crypto" else 252)


def liquidity_on():
    raw = yf.download(["DX-Y.NYB", "HYG", "IEF", "^VIX"], start="2012-01-01", auto_adjust=True, progress=False)["Close"]
    raw = raw.ffill()
    dxy, vix, cr = raw["DX-Y.NYB"], raw["^VIX"], raw["HYG"] / raw["IEF"]
    votes = ((dxy < dxy.rolling(100).mean()).astype(int) + (cr > cr.rolling(100).mean()).astype(int)
             + (vix < vix.rolling(100).mean()).astype(int))
    return (votes >= 2).where(dxy.rolling(100).mean().notna() & cr.rolling(100).mean().notna()), raw


def cmf_table(jobs):
    out = {}
    for tk, df, mk, _ in jobs:
        d = df.dropna(subset=["Open", "High", "Low", "Close"])
        h, l, c, v = d.High, d.Low, d.Close, d.Volume.fillna(0)
        mfm = ((c - l) - (h - c)) / (h - l).where(h > l)
        out[tk] = (mfm.fillna(0) * v).rolling(20).sum() / v.rolling(20).sum()
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cache = DATA / "ml_signals2_events.pkl"
    if cache.exists():
        ev, idx_map, closes = pd.read_pickle(cache)
    else:
        ev, res, closes = v2.build()
        idx_map = {r[0]: r[2] for r in res}
        pd.to_pickle((ev, idx_map, closes), cache)
    ev = ev[ev.hit.notna() & (ev.date >= "2016-01-01")].copy()
    liq, raw = liquidity_on()
    # liquidity is a US-hours series; a signal on day d uses the value at d (EGX: last US close on/before d)
    ev["liq_on"] = liq.reindex(liq.index.union(ev.date.unique())).ffill().reindex(ev.date).to_numpy()
    cmf = cmf_table(load())
    ev["cmf20"] = [cmf[t].get(d, np.nan) if t in cmf else np.nan for t, d in zip(ev.ticker, ev.date)]

    md = ["# Signal order, liquidity filter and whale-footprint filter (pre-registered)\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev):,} closed trades from 2016 (dashboard rule + the user's "
          "rule; half at +2 ATR then stop at entry; costs included). Rules and pass conditions were fixed before "
          "the run (see run_order_liquidity.py).\n"]

    # ---------------- A. simple order ----------------
    md += ["## A. Simple order vs random order (fixed slots)", "",
           "| Market | Slots | Period | Simple: CAGR / Sharpe / maxDD | Random (avg of 50): CAGR / Sharpe / maxDD | Simple better? |",
           "|---|---|---|---|---|---|"]
    a_pass = {}
    for mk in MARKETS:
        d = ev[ev.market == mk].sort_values("source").drop_duplicates(["ticker", "date"]).copy()
        d["simple"] = d.weekly_up * 10 + d.ret60.fillna(-1)
        for n in sorted({5, v2.SLOTS[mk], 20}):
            ch = v2.slot_pick(d, "simple", n)
            r_s = returns(ch, idx_map, closes[mk], mk, n)
            rnd = [returns(v2.slot_pick(d, None, n, rng=s), idx_map, closes[mk], mk, n) for s in range(50)]
            for per in PERIODS:
                s = pstats(r_s, mk, per)
                rs = [pstats(r, mk, per) for r in rnd]
                rc, rsh, rdd = (np.mean([x[k] for x in rs]) for k in ("cagr", "sharpe", "max_dd"))
                better = s["cagr"] > rc and s["sharpe"] > rsh
                if n == v2.SLOTS[mk]:
                    a_pass[(mk, per)] = better
                md.append(f"| {mk} | {n}{' (main)' if n == v2.SLOTS[mk] else ''} | {per} | {s['cagr']:.1%} / {s['sharpe']:.2f} / "
                          f"{s['max_dd']:.0%} | {rc:.1%} / {rsh:.2f} / {rdd:.0%} | {'yes' if better else 'no'} |")
            print(f"  A {mk} {n} slots done", flush=True)
    a_mk = {mk: all(a_pass[(mk, p)] for p in PERIODS) for mk in MARKETS}
    md += ["", f"**A verdict: {'PASS' if a_mk['US'] and a_mk['EGX'] else 'FAIL'}** - US "
               f"{'passes' if a_mk['US'] else 'fails'}, EGX {'passes' if a_mk['EGX'] else 'fails'} "
               f"(crypto, info only: {'better' if a_mk['Crypto'] else 'not better'} in both periods).", ""]

    # ---------------- B and C. filters ----------------
    def filter_block(title, mask_col, cond, markets_needed, need):
        nonlocal md
        md += [f"## {title}", "", "| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        ok = {}
        for mk in MARKETS:
            d_all = ev[ev.market == mk]
            res_mk = []
            for per, (a, b) in PERIODS.items():
                d = d_all[(d_all.date >= a) & (d_all.date <= b)]
                f = d[cond(d)]
                out = {}
                for name, x in (("All", d), ("Filter on", f), ("Filter off", d[~cond(d)])):
                    t = trade_stats(x)
                    s = pstats(returns(x, idx_map, closes[mk], mk), mk, per)
                    out[name] = (t, s)
                    md.append(f"| {mk} | {per} | {name} | {t['n']} | {t['win']:.0%} | {t['avg']:+.1%} | {t['pf']:.2f} | "
                              f"{s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} |")
                (ta, sa), (tf, sf) = out["All"], out["Filter on"]
                res_mk.append(tf["n"] >= 20 and tf["win"] - ta["win"] >= 0.03 and tf["avg"] > ta["avg"]
                              and sf["sharpe"] > sa["sharpe"])
            ok[mk] = all(res_mk)
        if markets_needed:
            verdict = all(ok[m] for m in markets_needed)
        else:
            verdict = sum(ok.values()) >= need
        md += ["", f"**Verdict: {'PASS' if verdict else 'FAIL'}** - passes in: "
                   f"{', '.join(m for m in MARKETS if ok[m]) or 'no market'}.", ""]

    filter_block("B. Liquidity (risk-on) filter: 2 of 3 of weak dollar, credit appetite, calm VIX", "liq_on",
                 lambda d: d.liq_on.fillna(0) > 0.5, ["US", "Crypto"], None)
    filter_block("C. Whale-footprint filter: Chaikin Money Flow (20) > 0.05", "cmf20",
                 lambda d: d.cmf20.fillna(-1) > 0.05, None, 2)
    on = ev.drop_duplicates("date").set_index("date").liq_on
    md += [f"Risk-on share of signal days: {on.mean():.0%}. Signals with CMF > 0.05: {(ev.cmf20 > 0.05).mean():.0%}."]
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
