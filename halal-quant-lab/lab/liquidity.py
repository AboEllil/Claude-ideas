"""Market liquidity regimes from free data (used by run_liquidity2.py and the daily signal board).

  Fed net liquidity = Fed balance sheet (WALCL) - Treasury cash account (WTREGEN) - reverse repo (RRPONTSYD),
      FRED. Weekly Wednesday values are used from the Friday after (published Thursday afternoon); the daily
      reverse repo from the next business day. RISING = above its 13-week (65 business day) average.
  Stablecoin money = total USD stablecoins in circulation (DefiLlama). RISING = higher than 30 days ago.
      Reliable only from 2020.
  Bitcoin on-chain = estimated USD value moved on the Bitcoin chain per day (blockchain.info).
      RISING = 30-day average above the 90-day average.
  Coinbase premium = Coinbase BTC-USD close / global BTC-USD close (Yahoo) - 1, 7-day average. POSITIVE = US buyers
      pay more. Holding Bitcoin only while it is positive passed a pre-registered test (reports/crypto_whales).
  Fear & Greed index (alternative.me), 0-100, with its own label (Extreme Fear ... Extreme Greed).

    python -m lab.liquidity        # writes reports/signal_board/liquidity.csv (dashboard chart data)

Forward tracking: the rules above were fixed on 2 Nov 2026 (reports/liquidity2/REPORT.md). Signals after that
date can be re-measured at any time from price history, so no log is needed.
"""
import io
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "reports" / "signal_board" / "liquidity.csv"


def fred(series):
    d = pd.read_csv(io.StringIO(requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=60).text))
    d.columns = ["date", "v"]
    return pd.Series(pd.to_numeric(d.v, errors="coerce").to_numpy(), index=pd.to_datetime(d.date)).dropna()


def coinbase_btc(start="2015-07-20"):
    rows, end = [], pd.Timestamp.utcnow().normalize().tz_localize(None)
    while end > pd.Timestamp(start):
        a = end - pd.Timedelta(days=299)
        r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/candles",
                         params={"granularity": 86400, "start": a.isoformat(), "end": end.isoformat()}, timeout=30)
        r.raise_for_status()
        rows += r.json()
        end = a - pd.Timedelta(days=1)
        time.sleep(0.35)
    s = pd.Series({pd.to_datetime(x[0], unit="s"): x[4] for x in rows}, dtype=float).sort_index()
    return s[~s.index.duplicated()]


def coinbase_premium(global_btc, start="2015-07-20"):
    """7-day average Coinbase premium, usable from the next day."""
    cb = coinbase_btc(start)
    prem = (cb / global_btc.reindex(cb.index) - 1).dropna()
    prem = prem[prem.abs() < 0.2]
    p7 = prem.rolling(7, min_periods=5).mean()
    p7.index = p7.index + pd.Timedelta(days=1)
    return p7


def fear_greed(with_label=False):
    js = requests.get("https://api.alternative.me/fng/?limit=0&format=json", timeout=30).json()["data"]
    v = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s") + pd.Timedelta(days=1): float(x["value"]) for x in js}).sort_index()
    if not with_label:
        return v
    lab = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s") + pd.Timedelta(days=1): x["value_classification"]
                     for x in js}).sort_index()
    return v, lab


