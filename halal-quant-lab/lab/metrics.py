"""Performance statistics, including the Deflated Sharpe Ratio.

The Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014) answers: "given that
we tried N strategies, what is the probability the best Sharpe is real skill
and not luck?" Values above ~0.95 are convincing; below 0.5 means noise.
"""
from statistics import NormalDist

import numpy as np
import pandas as pd

YEAR = 252
_N = NormalDist()


def stats(r: pd.Series, trades=None):
    r = r.dropna()
    if len(r) < 20 or r.std() == 0:
        return {"cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "sortino": 0.0, "max_dd": 0.0,
                "calmar": 0.0, "exposure": 0.0, "trades": 0, "win_rate": np.nan}
    eq = (1 + r).cumprod()
    years = len(r) / YEAR
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = r.std() * np.sqrt(YEAR)
    down = r[r < 0].std() * np.sqrt(YEAR)
    dd = (eq / eq.cummax() - 1).min()
    out = {
        "cagr": cagr, "vol": vol,
        "sharpe": r.mean() / r.std() * np.sqrt(YEAR),
        "sortino": r.mean() * YEAR / down if down else 0.0,
        "max_dd": dd, "calmar": cagr / -dd if dd < 0 else 0.0,
        "exposure": float((r != 0).mean()),   # share of days with a P&L, not capital invested
    }
    if trades is not None:
        out["trades"] = len(trades)
        out["win_rate"] = float(np.mean(np.array(trades) > 0)) if trades else np.nan
    return out


def drawdown(r):
    eq = (1 + r).cumprod()
    return eq / eq.cummax() - 1


def yearly(r):
    return (1 + r).groupby(r.index.year).prod() - 1


def deflated_sharpe(best: pd.Series, all_sharpes, ):
    """Probability that `best`'s Sharpe beats the max Sharpe expected from luck alone."""
    r = best.dropna()
    n_trials = max(len(all_sharpes), 2)
    sr = r.mean() / r.std()                                   # per-day Sharpe
    var_trials = np.var(np.asarray(all_sharpes) / np.sqrt(YEAR))
    g = 0.5772156649                                          # Euler-Mascheroni
    sr0 = np.sqrt(var_trials) * ((1 - g) * _N.inv_cdf(1 - 1 / n_trials)
                                 + g * _N.inv_cdf(1 - 1 / (n_trials * np.e)))
    skew, kurt = r.skew(), r.kurt() + 3
    denom = np.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    return _N.cdf((sr - sr0) * np.sqrt(len(r) - 1) / denom)
