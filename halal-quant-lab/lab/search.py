"""Mass strategy search and walk-forward selection.

Every config is backtested once over the full history, giving one daily return
stream per config. Walk-forward then, for each year Y, picks the configs that
did best over the previous `train_years` only, and records what they earned in
year Y. Stitching those years gives a curve where every day was traded by a
strategy chosen without seeing that day - the honest estimate.
"""
import random
import time

import numpy as np
import pandas as pd

from . import engine
from .metrics import stats

SWING_CONCEPTS = ("strong", "momentum", "rel_strength", "pullback", "bb_dip", "breakout", "volume")


def sample_rotation(rng):
    w = {k: rng.choice([0, 0.5, 1, 2]) for k in ("w_mom", "w_short", "w_lowvol", "w_strength", "w_dip")}
    if not any(w.values()):
        w["w_mom"] = 1
    return {
        "family": "rotation", **w,
        "mom_lb": rng.choice([126, 189, 252]),
        "trend_n": rng.choice([50, 100, 150, 200]),
        "top_n": rng.choice([5, 8, 10, 15, 20]),
        "rebalance": rng.choice(["W", "M"]),
        "weighting": rng.choice(["equal", "invvol"]),
        "regime": rng.random() < 0.7,
        "regime_n": rng.choice([100, 150, 200]),
        "vix_max": rng.choice([25, 30, 40, 100]),
    }


def sample_swing(rng):
    w = {k: rng.choice([0, 0, 1, 1, 2]) for k in SWING_CONCEPTS}
    if sum(w.values()) < 2:
        w[rng.choice(SWING_CONCEPTS)] += 2
    rsi_n = rng.choice([2, 3, 5, 14])
    return {
        "family": "swing", "w": w,
        "threshold": rng.choice([0.4, 0.5, 0.6, 0.7]),
        "require_trend": rng.random() < 0.8,
        "trend_n": rng.choice([50, 100, 150, 200]),
        "adx_th": rng.choice([15, 20, 25, 30]),
        "mom_lb": rng.choice([126, 252]),
        "mom_q": rng.choice([0.5, 0.7, 0.8]),
        "rs_n": rng.choice([21, 63, 126]),
        "rsi_n": rsi_n,
        "rsi_th": rng.choice([10, 20, 30] if rsi_n <= 3 else [30, 40, 45]),
        "bb_z": rng.choice([1.0, 1.5, 2.0]),
        "break_n": rng.choice([20, 55, 100]),
        "vol_mult": rng.choice([1.2, 1.5, 2.0]),
        "max_pos": rng.choice([5, 8, 10, 15]),
        "atr_k": rng.choice([2.0, 3.0, 4.0, 5.0]),
        "max_hold": rng.choice([10, 20, 40, 60, 120]),
        "exit_n": rng.choice([10, 20, 50, 100]),
        "regime": rng.random() < 0.7,
        "regime_n": rng.choice([100, 150, 200]),
        "vix_max": rng.choice([25, 30, 40, 100]),
    }


def describe(cfg):
    if cfg["family"] == "rotation":
        f = [f"{k[2:]}x{cfg[k]:g}" for k in ("w_mom", "w_short", "w_lowvol", "w_strength", "w_dip") if cfg[k]]
        return (f"ROTATION top{cfg['top_n']} {cfg['rebalance']} {cfg['weighting']} | "
                f"score={'+'.join(f)} mom{cfg['mom_lb']} | trend>SMA{cfg['trend_n']}"
                + (f" | regime SPY>SMA{cfg['regime_n']} VIX<{cfg['vix_max']}" if cfg["regime"] else ""))
    f = [f"{k}x{v}" for k, v in cfg["w"].items() if v]
    return (f"SWING max{cfg['max_pos']} | vote({'+'.join(f)})>={cfg['threshold']:.0%}"
            + (f" trend>SMA{cfg['trend_n']}" if cfg["require_trend"] else "")
            + f" | exit ATRx{cfg['atr_k']:g}, {cfg['max_hold']}d, <SMA{cfg['exit_n']}"
            + (f" | regime SPY>SMA{cfg['regime_n']} VIX<{cfg['vix_max']}" if cfg["regime"] else ""))


def run_many(F, n_rotation, n_swing, cost, seed=7, log_every=50):
    rng = random.Random(seed)
    cfgs = [sample_rotation(rng) for _ in range(n_rotation)] + [sample_swing(rng) for _ in range(n_swing)]
    returns, rows, t0 = {}, [], time.time()
    for i, cfg in enumerate(cfgs):
        r, _, trades = engine.run(F, cfg, cost)
        returns[i] = r
        rows.append({"id": i, "family": cfg["family"], "desc": describe(cfg),
                     **stats(r, trades if cfg["family"] == "swing" else None)})
        if (i + 1) % log_every == 0:
            print(f"  {i + 1}/{len(cfgs)} configs tested ({time.time() - t0:.0f}s)")
    return cfgs, pd.DataFrame(returns), pd.DataFrame(rows).set_index("id")


def train_score(r, max_dd_limit):
    s = stats(r)
    if s["max_dd"] < max_dd_limit or s["exposure"] < 0.3:
        return -np.inf
    return s["sharpe"]


def walk_forward(R: pd.DataFrame, first_year, train_years=5, top_k=3, max_dd_limit=-0.35):
    """Return stitched out-of-sample daily returns and the configs chosen each year."""
    oos, picks = [], []
    years = sorted(set(R.index.year))
    for y in [y for y in years if y >= first_year]:
        train = R[(R.index.year >= y - train_years) & (R.index.year < y)]
        scores = train.apply(train_score, max_dd_limit=max_dd_limit).sort_values(ascending=False)
        chosen = [c for c in scores.index[:top_k] if np.isfinite(scores[c])] or list(scores.index[:1])
        test = R.loc[R.index.year == y, chosen].mean(axis=1)   # equal-weight blend of the winners
        oos.append(test)
        picks.append({"year": y, "chosen": chosen, "train_sharpe": [round(scores[c], 2) for c in chosen],
                      "oos_return": float((1 + test).prod() - 1)})
    return pd.concat(oos), pd.DataFrame(picks)
