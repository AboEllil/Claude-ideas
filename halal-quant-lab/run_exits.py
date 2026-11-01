"""The user's system on US halal stocks, with better exits (pre-registered rules).

    python run_exits.py

Entry (decided at the close): AlgoAlpha ML Adaptive SuperTrend green arrow AND Squeeze momentum
bright green (> 0 and rising). High-confidence version: also a Lorentzian green arrow in the last
5 bars.
Exits:
  X1 red arrow            - sell when the SuperTrend turns red (the user's current exit)
  X2 trail 3xATR          - sell when the close falls 3 x ATR14 below the highest close since entry,
                            or on the red arrow, whichever comes first
  X3 trail 2xATR          - same with 2 x ATR14
  X4 half at +3ATR        - sell half when the close reaches entry + 3 x ATR14 (ATR at entry),
                            hold the rest until the red arrow
Positions may be fractional (X4). Weights decided at the close trade at the next close; 5 bps per side.
Portfolio: capital split equally over stocks with a position (max 10% each, scaled by the fraction held).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import tv
from lab.data import load_prices
from lab.metrics import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "exits"
START, COST, CAP = "2010-01-01", 0.0005, 0.10
PERIODS = {"2010-2018": ("2010", "2018"), "2019-today": ("2019", "2100"), "2010-today": ("2010", "2100")}
ENTRIES = {"Your rule": False, "High confidence": True}
EXITS = ["X1 red arrow", "X2 trail 3xATR", "X3 trail 2xATR", "X4 half at +3ATR"]


def positions(o, h, l, c):
    st = tv.adaptive_supertrend(o, h, l, c)[0]
    _, mom = tv.squeeze(o, h, l, c)
    lpos, _ = tv.lorentzian(o, h, l, c)
    a = tv.atr(h, l, c, 14)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]
    larrow5 = pd.Series(larrow).rolling(6, min_periods=1).max().to_numpy() > 0
    out = {}
    for en, hc in ENTRIES.items():
        entry = flip & bright & (larrow5 if hc else True) & ~np.isnan(a)
        for ex in EXITS:
            pos = np.zeros(len(c))
            hi = e_px = e_atr = 0.0
            for t in range(1, len(c)):
                p = pos[t - 1]
                if p > 0:
                    hi = max(hi, c[t])
                    if st[t] == 0:
                        p = 0
                    elif ex == "X2 trail 3xATR" and c[t] < hi - 3 * a[t]:
                        p = 0
                    elif ex == "X3 trail 2xATR" and c[t] < hi - 2 * a[t]:
                        p = 0
                    elif ex == "X4 half at +3ATR" and p == 1 and c[t] >= e_px + 3 * e_atr:
                        p = 0.5
                if p == 0 and entry[t]:
                    p, hi, e_px, e_atr = 1.0, c[t], c[t], a[t]
                pos[t] = p
            out[f"{en} | {ex}"] = pos
    out["Buy & hold"] = np.ones(len(c))
    return out


def one(args):
    tk, df = args
    df = df.dropna()
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    return tk, pd.DataFrame(positions(o, h, l, c), index=df.index)


def portfolio(P: dict, rets: pd.DataFrame, name, cap=CAP):
    """Weights: each held stock gets fraction x min(1/k, cap), k = number of stocks held."""
    F = pd.DataFrame({t: P[t][name] for t in rets.columns}).reindex(rets.index).fillna(0)
    k = (F > 0).sum(axis=1).replace(0, np.nan)
    W = F.mul(np.minimum(1 / k, cap), axis=0).fillna(0)
    r = (W.shift(1) * rets.fillna(0)).sum(axis=1) - COST * W.diff().abs().sum(axis=1).fillna(0)
    return r, float((F > 0).sum(axis=1).mul(cap).clip(upper=1).loc[START:].mean())


def trade_stats(P, C, name, tks):
    res = []
    for t in tks:
        p = P[t][name].reindex(C.index).fillna(0).to_numpy()
        c = C[t].to_numpy()
        m = C.index >= START
        i = 0
        while i < len(p):
            if m[i] and p[i] > 0 and (i == 0 or p[i - 1] == 0):
                j, val, w = i, 0.0, 1.0
                e = c[i]
                while j + 1 < len(p) and p[j + 1] > 0:
                    if p[j + 1] < p[j]:                       # partial sale
                        val += (p[j] - p[j + 1]) * c[j + 1] / e
                    j += 1
                val += p[j] * (c[min(j + 1, len(c) - 1)] / e)
                res.append((val - 1, j - i + 1))
                i = j + 1
            else:
                i += 1
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tickers = list(pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0).index[:100])
    px = load_prices(tickers)
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")})) for t in tickers]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        P = dict(ex.map(one, jobs))
    C = px["Close"][tickers].loc["2009-01-01":]
    rets = C.pct_change(fill_method=None)
    years = (C.index[-1] - pd.Timestamp(START)).days / 365.25
    md = ["# Your system on US halal stocks: which exit works best?\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Entry: AlgoAlpha green arrow + Squeeze BRIGHT green "
          "(high confidence: + Lorentzian arrow in the last 5 days). Daily bars, 5 bps per side, max 10% per stock.\n"
          "Cells: CAGR / Sharpe / max drawdown.\n"]
    for label, tks in (("Top 20", tickers[:20]), ("Ranks 21-100 (fair test)", tickers[20:])):
        md += [f"## {label}", "", "| Strategy | " + " | ".join(PERIODS) + " | Invested | Trades/yr | Win rate | Avg trade | Avg days |",
               "|---|---|---|---|---|---|---|---|---|"]
        for name in ["Buy & hold"] + [f"{e} | {x}" for e in ENTRIES for x in EXITS]:
            r, inv = portfolio(P, rets[tks], name, cap=1.0 if name == "Buy & hold" else CAP)
            r = r.loc[START:]
            cells = " | ".join(f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / "
                               f"{stats(r.loc[a:b])['max_dd']:.0%}" for a, b in PERIODS.values())
            if name == "Buy & hold":
                md.append(f"| **{name}** | {cells} | 100% | | | | |")
                continue
            tr = trade_stats(P, C[tks], name, tks)
            tr = [(x, d) for x, d in tr if np.isfinite(x)]
            rr = np.array([x for x, _ in tr])
            md.append(f"| {name} | {cells} | {inv:.0%} | {len(tr) / years:.0f} | {np.mean(rr > 0):.0%} | "
                      f"{rr.mean():+.1%} | {np.mean([d for _, d in tr]):.0f} |")
        md.append("")
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
