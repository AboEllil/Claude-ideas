"""Bigger universes for the signal board: US mid caps ($2-10B, Shariah screened) and top crypto coins.

Lists come from Yahoo Finance's screener and are saved in reports/universe/ (committed, so the
daily scan in a fresh session can use them without re-screening). Re-run `python -m lab.expand` occasionally (e.g. monthly) to refresh them.
"""
import json
import re

import yfinance as yf
from yfinance import EquityQuery

from pathlib import Path

from .universe import screen

UNIVERSE = Path(__file__).resolve().parent.parent / "reports" / "universe"

# Crypto excluded on Shariah or practical grounds (kept conservative):
# meme coins (gharar / pure speculation), interest or yield-bearing / lending tokens, perpetual-futures
# exchange tokens, and unclear tokens. Stablecoins and wrapped / staked copies are excluded by pattern.
CRYPTO_EXCLUDE = {
    "DOGE", "SHIB", "PEPE", "TRUMP", "BONK", "WIF", "FLOKI", "PENGU", "FARTCOIN", "SPX", "BRETT", "POPCAT",
    "AAVE", "ENA", "ONDO", "COMP", "MKR", "SKY", "CRV", "PENDLE", "JST", "SUSDE", "USDY", "BUIDL",
    "HYPE", "DYDX", "GMX", "JUP", "DEL", "RAIN", "CC", "GRAM", "M", "BTW", "XAUT", "PAXG",
    "PUMP", "ASTER", "MORPHO", "VVV", "U", "BTCT",
    "RETH", "LBTC", "JLP", "LIT", "CTM", "DHN",   # staked / perp-LP / perp-exchange / unclear tokens
    # exchange tokens of platforms built around margin / futures trading
    "LEO", "OKB", "BGB", "GT", "KCS", "HTX", "WBT",
}
STABLE_OR_WRAPPED = re.compile(r"USD|DAI|EUR|^W[A-Z]{2,5}$|STETH|BETH|WEETH|CBBTC|BTCB|AETH|^RW|TUSD|FDUSD", re.I)


def _base(symbol):
    return re.sub(r"\d+$", "", symbol.replace("-USD", ""))


def crypto_list(n=40):
    q = yf.screen("all_cryptocurrencies_us", count=150)["quotes"]
    out = []
    for x in sorted(q, key=lambda x: -(x.get("marketCap") or 0)):
        b = _base(x["symbol"])
        name = re.sub(r"\s+USD$", "", x.get("shortName") or x.get("longName") or b)
        if b in CRYPTO_EXCLUDE or STABLE_OR_WRAPPED.search(b) or re.search(r"wrapped|staked|bridged|dollar|\busd", name, re.I):
            continue
        out.append({"symbol": x["symbol"], "name": name})
        if len(out) >= n:
            break
    return out


def midcap_list(lo=2e9, hi=10e9):
    q = EquityQuery("and", [EquityQuery("eq", ["region", "us"]),
                            EquityQuery("btwn", ["intradaymarketcap", lo, hi]),
                            EquityQuery("is-in", ["exchange", "NMS", "NYQ", "NGM", "NCM", "ASE"])])
    syms, off = [], 0
    while True:
        r = yf.screen(q, size=250, offset=off, sortField="intradaymarketcap", sortAsc=False)
        qs = r.get("quotes", [])
        syms += [x["symbol"] for x in qs if x.get("quoteType", "EQUITY") == "EQUITY" and "." not in x["symbol"]]
        off += 250
        if not qs or off >= r.get("total", 0):
            break
    return sorted(set(syms))


def main():
    UNIVERSE.mkdir(parents=True, exist_ok=True)
    cryptos = crypto_list()
    (UNIVERSE / "crypto_list.json").write_text(json.dumps(cryptos, indent=1))
    print(f"crypto: {len(cryptos)} coins")
    mids = midcap_list()
    print(f"mid caps from screener: {len(mids)}; screening (this downloads fundamentals) ...")
    df = screen(mids)
    df.to_csv(UNIVERSE / "midcap_screen.csv", index=False)
    print(f"mid caps passing the Shariah screen: {int(df.compliant.sum())} of {len(df)}")


if __name__ == "__main__":
    main()
