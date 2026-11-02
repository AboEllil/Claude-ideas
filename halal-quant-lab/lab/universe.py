"""Halal (Shariah-compliant) US stock universe using an AAOIFI-style screen.

Two screens, both must pass:
  1. Business activity: no conventional finance (banks, insurance, lending,
     capital markets), alcohol, tobacco, gambling, pork, adult or mainstream
     entertainment, and no real estate (conservative: mortgage/REIT leverage).
  2. Financial ratios (AAOIFI Standard 21 thresholds):
       total debt / market cap        < 30%
       cash & securities / market cap < 30%   (proxy for interest-bearing assets)

Limitations - read before relying on it:
  * AAOIFI uses a 36-month average market cap; we use the current one.
  * Non-permissible income (<5% of revenue) is not available from free data.
  * The screen is a research filter, not a fatwa. Cross-check with a dedicated
    screener (Zoya, Musaffa, Islamicly) or the holdings of SPUS / HLAL.
"""
import json
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA = Path(__file__).resolve().parent.parent / "data"

# Liquid US large caps. Some are expected to FAIL the screen (banks, alcohol,
# tobacco, casinos, pork, high-debt names) - they are here to prove it works.
CANDIDATES = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "AMD", "MU", "QCOM", "TXN",
    "INTC", "AMAT", "LRCX", "KLAC", "ADI", "MCHP", "NXPI", "ON", "MPWR", "ADBE",
    "CRM", "NOW", "INTU", "PANW", "CRWD", "FTNT", "ANET", "CSCO", "SNPS", "CDNS",
    "ADSK", "WDAY", "DDOG", "ZS", "ACN", "IT", "KEYS", "TER", "GLW", "APH",
    "TEL", "ORCL", "IBM", "HPQ", "DELL",
    # Consumer
    "AMZN", "TSLA", "COST", "WMT", "TJX", "ROST", "LULU", "NKE", "DECK", "HD",
    "LOW", "TSCO", "ORLY", "AZO", "BKNG", "ABNB", "PG", "CL", "KMB", "CHD",
    "CLX", "EL", "KO", "PEP", "MDLZ", "HSY", "GIS",
    # Health care
    "LLY", "JNJ", "MRK", "ABBV", "ABT", "TMO", "DHR", "ISRG", "SYK", "BSX",
    "MDT", "EW", "REGN", "VRTX", "AMGN", "GILD", "ZTS", "IDXX", "DXCM", "IQV",
    "A", "WST", "RMD", "ALGN",
    # Industrials
    "CAT", "DE", "ETN", "EMR", "ITW", "PH", "ROK", "HON", "GE", "CMI",
    "PCAR", "ODFL", "FAST", "GWW", "CTAS", "CPRT", "URI", "WM", "RSG", "UNP",
    "CSX", "NSC", "UPS", "FDX",
    # Energy & materials
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "DVN", "HAL", "MPC", "PSX",
    "VLO", "LIN", "APD", "SHW", "ECL", "NUE", "FCX", "NEM", "DD", "DOW",
    # Communication
    "NFLX", "DIS", "T", "VZ",
    # Control group - should fail
    "JPM", "BAC", "V", "MA", "STZ", "MO", "PM", "LVS", "HRL", "TSN", "O", "PLD",
]

EXCLUDED_SECTORS = {"Financial Services", "Real Estate"}
EXCLUDED_INDUSTRY_WORDS = (
    "Bank", "Insurance", "Capital Markets", "Credit Services", "Mortgage",
    "Asset Management", "Brewers", "Wineries", "Distillers", "Tobacco",
    "Gambling", "Casinos", "Entertainment", "Lodging",
)
EXCLUDED_TICKERS = {
    "HRL": "pork products", "TSN": "pork products",
    # Weapons makers - excluded by the Dow Jones Islamic Market index methodology.
    "LMT": "weapons/defense", "NOC": "weapons/defense", "GD": "weapons/defense",
    "RTX": "weapons/defense", "LHX": "weapons/defense", "HII": "weapons/defense",
    "MSTR": "bitcoin treasury company",
    "RCL": "cruise line (onboard casinos/alcohol)", "CCL": "cruise line (onboard casinos/alcohol)",
    "NCLH": "cruise line (onboard casinos/alcohol)",
    "CASY": "convenience stores (large beer/tobacco/lottery sales)",
    "MUSA": "convenience stores (large beer/tobacco/lottery sales)",
    "ARKO": "convenience stores (large beer/tobacco/lottery sales)",
    "SFD": "pork products", "VIK": "cruise line (onboard casinos/alcohol)",
}
FIELDS = ("shortName", "sector", "industry", "marketCap", "totalDebt", "totalCash",
          "returnOnEquity", "returnOnAssets", "profitMargins", "grossMargins",
          "revenueGrowth", "earningsGrowth", "freeCashflow", "trailingPE", "forwardPE")
MAX_DEBT_TO_MCAP = 0.30
MAX_CASH_TO_MCAP = 0.30


def fetch_fundamentals(tickers, refresh=False):
    """Sector, industry, market cap, debt, cash and quality metrics per ticker (cached)."""
    DATA.mkdir(exist_ok=True)
    cache_file = DATA / "fundamentals.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() and not refresh else {}
    todo = [t for t in tickers if not (t in cache and all(k in cache[t] for k in FIELDS))]

    def one(t):
        info = {}
        for attempt in range(3):
            try:
                info = yf.Ticker(t).info or {}
                if info.get("marketCap"):
                    break
            except Exception:
                pass
            time.sleep(2 * (attempt + 1))
        return t, {k: info.get(k) for k in FIELDS}

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as ex:                 # parallel: much faster than one at a time
        for i, (t, rec) in enumerate(ex.map(one, todo), 1):
            cache[t] = rec
            if i % 100 == 0:
                print(f"  fundamentals {i}/{len(todo)}", flush=True)
                cache_file.write_text(json.dumps(cache, indent=1))
    cache_file.write_text(json.dumps(cache, indent=1))
    return cache


def screen(tickers=CANDIDATES, refresh=False):
    """Return a DataFrame with the screen result and the reason for each ticker."""
    fund = fetch_fundamentals(tickers, refresh)
    rows = []
    for t in tickers:
        f = fund.get(t, {})
        mcap, debt, cash = f.get("marketCap"), f.get("totalDebt") or 0, f.get("totalCash") or 0
        sector, industry = f.get("sector") or "", f.get("industry") or ""
        reason = ""
        if not mcap:
            reason = "no fundamental data"
        elif t in EXCLUDED_TICKERS:
            reason = EXCLUDED_TICKERS[t]
        elif sector in EXCLUDED_SECTORS:
            reason = f"sector: {sector}"
        elif any(w in industry for w in EXCLUDED_INDUSTRY_WORDS):
            reason = f"industry: {industry}"
        elif debt / mcap >= MAX_DEBT_TO_MCAP:
            reason = f"debt/mcap {debt / mcap:.0%}"
        elif cash / mcap >= MAX_CASH_TO_MCAP:
            reason = f"cash/mcap {cash / mcap:.0%}"
        rows.append({
            "ticker": t, "name": f.get("shortName"), "sector": sector, "industry": industry,
            "debt_to_mcap": round(debt / mcap, 3) if mcap else None,
            "cash_to_mcap": round(cash / mcap, 3) if mcap else None,
            "compliant": reason == "", "reason": reason or "pass",
        })
    return pd.DataFrame(rows)


def halal_tickers(refresh=False):
    df = screen(refresh=refresh)
    return df.loc[df.compliant, "ticker"].tolist(), df
