"""Market liquidity regimes from free data (used by run_liquidity2.py and the daily signal board).

  Fed net liquidity = Fed balance sheet (WALCL) - Treasury cash account (WTREGEN) - reverse repo (RRPONTSYD),
      FRED. Weekly Wednesday values are used from the Friday after (published Thursday afternoon); the daily
      reverse repo from the next business day. RISING = above its 13-week (65 business day) average.
  Stablecoin money = total USD stablecoins in circulation (DefiLlama). RISING = higher than 30 days ago.
      Reliable only from 2020.
  Bitcoin on-chain = estimated USD value moved on the Bitcoin chain per day (blockchain.info).
      RISING = 30-day average above the 90-day average.

    python -m lab.liquidity        # writes reports/signal_board/liquidity.csv (dashboard chart data)

Forward tracking: the rules above were fixed on 2 Nov 2026 (reports/liquidity2/REPORT.md). Signals after that
date can be re-measured at any time from price history, so no log is needed.
"""
import io
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "reports" / "signal_board" / "liquidity.csv"


def fred(series):
    d = pd.read_csv(io.StringIO(requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=60).text))
    d.columns = ["date", "v"]
    return pd.Series(pd.to_numeric(d.v, errors="coerce").to_numpy(), index=pd.to_datetime(d.date)).dropna()


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
    cols = {}
    for k, (val, ref, flag) in s.items():
        cols[f"{k.lower()}_value"] = val
        cols[f"{k.lower()}_ref"] = ref
        cols[f"{k.lower()}_rising"] = flag
    days = pd.date_range(start, pd.Timestamp.today().normalize(), freq="D")
    df = pd.DataFrame({c: v.reindex(v.index.union(days)).ffill().reindex(days) for c, v in cols.items()})
    keep = (df.index.weekday == 4) | (df.index == df.index[-1])
    df = df[keep].copy()
    for k in ("fed", "stable"):                                       # $ trillions / $ billions
        div = 1e6 if k == "fed" else 1e9
        df[f"{k}_value"], df[f"{k}_ref"] = df[f"{k}_value"] / div, df[f"{k}_ref"] / div
    df["chain_value"], df["chain_ref"] = df["chain_value"] / 1e9, df["chain_ref"] / 1e9
    for k in ("fed", "stable", "chain"):
        df[f"{k}_rising"] = df[f"{k}_rising"].map({True: "yes", False: "no", 1.0: "yes", 0.0: "no"}).fillna("")
    df.index.name = "date"
    out = df.reset_index()
    out["date"] = out.date.dt.strftime("%Y-%m-%d")
    out.round(4).to_csv(path, index=False)
    return out


if __name__ == "__main__":
    d = export_csv()
    print(d.tail(3).to_string())
