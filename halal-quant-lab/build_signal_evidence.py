"""History behind each buy signal's strength meter: how often past signals like it won.

    python build_signal_evidence.py      # needs data/ml_signals2_events.pkl (made by run_ml_signals2.py)

Strength = how many of 5 confirmations hold at the signal close (chosen from the user's own system and earlier
tests, not tuned):
  1. weekly AlgoAlpha SuperTrend green        2. daily AlgoAlpha SuperTrend green
  3. Squeeze momentum bright green             4. Lorentzian green arrow in the last 5 days
  5. backdrop: market above its 200-day average (US, EGX) / Fed net liquidity rising (crypto)
  Strong = 4-5, Medium = 3, Weak = 0-2.
Trades as everywhere in the lab: bought at the next close, half sold at +2 ATR, then stop at entry, costs.
Finding (2 Nov 2026): strength separates winners in BOTH periods for EGX and crypto, NOT for US stocks.
Writes reports/signal_board/signal_evidence.csv (committed; the daily scanner reads it).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from lab.liquidity import regimes
from lab.universe import DATA

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "signal_board" / "signal_evidence.csv"


def strength_label(n):
    return "Strong" if n >= 4 else "Medium" if n == 3 else "Weak"


def main():
    ev, _, _ = pd.read_pickle(DATA / "ml_signals2_events.pkl")
    ev = ev[ev.ret.notna() & (ev.date >= "2016-01-01")].copy()
    fed = regimes()[0]["FED"].dropna().astype(float)
    ev["fed_on"] = fed.reindex(fed.index.union(ev.date.unique())).ffill().reindex(ev.date).to_numpy()
    checks = pd.DataFrame({
        "c1": ev.weekly_up > 0.5, "c2": ev.st_up > 0.5, "c3": (ev.sq_mom > 0) & (ev.sq_slope > 0),
        "c4": ev.lor_arrow5 > 0.5, "c5": np.where(ev.market == "Crypto", ev.fed_on > 0.5, ev.mkt_up200 > 0.5)})
    ev["strength"] = checks.sum(axis=1).map(strength_label)
    rows = []
    for (mk, src, st), g in ev.groupby(["market", "source", "strength"]):
        r = {"market": mk, "rule": src, "strength": st, "trades": len(g),
             "win_rate": round(float((g.ret > 0).mean()), 4), "avg_trade": round(float(g.ret.mean()), 4)}
        for per, part in (("2016_2020", g[g.date < "2021-01-01"]), ("2021_today", g[g.date >= "2021-01-01"])):
            r[f"win_{per}"] = round(float((part.ret > 0).mean()), 4) if len(part) else None
            r[f"trades_{per}"] = len(part)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
