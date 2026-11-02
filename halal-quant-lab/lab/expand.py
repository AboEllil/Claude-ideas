"""Bigger universes for the signal board: all US large caps ($10B+), mid caps ($2-10B) and small caps ($1-2B),
business-screened, and the top 100 halal-filtered crypto coins.

    python -m lab.expand            # everything
    python -m lab.expand crypto     # only the crypto list


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
    # added Nov 2026 when the list grew to 100 coins:
    "GHO", "USX", "STABLE", "FF",                      # stablecoins / synthetic-dollar yield
    "NEXO", "SUN", "LDO", "ETHFI",                     # interest / lending or staking-yield protocols
    "DRV", "INJ",                                       # derivatives exchanges / chains
    "SHFL", "PREDICT",                                  # gambling / prediction markets
    "APEPE", "LUNC",                                    # meme / failed coins
    "SLISBNBX", "TETH", "VBNB",                         # staked / lending-wrapped copies
    "BP", "UB", "PEARL", "GROW", "KOGE", "PIEVERSE", "NFT",   # unclear tokens (excluded to stay safe)
    "CVX", "JTO", "SYRUP", "KMNO", "INF", "FLUID", "EIGEN", "ETHX", "KNTQ", "BORG",  # yield / lending / (re)staking
    "BTSE", "USAT", "SPCXB", "CRCLB",                  # futures exchange, stablecoin, tokenized shares
    "TIBBIR", "PONS", "GOMINING",                      # unclear tokens
}
STABLE_OR_WRAPPED = re.compile(r"USD|DAI|EUR|^W[A-Z]{2,5}$|STETH|BETH|WEETH|CBBTC|BTCB|AETH|^RW|TUSD|FDUSD|"
                               r"^[A-Z]+BTC$|^V(BTC|ETH|BNB|USDT)$|^\d+$", re.I)    # wrapped BTC copies, Venus, bare numbers


def _base(symbol):
    return re.sub(r"\d+$", "", symbol.replace("-USD", ""))


def crypto_list(n=100):
    q = yf.screen("all_cryptocurrencies_us", count=250)["quotes"]
    out = []
    for x in sorted(q, key=lambda x: -(x.get("marketCap") or 0)):
        b = _base(x["symbol"])
        if not b or x["symbol"].split("-")[0].isdigit():               # bare-number symbols: unidentifiable
            continue
        name = re.sub(r"\s+USD$", "", x.get("shortName") or x.get("longName") or b)
        if b in CRYPTO_EXCLUDE or STABLE_OR_WRAPPED.search(b) or re.search(r"wrapped|staked|bridged|dollar|\busd", name, re.I):
            continue
        out.append({"symbol": x["symbol"], "name": name})
        if len(out) >= n:
            break
    return out


def cap_list(lo, hi):
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


def midcap_list(lo=2e9, hi=10e9):
    return cap_list(lo, hi)


SIZES = {"largecap": (10e9, 1e14), "midcap": (2e9, 10e9), "smallcap": (1e9, 2e9)}


def main():
    import sys
    UNIVERSE.mkdir(parents=True, exist_ok=True)
    cryptos = crypto_list()
    (UNIVERSE / "crypto_list.json").write_text(json.dumps(cryptos, indent=1))
    print(f"crypto: {len(cryptos)} coins")
    if "crypto" in sys.argv:
        return
    for name, (lo, hi) in SIZES.items():
        syms = cap_list(lo, hi)
        print(f"{name}: {len(syms)} from the screener; business screen (downloads fundamentals) ...", flush=True)
        df = screen(syms)
        df.to_csv(UNIVERSE / f"{name}_screen.csv", index=False)
        print(f"{name}: {int(df.compliant.sum())} of {len(df)} pass the business screen", flush=True)


if __name__ == "__main__":
    main()
