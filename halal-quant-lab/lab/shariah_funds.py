"""Independent Shariah confirmation: which stocks do certified Shariah funds actually hold?

    SEC_USER_AGENT="Name email" python -m lab.shariah_funds

US-registered Shariah funds must file their complete holdings with the SEC every quarter (Form
N-PORT, public on EDGAR). Each of these funds is screened by its own Sharia supervisory board or a
Shariah index methodology (AAOIFI / S&P / FTSE / Russell Shariah), so a stock held by one of them has
been approved by Islamic scholars - an outside check on our own financial-statement screen
(lab/shariah.py). Writes reports/universe/shariah_funds.csv: ticker, the funds holding it, filing date.
Holdings are about 2-3 months old (filing lag), so re-run each quarter.
"""
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "universe" / "shariah_funds.csv"
FUNDS = {  # ticker: (EDGAR CIK, series id, description)
    "SPUS": (1742912, "S000067283", "SP Funds S&P 500 Sharia ETF"),
    "HLAL": (1683471, "S000065986", "Wahed FTSE USA Shariah ETF"),
    "SPTE": (1989916, "S000082880", "SP Funds S&P Global Technology ETF"),
    "MNZL": (1592900, "S000096943", "Manzil Russell Fossil Fuel Free Shariah ETF"),
    "AMAGX": (766285, "S000022508", "Amana Growth Fund"),
    "AMANX": (766285, "S000004772", "Amana Income Fund"),
    "IMANX": (1105877, "S000005190", "Iman Fund"),
    "ADJEX": (1031008, "S000004763", "Azzad Ethical Fund"),
}
NS = {"n": "http://www.sec.gov/edgar/nport"}


def _session():
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua or "@" not in ua:
        raise SystemExit('Set SEC_USER_AGENT="Your Name your@email.com" (required by the SEC).')
    s = requests.Session()
    s.headers.update({"User-Agent": ua})
    return s


def latest_nport(s, cik, series):
    sub = s.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", timeout=30).json()
    rec = sub["filings"]["recent"]
    for form, acc, date in zip(rec["form"], rec["accessionNumber"], rec["filingDate"]):
        if form not in ("NPORT-P", "NPORT-P/A"):
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/primary_doc.xml"
        time.sleep(0.2)
        r = s.get(url, timeout=60)
        if r.status_code != 200 or series not in r.text[:20000]:
            continue
        return date, r.text
    return None, None


def holdings(xml):
    root = ET.fromstring(xml)
    out = []
    for h in root.iter("{http://www.sec.gov/edgar/nport}invstOrSec"):
        name = (h.findtext("n:name", default="", namespaces=NS) or "").strip()
        title = (h.findtext("n:title", default="", namespaces=NS) or "").strip()
        cusip = (h.findtext("n:cusip", default="", namespaces=NS) or "").strip()
        tick = ""
        ids = h.find("n:identifiers", NS)
        if ids is not None:
            t = ids.find("n:ticker", NS)
            if t is not None:
                tick = t.get("value", "")
        out.append({"name": name, "title": title, "cusip": cusip, "ticker": tick.upper()})
    return out


_DROP = r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|holdings?|group|class [a-z]|cl [a-z]|the|n\.?v|s\.?a|ag|se|lp|llc|com|common|stock|shares?|ordinary|new|de)\b"


def norm(name):
    n = re.sub(r"[^a-z0-9 ]", " ", str(name).lower().replace("&", " and "))
    n = re.sub(_DROP, " ", n)
    return re.sub(r"\s+", " ", n).strip()


def main():
    s = _session()
    names = pd.concat([pd.read_csv(ROOT / "reports" / "broad_screen.csv")[["ticker", "name"]],
                       pd.read_csv(ROOT / "reports" / "universe" / "midcap_screen.csv")[["ticker", "name"]]]).dropna()
    by_name = {norm(n): t for t, n in zip(names.ticker, names.name)}
    tickers = set(names.ticker)
    held = {}
    for fund, (cik, series, desc) in FUNDS.items():
        date, xml = latest_nport(s, cik, series)
        if not xml:
            print(f"  {fund}: no N-PORT filing found")
            continue
        hs = holdings(xml)
        matched = 0
        for h in hs:
            t = h["ticker"] if h["ticker"] in tickers else by_name.get(norm(h["name"])) or by_name.get(norm(h["title"]))
            if t:
                held.setdefault(t, {})[fund] = date
                matched += 1
        print(f"  {fund} ({desc}): filed {date}, {len(hs)} holdings, {matched} matched to our universe")
    rows = [{"ticker": t, "funds": ",".join(sorted(f)), "n_funds": len(f), "latest_filing": max(f.values())}
            for t, f in held.items()]
    df = pd.DataFrame(rows).sort_values("n_funds", ascending=False)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} stocks held by at least one certified Shariah fund -> {OUT}")


if __name__ == "__main__":
    main()
