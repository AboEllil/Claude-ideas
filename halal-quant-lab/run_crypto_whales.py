"""Whale / crowd data for crypto: Coinbase premium and the Fear & Greed index (pre-registered).

    python run_crypto_whales.py      # writes reports/crypto_whales/REPORT.md

Data (free):
  Coinbase premium = Coinbase BTC-USD daily close (api.exchange.coinbase.com) / the global BTC-USD close (Yahoo,
      volume-weighted across exchanges) - 1. Positive = US buyers (institutions use Coinbase) pay more than the
      rest of the world. Both closes are 00:00 UTC; a day's value is used from the next day.
  Fear & Greed index (api.alternative.me), 0 = extreme fear, 100 = extreme greed, daily from Feb 2018; used from
      the next day.
  Not available here: Binance funding rates (refuses this server's location), ETF flows (bot check), whale
      wallet / exchange-flow data (paid).
Regimes (fixed before the run):
  PREMIUM ON : the 7-day average Coinbase premium is above 0
  NO-GREED ON: the Fear & Greed index is below 75 (not "extreme greed")
Signals / trades: the crypto signals of run_ml_signals2.py (dashboard crypto rule + the user's arrow rule; half at
+2 ATR, then stop at entry; costs). Periods: 2018-2020 (2018-03 on, when both series exist) and 2021-today.
PRE-REGISTERED PASS RULES (same as run_liquidity2.py):
  Filter: in BOTH periods the filtered signals have a win rate >= +3 points, a higher average trade and a higher
      Sharpe (equal weight, max 10% each) than all crypto signals.
  Timing: hold Bitcoin only while the regime is ON (else cash): Sharpe higher AND max drawdown smaller than
      buy & hold in BOTH periods.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from lab.liquidity import coinbase_premium, fear_greed
from lab.metrics import stats
from lab.universe import DATA
from run_ml_signals import trade_stats
from run_order_liquidity import returns

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "crypto_whales"
PERIODS = {"2018-2020": ("2018-03-01", "2020-12-31"), "2021-today": ("2021-01-01", "2100-01-01")}


def at(series, dates):
    s = series.dropna()
    return s.reindex(s.index.union(pd.DatetimeIndex(dates).unique())).ffill().reindex(dates).to_numpy()


def pstats(r, period):
    a, b = PERIODS[period]
    return stats(r.loc[a:b], year=365)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev, idx_map, closes = pd.read_pickle(DATA / "ml_signals2_events.pkl")
    ev = ev[ev.hit.notna() & (ev.market == "Crypto") & (ev.date >= PERIODS["2018-2020"][0])].copy()
    glob = closes["Crypto"]["BTC-USD"].dropna()
    prem7 = coinbase_premium(glob)
    prem = prem7
    fg = fear_greed()
    reg = {"PREMIUM": (prem7 > 0).astype(float).where(prem7.notna()), "NO-GREED": (fg < 75).astype(float)}
    for k, s in reg.items():
        ev[k] = at(s, ev.date)
    names = {"PREMIUM": "Coinbase premium positive (7-day average)", "NO-GREED": "Fear & Greed below 75 (no extreme greed)"}

    md = ["# Whale / crowd data for crypto - Coinbase premium and Fear & Greed (pre-registered)\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev):,} closed crypto trades from March 2018. Coinbase premium "
          f"from {prem.index[0]:%Y-%m-%d}, Fear & Greed from {fg.index[0]:%Y-%m-%d}. Days ON since 2018-03: "
          + ", ".join(f"{k} {s.loc['2018-03':].mean():.0%}" for k, s in reg.items()) + ". Funding rates (Binance refuses "
          "this server's location), ETF flows (bot check) and wallet flows (paid) could not be tested.\n"]
    verdicts = {}
    for k in reg:
        md += [f"## Filter: {names[k]}", "",
               "| Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |",
               "|---|---|---|---|---|---|---|---|---|"]
        res = []
        for per, (a, b) in PERIODS.items():
            d = ev[(ev.date >= a) & (ev.date <= b) & ev[k].notna()]
            out = {}
            for nm, x in (("All", d), ("Regime ON", d[d[k] > 0.5]), ("Regime OFF", d[d[k] <= 0.5])):
                t, s = trade_stats(x), pstats(returns(x, idx_map, closes["Crypto"], "Crypto"), per)
                out[nm] = (t, s)
                md.append(f"| {per} | {nm} | {t['n']} | {t['win']:.0%} | {t['avg']:+.1%} | {t['pf']:.2f} | {s['cagr']:.1%} | "
                          f"{s['sharpe']:.2f} | {s['max_dd']:.0%} |")
            (ta, sa), (tf, sf) = out["All"], out["Regime ON"]
            res.append(tf["n"] >= 20 and tf["win"] - ta["win"] >= 0.03 and tf["avg"] > ta["avg"] and sf["sharpe"] > sa["sharpe"])
        verdicts[f"{k} filter"] = all(res)
        md += ["", f"**Verdict: {'PASS' if all(res) else 'FAIL'}**", ""]

    timing_rows = []
    md += ["## Timing: hold Bitcoin only while the regime is ON (else cash)", "",
           "| Period | Strategy | CAGR | Sharpe | Max DD | Time invested |", "|---|---|---|---|---|---|"]
    r = glob.pct_change().fillna(0)
    for k in reg:
        on = pd.Series(at(reg[k], r.index), index=r.index).fillna(0)
        ok = []
        for per, (a, b) in PERIODS.items():
            rows = {}
            for nm, w in (("Buy & hold", pd.Series(1.0, index=r.index)), (f"{k} ON", on)):
                w = w.shift(1).fillna(0)
                rr = (w * r - 0.001 * w.diff().abs().fillna(0)).loc[a:b]
                rows[nm] = stats(rr, year=365)
                if k == "PREMIUM":
                    timing_rows.append({"strategy": "Hold Bitcoin only while the Coinbase premium is positive" if nm != "Buy & hold"
                                        else "Hold Bitcoin all the time", "period": per, "cagr": round(rows[nm]["cagr"], 4),
                                        "sharpe": round(rows[nm]["sharpe"], 2), "max_dd": round(rows[nm]["max_dd"], 4),
                                        "invested": round(float(w.loc[a:b].mean()), 3)})
                if nm != "Buy & hold" or k == list(reg)[0]:
                    md.append(f"| {per} | {nm} | {rows[nm]['cagr']:.1%} | {rows[nm]['sharpe']:.2f} | {rows[nm]['max_dd']:.0%} | "
                              f"{w.loc[a:b].mean():.0%} |")
            ok.append(rows[f"{k} ON"]["sharpe"] > rows["Buy & hold"]["sharpe"] and rows[f"{k} ON"]["max_dd"] > rows["Buy & hold"]["max_dd"])
        verdicts[f"{k} timing (BTC)"] = all(ok)
    md += ["", "## Verdicts (pre-registered)", "", "| Test | Result |", "|---|---|"] + \
          [f"| {k} | **{'PASS' if v else 'FAIL'}** |" for k, v in verdicts.items()]
    md += ["", f"Latest: Coinbase premium (7-day) {prem7.dropna().iloc[-1]:+.3%}; Fear & Greed {fg.iloc[-1]:.0f}."]
    pd.DataFrame(timing_rows).to_csv(ROOT / "reports" / "signal_board" / "btc_timing_evidence.csv", index=False)
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
