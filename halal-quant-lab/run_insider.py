"""Does insider buying (SEC Form 4, free) improve the halal confluence strategy?

    export SEC_USER_AGENT="Your Name your@email.com"
    python run_insider.py

Pre-registered tests (rules and pass criteria fixed before any result was seen):
  E1 event study : after an insider open-market purchase >= $25k is filed, the stock's excess return
                   vs the equal-weight universe over 20/60/120 trading days (entry at the next close).
                   PASS if the 60-day mean excess return > 0 with t-stat > 2.
  E2 risk boost  : variant A, but 2% risk per trade (instead of 1%) when insiders bought in the
                   last 180 days.
  E3 filter      : variant A, new entries only in stocks with insider buying in the last 365 days.
  E2/E3 PASS on ranks 21-100 if Sharpe improves by >= 0.05 AND max drawdown is no more than 2 points
  worse, in BOTH 2010-2018 and 2019-today.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import risk_engine
from lab.data import load_prices
from lab.metrics import stats
from lab.sec_insider import buy_window, load_insider_buys
from run_tv import START, market_ok
from run_tv_rotation import signals

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "insider"
HALVES = {"2010-2018": ("2010", "2018"), "2019-today": ("2019", "2100")}
MIN_VALUE = 25_000


def event_study(buys, C, ew, horizons=(20, 60, 120)):
    b = buys[buys.value >= MIN_VALUE].sort_values("filing_date")
    rows = []
    for t, g in b.groupby("ticker"):
        if t not in C:
            continue
        last = None
        for d in g.filing_date.dropna().unique():
            d = pd.Timestamp(d)
            if last is not None and (d - last).days < 30:
                continue                          # one event per 30-day cluster
            last = d
            cluster = int(g[(g.filing_date >= d) & (g.filing_date <= d + pd.Timedelta(days=30))].owner.nunique())
            pos = C.index.searchsorted(d, side="right")      # first trading day after filing
            if pos >= len(C):
                continue
            r = {"ticker": t, "date": C.index[pos], "insiders": cluster,
                 "value": float(g[g.filing_date == d].value.sum())}
            p0 = C[t].iloc[pos]
            for h in horizons:
                if pos + h < len(C) and p0 > 0:
                    stock = C[t].iloc[pos + h] / p0 - 1
                    bench = (1 + ew.iloc[pos + 1:pos + h + 1]).prod() - 1
                    r[f"x{h}"] = stock - bench
            rows.append(r)
    return pd.DataFrame(rows)


def summarize(ev, horizons=(20, 60, 120)):
    out = []
    for h in horizons:
        x = ev[f"x{h}"].dropna()
        t = x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan
        out.append((h, len(x), x.mean(), x.median(), (x > 0).mean(), t))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rank = pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0)
    tickers = list(rank.index)[:100]
    print("SEC insider data ...")
    buys = load_insider_buys(tickers)
    print(f"  {len(buys)} open-market purchases, {buys.ticker.nunique()} stocks")
    px = load_prices(tickers)
    C_all = px["Close"][tickers]
    ew = C_all.pct_change(fill_method=None).mean(axis=1).fillna(0)

    md = [f"# Insider buying (SEC Form 4) as an add-on to the halal strategy\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. Source: SEC Insider Transactions Data Sets (free), "
          f"open-market purchases (code P) >= ${MIN_VALUE:,} by officers, directors or 10% owners, "
          f"filed {buys.filing_date.min():%Y-%m} to {buys.filing_date.max():%Y-%m}.\n",
          f"**{len(buys[buys.value >= MIN_VALUE])} qualifying purchases in {buys[buys.value >= MIN_VALUE].ticker.nunique()} "
          f"of the 100 stocks.** Large caps rarely see insider buying.\n"]

    # ---------------- E1 event study
    ev = event_study(buys, C_all, ew)
    ev.to_csv(OUT / "events.csv", index=False)
    md += ["## E1 - event study: excess return after insider buying (vs equal-weight halal universe)", "",
           "| Group | Horizon (days) | Events | Mean excess | Median excess | Beat universe | t-stat |",
           "|---|---|---|---|---|---|---|"]
    e1_pass = False
    groups = {"All events": ev, "Cluster buys (2+ insiders in 30 days)": ev[ev.insiders >= 2],
              "Since 2019": ev[ev.date >= "2019-01-01"]}
    for gname, g in groups.items():
        if len(g) < 3:
            md.append(f"| {gname} | - | {len(g)} | too few | | | |")
            continue
        for h, n, m, med, hit, t in summarize(g):
            md.append(f"| {gname} | {h} | {n} | {m:+.2%} | {med:+.2%} | {hit:.0%} | {t:.2f} |")
            if gname == "All events" and h == 60:
                e1_pass = m > 0 and t > 2
    md += ["", f"**E1 verdict: {'PASS' if e1_pass else 'FAIL'}** (rule: 60-day mean excess > 0 and t > 2)", ""]

    # ---------------- E2 / E3 strategy tests
    mkt = market_ok(px["Close"]["SPY"].ffill())
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        sig = dict(ex.map(signals, jobs))
    verdicts = {}
    for label, tks in (("Top 20", tickers[:20]), ("Ranks 21-100", tickers[20:])):
        sl = slice("2009-01-01", None)
        O, H, L, C, V = (px[f][tks].loc[sl] for f in ("Open", "High", "Low", "Close", "Volume"))
        on = pd.DataFrame({t: sig[t]["cf_nm"] for t in tks}).reindex(C.index)
        w180 = buy_window(buys, C.index, tks, 180, MIN_VALUE)
        w365 = buy_window(buys, C.index, tks, 365, MIN_VALUE)
        variants = {"A  baseline (1% risk)": {},
                    "E2 2% risk if insider bought (180d)": {"risk_scale": 1 + w180.astype(float)},
                    "E3 entries only after insider buying (365d)": {"entry_mask": w365}}
        res = {}
        for n, kw in variants.items():
            r, inv, trs = risk_engine.run(O, H, L, C, V, on, risk=0.01, k=3.0, **kw)
            res[n] = (r.loc[START:], float(inv.loc[START:].mean()), len(trs))
        cover = float(w365.loc[START:].mean().mean())
        md += [f"## {label}", "", f"Share of stock-days with insider buying in the prior 365 days: {cover:.1%}", "",
               "| Strategy | 2010-2018 | 2019-today | 2010-today | Avg invested | Trades |", "|---|---|---|---|---|---|"]
        for n, (r, inv, ntr) in res.items():
            cells = [f"{stats(r.loc[a:b])['cagr']:.1%} / {stats(r.loc[a:b])['sharpe']:.2f} / "
                     f"{stats(r.loc[a:b])['max_dd']:.0%}" for a, b in list(HALVES.values()) + [("2010", "2100")]]
            md.append(f"| {n} | " + " | ".join(cells) + f" | {inv:.0%} | {ntr} |")
        md.append("")
        if label == "Ranks 21-100":
            base = res["A  baseline (1% risk)"][0]
            for n in list(variants)[1:]:
                ok, notes = True, []
                for h, (a, b) in HALVES.items():
                    sb, sn = stats(base.loc[a:b]), stats(res[n][0].loc[a:b])
                    good = sn["sharpe"] >= sb["sharpe"] + 0.05 and sn["max_dd"] >= sb["max_dd"] - 0.02
                    ok &= good
                    notes.append(f"{h}: Sharpe {sb['sharpe']:.2f} -> {sn['sharpe']:.2f}, "
                                 f"drawdown {sb['max_dd']:.1%} -> {sn['max_dd']:.1%}")
                verdicts[n] = (ok, notes)
    md += ["## Verdicts (ranks 21-100, both halves)", ""]
    for n, (ok, notes) in verdicts.items():
        md.append(f"- **{n.split()[0]}: {'PASS' if ok else 'FAIL'}** - " + "; ".join(notes))
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
