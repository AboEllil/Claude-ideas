"""Single-stock long-only engine for target-position strategies.

pos[t] is decided at the close of bar t and becomes the holding from the open of
bar t+1. Entry earns open->close on the entry day, exit earns close->open on the
exit day, and every change pays `cost` per side.
"""
import numpy as np
import pandas as pd


def run_position(o, c, pos, cost=0.0005):
    p = np.r_[0.0, pos[:-1]]                 # holding during bar t (decided at t-1)
    pp = np.r_[0.0, p[:-1]]                  # holding during bar t-1
    prev_c = np.r_[np.nan, c[:-1]]
    hold = p * pp * (c / prev_c - 1)
    enter = p * (1 - pp) * (c / o - 1)
    leave = (1 - p) * pp * (o / prev_c - 1)
    r = np.nan_to_num(hold + enter + leave) - cost * np.abs(p - pp)
    return r, p


def trades(o, c, p, cost=0.0005):
    """Per-trade returns (entry at open, exit at open, costs included)."""
    out, entry = [], None
    for t in range(1, len(p)):
        if p[t] == 1 and p[t - 1] == 0:
            entry = o[t]
        elif p[t] == 0 and p[t - 1] == 1 and entry:
            out.append(o[t] * (1 - cost) / (entry * (1 + cost)) - 1)
            entry = None
    if entry:
        out.append(c[-1] * (1 - cost) / (entry * (1 + cost)) - 1)
    return out


def run_strategy(df: pd.DataFrame, fn, start, cost=0.0005, **kw):
    """Run `fn(o, h, l, c, **kw) -> (pos, ...)` on one stock; returns daily returns from `start`,
    exposure and trade list (trades counted from `start` only)."""
    df = df.dropna()
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    kw = {k: (v.reindex(df.index).ffill().to_numpy(float) if isinstance(v, pd.Series) else v)
          for k, v in kw.items()}
    res = fn(o, h, l, c, **kw)
    pos = res[0] if isinstance(res, tuple) else res
    r, p = run_position(o, c, pos, cost)
    s = pd.Series(r, index=df.index)
    m = (df.index >= start)
    tr = trades(o[m], c[m], p[m], cost) if m.any() else []
    return s.loc[start:], float(p[m].mean()) if m.any() else 0.0, tr
