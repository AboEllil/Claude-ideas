"""Full AAOIFI-style Shariah check from company financial statements (Yahoo Finance).

    python -m lab.shariah        # checks every US and EGX stock on the signal board (~20-40 min)

For each stock, from the latest annual balance sheet and income statement:
  debt      total debt / market cap                       < 30%
  cash      (cash + short-term investments) / market cap   < 30%
  income    interest income / total revenue                <  5%   (non-permissible income)
plus the business-activity screen already applied when the universe was built.
A stock whose figures are missing cannot be verified and is marked "unverified" - the scanner leaves
it out rather than assuming it is halal. Results: reports/universe/shariah_check.csv (re-run each
quarter, when new financial statements come out).

This is an approximate, automated screen. Zoya, Musaffa or your scholar's list take precedence when
they disagree.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from .egx import halal_egx

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "reports" / "universe"
OUT = UNIVERSE / "shariah_check.csv"
LIMITS = {"debt": 0.30, "cash": 0.30, "income": 0.05}
# Islamic banks are certified by their own Sharia supervisory boards; the cash and debt ratios are designed
# for non-financial companies and do not apply to them.
ISLAMIC_BANKS = {"ADIB.CA": "Abu Dhabi Islamic Bank Egypt", "FAIT.CA": "Faisal Islamic Bank of Egypt",
                 "FAITA.CA": "Faisal Islamic Bank of Egypt (USD)", "SAUD.CA": "Al Baraka Bank Egypt"}


def _first(df, names):
    if df is None or not len(df):
        return np.nan
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if len(s):
                return float(s.iloc[0])
    return np.nan


def check(tk):
    if tk in ISLAMIC_BANKS:
        return {"ticker": tk, "status": "pass", "reason": "Islamic bank with its own Sharia board"}
    for attempt in range(3):
        try:
            t = yf.Ticker(tk)
            info = t.info or {}
            bs, inc = t.balance_sheet, t.income_stmt
            break
        except Exception:
            time.sleep(3 * (attempt + 1))
    else:
        return {"ticker": tk, "status": "unverified", "reason": "no data from Yahoo"}
    mcap = info.get("marketCap") or np.nan
    debt = _first(bs, ["Total Debt"])
    if np.isnan(debt):
        debt = info.get("totalDebt") or np.nan
    cash = _first(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
    if np.isnan(cash):
        cash = info.get("totalCash") or np.nan
    rev = _first(inc, ["Total Revenue", "Operating Revenue"])
    ii = _first(inc, ["Interest Income", "Interest Income Non Operating"])
    ii = 0.0 if np.isnan(ii) and not np.isnan(rev) else max(ii, 0.0)
    r = {"ticker": tk, "market_cap": mcap, "debt_ratio": debt / mcap if mcap else np.nan,
         "cash_ratio": cash / mcap if mcap else np.nan,
         "income_ratio": ii / rev if rev and rev > 0 else (np.inf if ii > 0 else np.nan)}
    fails = []
    for k, lim in LIMITS.items():
        v = r[k + "_ratio"]
        if not np.isnan(v) and v >= lim:
            fails.append(f"{k} {v:.0%}" if np.isfinite(v) else f"{k}: interest income with no revenue")
    missing = [k for k in ("debt", "cash") if not np.isfinite(r[k + "_ratio"])]
    if not np.isfinite(r["income_ratio"]) and r["income_ratio"] != np.inf:
        missing.append("income")
    if fails:
        r["status"], r["reason"] = "fail", ", ".join(fails)
    elif missing:
        r["status"], r["reason"] = "unverified", "missing " + ", ".join(missing)
    else:
        r["status"], r["reason"] = "pass", "pass"
    return r


def board_tickers():
    scr = pd.read_csv(ROOT / "reports" / "broad_screen.csv")
    mid = pd.read_csv(UNIVERSE / "midcap_screen.csv")
    us = list(scr[scr.compliant & (scr.marketCap >= 10e9)].ticker) + list(mid[mid.compliant].ticker)
    for name in ("largecap", "smallcap"):                      # lists from lab/expand.py
        p = UNIVERSE / f"{name}_screen.csv"
        if p.exists():
            x = pd.read_csv(p)
            us += list(x[x.compliant & (x.industry != "Aerospace & Defense")].ticker)
    return sorted(set(us)) + [t + ".CA" for t in halal_egx()]


def main():
    tickers = board_tickers()
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["ticker"])
    todo = [t for t in tickers if t not in set(done.ticker)]
    print(f"{len(tickers)} stocks, {len(todo)} to check")
    rows = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, r in enumerate(ex.map(check, todo), 1):
            rows.append(r)
            if i % 50 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
                pd.concat([done, pd.DataFrame(rows)]).to_csv(OUT, index=False)
    res = pd.concat([done, pd.DataFrame(rows)])
    res = res[res.ticker.isin(tickers)]
    res.to_csv(OUT, index=False)
    print(res.status.value_counts().to_string())
    print(json.dumps(res[res.status == "fail"].reason.str.split(" ").str[0].value_counts().to_dict()))


if __name__ == "__main__":
    main()
