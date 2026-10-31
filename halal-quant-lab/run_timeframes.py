"""Same TradingView strategies on 1-hour, 4-hour and weekly bars.

    python run_timeframes.py

1h  : Yahoo hourly bars (about the last 730 days), evaluated from 2024-06-01 after warm-up.
4h  : built from the hourly bars the way TradingView splits a US stock session
      (09:30-13:30 and 13:30-16:00), same evaluation window.
1W  : weekly bars (Friday close) from daily data, evaluated 2010-today.
All indicator settings stay at their published defaults (counted in bars). Decisions at
the bar close, trades at the next bar's open, 5 bps per side, long-only. Intraday
returns are compounded to daily before computing statistics.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.data import load_prices
from lab.metrics import stats
from lab.single import run_strategy
from lab.universe import DATA
from run_tv import buy_hold, market_ok
from run_tv_rotation import rotate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "tv"
FIELDS = ("Open", "High", "Low", "Close")

STRATS = {
    "Buy & hold": (buy_hold, {}),
    "Lorentzian Classification (TV)": (tv.lorentzian, {}),
    "Lorentzian, fixed labels": (tv.lorentzian, {"fixed": True}),
    "ML Adaptive SuperTrend (TV)": (tv.adaptive_supertrend, {}),
    "Squeeze Momentum (TV)": (tv.squeeze_strategy, {}),
    "Smart Money Concepts (OB/FVG)": (tv.smc_strategy, {}),
    "CONFLUENCE (ours)": (tv.confluence, {"mkt": True, "use_market": False}),
}


def hourly(tickers):
    cache = DATA / "hourly.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    raw = yf.download(tickers, period="729d", interval="1h", auto_adjust=True, progress=False, threads=True)
    px = {f: raw[f] for f in FIELDS}
    pd.to_pickle(px, cache)
    return px


def to_4h(df):
    """TradingView 4h session bars for US stocks: 09:30-13:30 and 13:30-16:00."""
    key = df.index.normalize().astype("int64") // 10 ** 9 * 10 + (df.index.hour >= 13)
    g = df.groupby(key)
    out = pd.DataFrame({"Open": g.Open.first(), "High": g.High.max(), "Low": g.Low.min(), "Close": g.Close.last()})
    out.index = g.apply(lambda x: x.index[0])
    return out


def to_weekly(df):
    return df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()


def one(args):
    tk, df, mkt, start = args
    out = {}
    for name, (fn, kw) in STRATS.items():
        kw = dict(kw)
        if kw.pop("mkt", False):
            kw["mkt_ok"] = mkt
        r, expo, trs = run_strategy(df, fn, start, **kw)
        pos = None
        if name in ("ML Adaptive SuperTrend (TV)", "CONFLUENCE (ours)"):
            d = df.dropna()
            res = fn(*(d[f].to_numpy(float) for f in FIELDS),
                     **{k: (v.reindex(d.index).ffill().to_numpy(float) if isinstance(v, pd.Series) else v)
                        for k, v in kw.items()})
            pos = pd.Series(res[0], index=d.index)
        out[name] = (r, expo, trs, pos)
    return tk, out


def daily(r):
    """Compound intraday bar returns into daily returns."""
    idx = r.index.tz_localize(None) if r.index.tz is not None else r.index
    return (1 + pd.Series(r.to_numpy(), index=idx)).groupby(idx.normalize()).prod() - 1


def run_tf(label, bars: dict, mkt, start, year, intraday, tickers20, tickers80):
    jobs = [(t, bars[t], mkt, start) for t in tickers20 + tickers80 if t in bars]
    res = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for tk, out in ex.map(one, jobs):
            res[tk] = out
    conv = daily if intraday else (lambda x: x)
    yr = 252 if intraday else year
    lines = []
    for uni, tks in (("Top 20", tickers20), ("Ranks 21-100", tickers80)):
        tks = [t for t in tks if t in res]
        lines += [f"#### {label} - {uni}", "",
                  "| Strategy | CAGR | Sharpe | Max DD | Time in market | Trades/stock/yr | Win rate |",
                  "|---|---|---|---|---|---|---|"]
        span = None
        for name in STRATS:
            R = pd.DataFrame({t: conv(res[t][name][0]) for t in tks})
            p = R.mean(axis=1).fillna(0)
            span = span or (p.index[-1] - p.index[0]).days / 365.25
            s = stats(p, year=yr)
            expo = np.mean([res[t][name][1] for t in tks])
            trs = [x for t in tks for x in res[t][name][2]]
            n_tr = len(trs) / len(tks) / span
            win = f"{np.mean(np.array(trs) > 0):.0%}" if trs and name != "Buy & hold" else ""
            b = "**" if name.startswith("CONF") else ""
            lines.append(f"| {b}{name}{b} | {s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} | {expo:.0%} | "
                         f"{'' if name == 'Buy & hold' else f'{n_tr:.1f}'} | {win} |")
        # Capital rotation into active signals (the fix from run_tv_rotation.py)
        closes = pd.DataFrame({t: bars[t]["Close"] for t in tks}).sort_index()
        rets = closes.pct_change(fill_method=None)
        rets = rets[rets.index >= pd.Timestamp(start, tz=rets.index.tz)]
        for name, key in (("SuperTrend rotation", "ML Adaptive SuperTrend (TV)"), ("CONFLUENCE rotation", "CONFLUENCE (ours)")):
            on = pd.DataFrame({t: res[t][key][3] for t in tks}).reindex(rets.index)
            r = conv(rotate(on, rets))
            s = stats(r, year=yr)
            inv = float(np.minimum(on.fillna(0).sum(axis=1) * 0.10, 1).mean())
            lines.append(f"| {b}{name}{b} | {s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} | {inv:.0%} | | |")
        lines.append("")
    return lines


def main():
    ranking = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(ranking.index)[:100]
    t20, t80 = tickers[:20], tickers[20:]
    dpx = load_prices(tickers)
    mkt_d = market_ok(dpx["Close"]["SPY"].ffill()).shift(1)   # yesterday's value: known during today

    md = ["# Timeframe comparison: 1 hour, 4 hours, weekly", "",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Same rules and default settings as `REPORT.md` (daily). "
          "Long-only, next-bar-open execution, 5 bps per side. Intraday results compounded to daily for statistics.",
          "",
          "> 1h/4h cover only ~2.4 years of evaluation (Yahoo limit), one market regime - treat them as indicative.", ""]

    print("hourly data ...")
    hp = hourly(tickers)
    h1 = {t: pd.DataFrame({f: hp[f][t] for f in FIELDS}).dropna() for t in tickers if t in hp["Close"]}
    h1 = {t: d for t, d in h1.items() if len(d) > 500}
    mkt_i = lambda idx: pd.Series(mkt_d.reindex(idx.tz_localize(None).normalize()).to_numpy(), index=idx)  # noqa: E731
    any_idx = next(iter(h1.values())).index
    start_i = str(pd.Timestamp("2024-06-01", tz=any_idx.tz))
    print("1h ...")
    md += ["## 1 hour", ""] + run_tf("1h", h1, mkt_i(any_idx), start_i, 252 * 7, True, t20, t80)
    print("4h ...")
    h4 = {t: to_4h(d) for t, d in h1.items()}
    idx4 = next(iter(h4.values())).index
    md += ["## 4 hours", ""] + run_tf("4h", h4, mkt_i(idx4), start_i, 252 * 2, True, t20, t80)
    print("weekly ...")
    wk = {t: to_weekly(pd.DataFrame({f: dpx[f][t] for f in FIELDS}).dropna()) for t in tickers}
    mkt_w = mkt_d.resample("W-FRI").last()
    md += ["## Weekly (2010-today)", ""] + run_tf("1W", wk, mkt_w, "2010-01-01", 52, False, t20, t80)
    (OUT / "TIMEFRAMES.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
