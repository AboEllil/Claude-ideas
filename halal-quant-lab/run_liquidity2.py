"""Real liquidity / whale data: Fed net liquidity, stablecoin supply and Bitcoin on-chain volume (pre-registered).

    SEC_USER_AGENT="Name email" python run_liquidity2.py

Data (free, downloaded fresh):
  Fed net liquidity = Fed balance sheet (WALCL) - Treasury cash account (WTREGEN) - reverse repo (RRPONTSYD),
      FRED. Weekly Wednesday values are used only from the following Friday (published Thursday afternoon);
      the daily reverse repo from the next day.
  Stablecoin supply = total USD stablecoins in circulation (DefiLlama). Reliable only from 2020.
  Bitcoin on-chain volume = estimated USD value moved on the Bitcoin chain per day (blockchain.info) -
      a free stand-in for whale activity (true exchange in/outflows are paid data).
Regimes (fixed before the run, no tuning):
  FED ON     : net liquidity above its 13-week (65 business day) average
  STABLE ON  : stablecoin supply higher than 30 days earlier
  CHAIN ON   : 30-day average on-chain USD volume above its 90-day average
Signals / trades as in run_order_liquidity.py (dashboard rule + user's rule, half at +2 ATR, costs).

PRE-REGISTERED PASS RULES
  Filter test (new entries only when the regime is ON): in every judged period the filtered signals need
  a win rate >= +3 points, a higher average trade and a higher Sharpe (equal weight, max 10% each) than
  all signals.
    FED    judged on US and crypto, periods 2016-2020 and 2021-today; passes if both markets pass.
    STABLE judged on crypto, 2021-today only (data unreliable before 2020; 2020 shown for information).
    CHAIN  judged on crypto, periods 2016-2020 and 2021-today.
  Timing test (hold the market only when the regime is ON, else cash at 0%): US = equal-weight halal
  universe, crypto = Bitcoin. Passes if Sharpe is higher AND max drawdown smaller than buy & hold in
  every judged period (same periods as above). Shown next to the 200-day rule for comparison.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from lab.liquidity import regimes
from lab.metrics import stats
from lab.universe import DATA
from run_ml_signals import MARKETS, trade_stats
from run_order_liquidity import PERIODS, returns

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "liquidity2"
PERIODS = dict(PERIODS, **{"2020 (info)": ("2020-01-01", "2020-12-31")})


def pstats(r, market, period):
    a, b = PERIODS[period]
    return stats(r.loc[a:b], year=365 if market == "Crypto" else 252)


def at(series, dates):
    s = series.dropna()
    return s.reindex(s.index.union(pd.DatetimeIndex(dates).unique())).ffill().reindex(dates).to_numpy()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev, idx_map, closes = pd.read_pickle(DATA / "ml_signals2_events.pkl")
    ev = ev[ev.hit.notna() & (ev.date >= "2016-01-01")].copy()
    reg, nl, sc, ch = regimes()
    for k, s in reg.items():
        ev[k] = at(s.astype(float), ev.date)

    md = ["# Real liquidity and whale data - Fed liquidity, stablecoins, Bitcoin on-chain (pre-registered)\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev):,} closed trades from 2016. Regimes and pass rules were "
          "fixed before the run (see run_liquidity2.py). Share of days ON since 2016: " +
          ", ".join(f"{k} {s.loc['2016':].mean():.0%}" for k, s in reg.items()) + ".\n"]

    plan = {"FED": (["US", "Crypto"], ["2016-2020", "2021-today"], ["EGX"]),
            "STABLE": (["Crypto"], ["2021-today"], []),
            "CHAIN": (["Crypto"], ["2016-2020", "2021-today"], [])}
    names = {"FED": "Fed net liquidity above its 13-week average", "STABLE": "Stablecoin supply up over 30 days",
             "CHAIN": "Bitcoin on-chain volume: 30-day avg above 90-day avg"}
    verdicts = {}
    evidence = []
    for k, (judged, pers, info) in plan.items():
        md += [f"## Filter: {names[k]}", "",
               "| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        ok = {}
        for mk in judged + info:
            res = []
            show = pers + (["2020 (info)"] if k == "STABLE" else [])
            for per in show:
                a, b = PERIODS[per]
                d = ev[(ev.market == mk) & (ev.date >= a) & (ev.date <= b) & ev[k].notna()]
                out = {}
                for nm, x in (("All", d), ("Regime ON", d[d[k] > 0.5]), ("Regime OFF", d[d[k] <= 0.5])):
                    t, s = trade_stats(x), pstats(returns(x, idx_map, closes[mk], mk), mk, per)
                    out[nm] = (t, s)
                    evidence.append({"measure": k, "market": mk, "period": per, "group": nm, "trades": t["n"],
                                     "win_rate": round(t["win"], 4) if t["n"] else None,
                                     "avg_trade": round(t["avg"], 4) if t["n"] else None})
                    md.append(f"| {mk} | {per} | {nm} | {t['n']} | {t['win']:.0%} | {t['avg']:+.1%} | {t['pf']:.2f} | "
                              f"{s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} |")
                if per in pers:
                    (ta, sa), (tf, sf) = out["All"], out["Regime ON"]
                    res.append(tf["n"] >= 20 and tf["win"] - ta["win"] >= 0.03 and tf["avg"] > ta["avg"]
                               and sf["sharpe"] > sa["sharpe"])
            ok[mk] = all(res)
        v = all(ok[m] for m in judged)
        verdicts[f"{k} filter"] = v
        md += ["", f"**Verdict: {'PASS' if v else 'FAIL'}** (judged on {', '.join(judged)}; "
                   f"{'EGX shown for information' if info else ''}).", ""]

    # ---- timing test: hold the market only when the regime is ON ----
    md += ["## Timing: hold the market only when the regime is ON (else cash at 0%)", "",
           "| Market | Period | Strategy | CAGR | Sharpe | Max DD | Time invested |", "|---|---|---|---|---|---|---|"]
    us_r = closes["US"].pct_change(fill_method=None).clip(-0.5, 0.5).mean(axis=1).fillna(0)
    btc = closes["Crypto"]["BTC-USD"].dropna()
    mk_series = {"US": (us_r, (1 + us_r).cumprod(), ["FED"]), "Crypto": (btc.pct_change().fillna(0), btc, ["FED", "STABLE", "CHAIN"])}
    for mk, (r, px, keys) in mk_series.items():
        sma = px.rolling(200).mean()
        strategies = {"Buy & hold": pd.Series(1.0, index=r.index),
                      "200-day rule": (px > sma).astype(float).where(sma.notna(), 0.0)}
        for k in keys:
            strategies[f"{k} ON"] = pd.Series(at(reg[k].astype(float), r.index), index=r.index).fillna(0)
        for k in keys:
            judged_pers = plan[k][1]
            on = strategies[f"{k} ON"]
            res = []
            for per in judged_pers:
                a, b = PERIODS[per]
                yr = 365 if mk == "Crypto" else 252
                cost = 0.001 if mk == "Crypto" else 0.0005
                sr = {}
                for nm in ("Buy & hold", "200-day rule", f"{k} ON"):
                    w = strategies[nm].shift(1).fillna(0)
                    rr = (w * r - cost * w.diff().abs().fillna(0)).loc[a:b]
                    sr[nm] = stats(rr, year=yr)
                    if not (nm != f"{k} ON" and k != keys[0]):
                        md.append(f"| {mk} | {per} | {nm} | {sr[nm]['cagr']:.1%} | {sr[nm]['sharpe']:.2f} | "
                                  f"{sr[nm]['max_dd']:.0%} | {w.loc[a:b].mean():.0%} |")
                res.append(sr[f"{k} ON"]["sharpe"] > sr["Buy & hold"]["sharpe"]
                           and sr[f"{k} ON"]["max_dd"] > sr["Buy & hold"]["max_dd"])
            verdicts[f"{k} timing ({mk})"] = all(res)
    md += ["", "## Verdicts (pre-registered)", "", "| Test | Result |", "|---|---|"] + \
          [f"| {k} | **{'PASS' if v else 'FAIL'}** |" for k, v in verdicts.items()]
    md += ["", f"Latest readings: Fed net liquidity ${nl.dropna().iloc[-1] / 1e6:.2f} trillion "
               f"({'ON' if reg['FED'].dropna().iloc[-1] else 'OFF'}); stablecoins ${sc.dropna().iloc[-1] / 1e9:.0f} billion "
               f"({'ON' if reg['STABLE'].dropna().iloc[-1] else 'OFF'}); Bitcoin on-chain "
               f"{'ON' if reg['CHAIN'].dropna().iloc[-1] else 'OFF'}."]
    pd.DataFrame(evidence).to_csv(OUT / "evidence.csv", index=False)
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