def series():
    """Daily series (as known on each day) and their RISING flags."""
    bd = pd.bdate_range("2012-01-01", pd.Timestamp.today().normalize())
    walcl, tga = fred("WALCL"), fred("WTREGEN")
    walcl.index, tga.index = walcl.index + pd.Timedelta(days=2), tga.index + pd.Timedelta(days=2)
    rrp = fred("RRPONTSYD") * 1000
    rrp.index = rrp.index + pd.offsets.BDay(1)
    al = lambda s: s.reindex(s.index.union(bd)).ffill().reindex(bd)
    nl = al(walcl) - al(tga) - al(rrp).fillna(0)
    nl_avg = nl.rolling(65).mean()

    js = requests.get("https://stablecoins.llama.fi/stablecoincharts/all", timeout=60).json()
    sc = pd.Series({pd.to_datetime(int(x["date"]), unit="s"): x["totalCirculatingUSD"].get("peggedUSD") for x in js},
                   dtype=float).sort_index()
    sc.index = sc.index + pd.Timedelta(days=1)                       # a day's total is known the next day
    sc_ago = sc.shift(30)

    js = requests.get("https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=all&format=json"
                      "&sampled=false", timeout=120).json()
    ch = pd.Series({pd.to_datetime(p["x"], unit="s"): p["y"] for p in js["values"]}, dtype=float).sort_index()
    ch.index = ch.index + pd.Timedelta(days=1)
    ch30, ch90 = ch.rolling(30).mean(), ch.rolling(90).mean()
    return {
        "FED": (nl, nl_avg, (nl > nl_avg).where(nl_avg.notna())),
        "STABLE": (sc, sc_ago, (sc > sc_ago).where(sc_ago.notna() & (sc.index >= "2020-01-01"))),
        "CHAIN": (ch30, ch90, (ch30 > ch90).where(ch90.notna())),
    }


def regimes():
    s = series()
    return {k: v[2] for k, v in s.items()}, s["FED"][0], s["STABLE"][0], s["CHAIN"][0]


def state_on(flag, day):
    """The regime as known on `day` (last value on or before it); None if unknown."""
    f = flag.dropna()
    f = f[f.index <= pd.Timestamp(day)]
    return None if f.empty else bool(f.iloc[-1])


def export_csv(path=CSV, years=3):
    """Weekly chart rows for the last `years` years plus the latest day, one row per date."""
    s = series()
    start = pd.Timestamp.today().normalize() - pd.DateOffset(years=years)
    try:                                                              # whale / crowd measures (optional)
        import yfinance as yf
        g = yf.download("BTC-USD", start=(start - pd.DateOffset(days=40)).strftime("%Y-%m-%d"), auto_adjust=True,
                        progress=False)["Close"]
        g = (g.iloc[:, 0] if isinstance(g, pd.DataFrame) else g).dropna()
        g.index = pd.to_datetime(g.index).tz_localize(None)
        p7 = coinbase_premium(g, start=(start - pd.DateOffset(days=40)).strftime("%Y-%m-%d")) * 100
        s["PREMIUM"] = (p7, pd.Series(0.0, index=p7.index), (p7 > 0).where(p7.notna()))
        fg, fg_lab = fear_greed(with_label=True)
        s["FG"] = (fg, pd.Series(float("nan"), index=fg.index), (fg >= 50).where(fg.notna()))
    except Exception as e:
        print(f"warning: Coinbase premium / Fear & Greed unavailable ({e})")
        fg_lab = None
    cols = {}
    for k, (val, ref, flag) in s.items():
        cols[f"{k.lower()}_value"] = val
        cols[f"{k.lower()}_ref"] = ref
        cols[f"{k.lower()}_rising"] = flag
    days = pd.date_range(start, pd.Timestamp.today().normalize(), freq="D")
    df = pd.DataFrame({c: v.reindex(v.index.union(days)).ffill().reindex(days) for c, v in cols.items()})
    if fg_lab is not None:
        df["fg_label"] = fg_lab.reindex(fg_lab.index.union(days)).ffill().reindex(days)
    keep = (df.index.weekday == 4) | (df.index == df.index[-1])
    df = df[keep].copy()
    for k in ("fed", "stable"):                                       # $ trillions / $ billions
        div = 1e6 if k == "fed" else 1e9
        df[f"{k}_value"], df[f"{k}_ref"] = df[f"{k}_value"] / div, df[f"{k}_ref"] / div
    df["chain_value"], df["chain_ref"] = df["chain_value"] / 1e9, df["chain_ref"] / 1e9
    for k in [x.lower() for x in s]:
        df[f"{k}_rising"] = df[f"{k}_rising"].map({True: "yes", False: "no", 1.0: "yes", 0.0: "no"}).fillna("")
    df.index.name = "date"
    out = df.reset_index()
    out["date"] = out.date.dt.strftime("%Y-%m-%d")
    out.round(4).to_csv(path, index=False)
    return out


if __name__ == "__main__":
    d = export_csv()
    print(d.tail(3).to_string())
