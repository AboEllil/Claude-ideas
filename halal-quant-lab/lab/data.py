"""Daily OHLCV download from Yahoo Finance with a local cache."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from .universe import DATA

FIELDS = ("Open", "High", "Low", "Close", "Volume")
BENCHMARKS = ["SPY", "^VIX", "SPUS", "HLAL", "QQQ"]


def load_prices(tickers, start="2005-01-01", refresh=False, cache_name="prices.pkl"):
    """Split/dividend-adjusted OHLCV as {field: DataFrame(dates x tickers)}."""
    DATA.mkdir(exist_ok=True)
    cache = DATA / cache_name
    want = sorted(set(tickers) | set(BENCHMARKS))
    if cache.exists() and not refresh:
        px = pd.read_pickle(cache)
        if set(want) <= set(px["Close"].columns):
            return {f: px[f][want] for f in FIELDS}

    raw = yf.download(want, start=start, auto_adjust=True, progress=False,
                      threads=True, group_by="column")
    px = {f: raw[f].astype(float) for f in FIELDS}

    # Drop today's bar while the US session is still open - it is not final.
    now = datetime.now(ZoneInfo("America/New_York"))
    last = px["Close"].index[-1]
    if last.date() == now.date() and now.hour < 16:
        px = {f: d.iloc[:-1] for f, d in px.items()}

    missing = [t for t in want if px["Close"][t].notna().sum() == 0]
    if missing:
        print(f"warning: no price data for {missing}")
    pd.to_pickle(px, cache)
    return px
