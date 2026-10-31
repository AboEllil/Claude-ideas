"""Insider open-market purchases from the SEC's free Insider Transactions Data Sets.

Source: https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
One ZIP per quarter (2006 onward) with every Form 3/4/5 filing as tab-separated tables.
We keep only non-derivative OPEN-MARKET PURCHASES (transaction code "P", acquired "A") by
insiders of our stocks - the type of insider trade with evidence of predicting returns
(Lakonishok & Lee 2001; Cohen, Malloy & Pomorski 2012). Sales are ignored (mostly
diversification / tax, little information).

The SEC requires a contact in the User-Agent of every automated request:
    export SEC_USER_AGENT="Your Name your@email.com"
Requests are throttled well below the SEC's 10 requests/second limit.
"""
import io
import os
import time
import zipfile
from datetime import date

import pandas as pd
import requests

from .universe import DATA

BASE = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{y}q{q}_form345.zip"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def _session():
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        raise SystemExit('Set SEC_USER_AGENT="Your Name your@email.com" (required by the SEC).')
    s = requests.Session()
    s.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
    return s


def ticker_to_cik(s, tickers):
    data = s.get(TICKERS_URL, timeout=30).json()
    m = {v["ticker"].upper(): int(v["cik_str"]) for v in data.values()}
    return {t: m[t] for t in tickers if t in m}


def _read(z, name, cols):
    with z.open(name) as f:
        return pd.read_csv(f, sep="\t", usecols=cols, dtype=str, low_memory=False)


def quarters(start=2006):
    today = date.today()
    for y in range(start, today.year + 1):
        for q in range(1, 5):
            if (y, q) < (today.year, (today.month - 1) // 3 + 1):
                yield y, q


def load_insider_buys(tickers, refresh=False, start=2006):
    """DataFrame of open-market purchases: ticker, filing_date, trans_date, owner, role, shares, price, value."""
    DATA.mkdir(exist_ok=True)
    cache = DATA / "insider_buys.csv"
    done_file = DATA / "insider_quarters_done.txt"
    if cache.exists() and not refresh:
        old = pd.read_csv(cache, parse_dates=["filing_date", "trans_date"])
        done = set(done_file.read_text().split()) if done_file.exists() else set()
    else:
        old, done = pd.DataFrame(), set()
    todo = [(y, q) for y, q in quarters(start) if f"{y}q{q}" not in done]
    if not todo:
        return old
    s = _session()
    cik = ticker_to_cik(s, tickers)
    by_cik = {v: k for k, v in cik.items()}
    frames = [old] if len(old) else []
    for y, q in todo:
        r = s.get(BASE.format(y=y, q=q), timeout=120)
        time.sleep(0.5)
        if r.status_code != 200:
            print(f"  {y}q{q}: HTTP {r.status_code}, skipped")
            continue
        z = zipfile.ZipFile(io.BytesIO(r.content))
        sub = _read(z, "SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERCIK"])
        sub = sub[sub.ISSUERCIK.astype(int).isin(by_cik)]
        if sub.empty:
            done.add(f"{y}q{q}")
            continue
        nd = _read(z, "NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES",
                                              "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
        nd = nd[(nd.TRANS_CODE == "P") & (nd.TRANS_ACQUIRED_DISP_CD == "A")]
        own = _read(z, "REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP"])
        own = own.groupby("ACCESSION_NUMBER").first().reset_index()
        x = nd.merge(sub, on="ACCESSION_NUMBER").merge(own, on="ACCESSION_NUMBER", how="left")
        if x.empty:
            done.add(f"{y}q{q}")
            continue
        out = pd.DataFrame({
            "ticker": x.ISSUERCIK.astype(int).map(by_cik),
            "accession": x.ACCESSION_NUMBER,
            "filing_date": pd.to_datetime(x.FILING_DATE, format="mixed", dayfirst=True, errors="coerce"),
            "trans_date": pd.to_datetime(x.TRANS_DATE, format="mixed", dayfirst=True, errors="coerce"),
            "owner": x.RPTOWNERNAME, "role": x.RPTOWNER_RELATIONSHIP,
            "shares": pd.to_numeric(x.TRANS_SHARES, errors="coerce"),
            "price": pd.to_numeric(x.TRANS_PRICEPERSHARE, errors="coerce"),
        })
        out["value"] = out.shares * out.price
        frames.append(out)
        done.add(f"{y}q{q}")
        print(f"  {y}q{q}: {len(out)} purchases")
    res = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(res):
        res = res.drop_duplicates(["accession", "trans_date", "shares", "price"]).sort_values("filing_date")
    res.to_csv(cache, index=False)
    done_file.write_text("\n".join(sorted(done)))
    return res


def buy_window(buys, index, tickers, days, min_value=25_000):
    """Boolean DataFrame: True if an open-market purchase worth >= min_value was FILED in the
    last `days` calendar days. Usable from the trading day AFTER the filing date (filings often
    arrive after the close), so there is no look-ahead."""
    b = buys[(buys.value >= min_value) & buys.ticker.isin(tickers)]
    out = pd.DataFrame(False, index=index, columns=tickers)
    for t, g in b.groupby("ticker"):
        for d in g.filing_date.dropna().unique():
            d = pd.Timestamp(d)
            out.loc[(out.index > d) & (out.index <= d + pd.Timedelta(days=days)), t] = True
    return out
