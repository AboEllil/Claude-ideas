"""Point-in-time company data from SEC EDGAR: earnings-release dates and quarterly fundamentals.

    SEC_USER_AGENT="Name email" python -m lab.sec_fundamentals AAPL MSFT    # quick check

Earnings dates  : 8-K filings with item 2.02 ("Results of Operations") = the earnings release.
Fundamentals    : XBRL company-concept data (10-Q / 10-K). Every value is stamped with the date it
                  was FILED, so a signal on day t only sees numbers filed before t (no look-ahead).
Cached in data/sec_fundamentals.pkl (data/ is not committed).
"""
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

from .universe import DATA

CACHE = DATA / "sec_fundamentals.pkl"
CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueGoodsNet"],
    "gross_profit": ["GrossProfit"],
    "op_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "assets": ["Assets"],
}
FLOWS = {"revenue", "gross_profit", "op_income", "net_income"}


def _session():
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise SystemExit('Set SEC_USER_AGENT="Your Name your@email.com" (required by the SEC).')
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


def _get(s, url):
    for k in range(6):
        try:
            r = s.get(url, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** k)
            continue
        time.sleep(0.12)                                   # SEC limit: 10 requests / second
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        time.sleep(2 ** k)
    return None


def earnings_dates(s, cik):
    sub = _get(s, f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    if not sub:
        return []
    pages = [sub["filings"]["recent"]] + [_get(s, f"https://data.sec.gov/submissions/{f['name']}") or {}
                                          for f in sub["filings"].get("files", [])]
    out = []
    for p in pages:
        for form, date, items in zip(p.get("form", []), p.get("filingDate", []), p.get("items", [])):
            if form in ("8-K", "8-K/A") and "2.02" in str(items):
                out.append(date)
    return sorted(set(out))


def concept_series(s, cik, names, flow):
    """Rows (end, filed, value) for quarterly flows (80-100 day periods) or point-in-time balances.
    All label variants are merged (companies switch XBRL labels over the years)."""
    rows = []
    for name in names:
        js = _get(s, f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{name}.json")
        if not js:
            continue
        for f in js.get("units", {}).get("USD", []):
            if f.get("form") not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            if flow:
                if "start" not in f:
                    continue
                days = (pd.Timestamp(f["end"]) - pd.Timestamp(f["start"])).days
                if not 80 <= days <= 100:
                    continue
            rows.append((f["end"], f["filed"], f["val"]))
    if len(rows) < 8:
        return None
    df = pd.DataFrame(rows, columns=["end", "filed", "val"])
    df["end"], df["filed"] = pd.to_datetime(df.end), pd.to_datetime(df.filed)
    return df.sort_values("filed").drop_duplicates("end", keep="first").sort_values("end")   # first report


def fetch(tickers, refresh=False):
    store = pd.read_pickle(CACHE) if CACHE.exists() and not refresh else {}
    todo = [t for t in tickers if t not in store]
    if not todo:
        return store
    s = _session()
    cik_map = {v["ticker"].upper(): int(v["cik_str"])
               for v in _get(s, "https://www.sec.gov/files/company_tickers.json").values()}
    for i, t in enumerate(todo, 1):
        cik = cik_map.get(t.upper().replace(".", "-")) or cik_map.get(t.upper())
        if cik is None:
            store[t] = None
            continue
        store[t] = {"earnings": earnings_dates(s, cik),
                    **{k: concept_series(s, cik, v, k in FLOWS) for k, v in CONCEPTS.items()}}
        if i % 25 == 0:
            print(f"  SEC {i}/{len(todo)}", flush=True)
            pd.to_pickle(store, CACHE)
    pd.to_pickle(store, CACHE)
    return store


def features(rec, index, close):
    """Daily point-in-time features on `index` for one company (NaN where unknown)."""
    out = pd.DataFrame(index=index)
    if not rec:
        return out
    # --- earnings timing and the price reaction to the last release (a free proxy for the surprise) ---
    ed = pd.to_datetime(pd.Series(rec["earnings"], dtype="object"))
    if len(ed):
        pos = np.searchsorted(ed.values, index.values, side="right") - 1      # last release on or before day
        last = np.where(pos >= 0, ed.values[np.clip(pos, 0, None)], np.datetime64("NaT"))
        since = (index.values - last).astype("timedelta64[D]").astype(float)
        out["days_since_earn"] = np.where(pos >= 0, since, np.nan)
        out["days_to_next_earn_est"] = np.clip(91 - out["days_since_earn"], -30, 91)
        c = close.reindex(index).ffill()
        r_react = {}
        for d in ed:
            i = index.searchsorted(d)                      # release day (or the next trading day)
            if 1 <= i < len(index) - 1:
                r_react[index[i + 1]] = c.iloc[i + 1] / c.iloc[i - 1] - 1          # known from day i+1
        react = pd.Series(r_react).reindex(index).ffill(limit=70)
        out["earn_reaction"] = react
    # --- fundamentals as of each filing date (+1 day: filed after the close) ---
    q = {}
    for k in CONCEPTS:
        df = rec.get(k)
        if df is None:
            continue
        df = df.copy()
        if k in FLOWS:                                     # year-ago value of the same quarter
            ago = df.set_index("end").val
            df["yago"] = [ago[(ago.index > e - pd.Timedelta(days=380)) & (ago.index < e - pd.Timedelta(days=350))].mean()
                          for e in df.end]
        q[k] = df
    if "revenue" in q:
        r = q["revenue"]
        s = pd.Series((r.val / r.yago - 1).to_numpy(), index=r.filed + pd.Timedelta(days=1))
        out["rev_growth"] = _asof(s, index)
        out["rev_accel"] = _asof(s - s.shift(1), index)
    if "net_income" in q:
        n = q["net_income"]
        s = pd.Series(((n.val - n.yago) / n.yago.abs()).clip(-5, 5).to_numpy(), index=n.filed + pd.Timedelta(days=1))
        out["ni_growth"] = _asof(s, index)
    for num, name in (("gross_profit", "gross_margin"), ("op_income", "op_margin"), ("net_income", "net_margin")):
        if num in q and "revenue" in q:
            m = q[num].merge(q["revenue"][["end", "val"]], on="end", suffixes=("", "_rev"))
            s = pd.Series((m.val / m.val_rev).clip(-2, 1).to_numpy(), index=m.filed + pd.Timedelta(days=1))
            out[name] = _asof(s, index)
    if "net_income" in q and "equity" in q:
        m = q["net_income"].merge(q["equity"][["end", "val"]], on="end", suffixes=("", "_eq"))
        s = pd.Series((4 * m.val / m.val_eq).where(m.val_eq > 0).clip(-2, 2).to_numpy(), index=m.filed + pd.Timedelta(days=1))
        out["roe"] = _asof(s, index)
    if "assets" in q:
        a = q["assets"].set_index("end").val
        g = [a[e] / a[(a.index > e - pd.Timedelta(days=380)) & (a.index < e - pd.Timedelta(days=350))].mean() - 1
             for e in a.index]
        s = pd.Series(g, index=q["assets"].filed.to_numpy() + pd.Timedelta(days=1))
        out["asset_growth"] = _asof(s, index)
    return out


def _asof(s, index):
    s = s[~s.index.duplicated(keep="last")].sort_index().replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return np.nan
    return s.reindex(s.index.union(index)).ffill(limit=None).reindex(index).where(
        index >= s.index[0]).to_numpy()


if __name__ == "__main__":
    st = fetch(sys.argv[1:] or ["AAPL", "MSFT"])
    for t in sys.argv[1:] or ["AAPL", "MSFT"]:
        idx = pd.bdate_range("2019-01-01", "2026-10-30")
        f = features(st[t], idx, pd.Series(np.linspace(100, 200, len(idx)), index=idx))
        print(t, len(st[t]["earnings"]) if st[t] else 0, "earnings dates")
        print(f.iloc[::400].round(3).to_string())
