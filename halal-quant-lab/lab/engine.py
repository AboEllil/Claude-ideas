"""Two backtest engines. Both are free of look-ahead: signals use data up to the
close of day t and trades happen on day t+1.

rotation  - every week/month rank the universe, hold the top N; between
            rebalances positions drift with the market (true buy-and-hold).
swing     - event-driven: enter on a confluence signal at next open, exit on an
            ATR trailing stop, a time stop or a trend break, also at next open.
"""
import numpy as np
import pandas as pd

from .signals import Features, rotation_score, swing_signals


def rebalance_days(index, freq):
    s = pd.Series(index, index=index)
    key = index.to_period("W" if freq == "W" else "M")
    return set(s.groupby(key).max())


def backtest_rotation(F: Features, cfg, cost=0.0005):
    C = F.C.to_numpy()
    rets = np.nan_to_num(F.C.pct_change().to_numpy(), nan=0.0)
    score = rotation_score(F, cfg).to_numpy()
    regime = F.get("regime", cfg["regime_n"], cfg["vix_max"]).to_numpy()
    vol = F.get("vol", 60).to_numpy()
    idx = F.C.index
    rb = rebalance_days(idx, cfg["rebalance"])
    T, N = C.shape

    equity = np.ones(T)
    w = np.zeros(N)           # current (drifted) weights, fraction of equity
    pending = None            # target weights decided at close t, traded at close t+1
    eq = 1.0
    for t in range(1, T):
        # Earn day t return on yesterday's holdings.
        port_r = float(w @ rets[t])
        eq *= 1 + port_r
        if 1 + port_r != 0:
            w = w * (1 + rets[t]) / (1 + port_r)
        if pending is not None:
            eq *= 1 - cost * np.abs(pending - w).sum()
            w = pending
            pending = None
        equity[t] = eq
        if idx[t] in rb:
            target = np.zeros(N)
            if not cfg["regime"] or regime[t]:
                s = score[t]
                ok = np.where(~np.isnan(s))[0]
                if len(ok):
                    top = ok[np.argsort(-s[ok])[: cfg["top_n"]]]
                    if cfg["weighting"] == "invvol":
                        iv = 1 / np.nan_to_num(vol[t, top], nan=np.nanmedian(vol[t]))
                        target[top] = iv / iv.sum()
                    else:
                        target[top] = 1 / len(top)
            pending = target
    holdings = pd.Series(w, index=F.C.columns)
    return pd.Series(equity, index=idx).pct_change().fillna(0), holdings[holdings > 0], []


def backtest_swing(F: Features, cfg, cost=0.0005):
    entry, exit_sig, rank = swing_signals(F, cfg)
    O, C = F.O.to_numpy(), F.C.to_numpy()
    E, X, R = entry.to_numpy(), exit_sig.to_numpy(), rank.to_numpy()
    A = F.get("atr", 14).to_numpy()
    T, N = C.shape
    k, max_hold, max_pos = cfg["atr_k"], cfg["max_hold"], cfg["max_pos"]

    cash, shares = 1.0, np.zeros(N)
    stop, high, held, entry_px = np.zeros(N), np.zeros(N), np.zeros(N, int), np.zeros(N)
    to_buy, to_sell = [], []
    equity, trades = np.zeros(T), []
    for t in range(T):
        o = np.where(np.isnan(O[t]), C[t - 1] if t else C[t], O[t])
        for j in to_sell:
            cash += shares[j] * o[j] * (1 - cost)
            trades.append(o[j] * (1 - cost) / (entry_px[j] * (1 + cost)) - 1)
            shares[j] = 0
        if to_buy:
            eq_open = cash + np.nansum(shares * o)
            slot = eq_open / max_pos
            for j in to_buy:
                amt = min(slot, cash)
                if amt <= 0 or np.isnan(o[j]) or o[j] <= 0:
                    continue
                shares[j] = amt * (1 - cost) / o[j]
                cash -= amt
                entry_px[j] = high[j] = o[j]
                a0 = A[t - 1, j] if t and not np.isnan(A[t - 1, j]) else 0.05 * o[j]
                stop[j] = o[j] - k * a0
                held[j] = 0
        to_buy, to_sell = [], []
        equity[t] = cash + np.nansum(shares * C[t])

        # Manage open positions on today's close; exits execute tomorrow.
        pos = np.where(shares > 0)[0]
        for j in pos:
            held[j] += 1
            high[j] = max(high[j], C[t, j])
            if not np.isnan(A[t, j]):
                stop[j] = max(stop[j], high[j] - k * A[t, j])
            if C[t, j] < stop[j] or held[j] >= max_hold or X[t, j]:
                to_sell.append(j)
        free = max_pos - (len(pos) - len(to_sell))
        if free > 0 and t + 1 < T:
            cand = np.where(E[t] & (shares == 0))[0]
            if len(cand):
                to_buy = list(cand[np.argsort(-R[t, cand])[:free]])
    holdings = pd.Series(shares * C[-1], index=F.C.columns)
    holdings = holdings[holdings > 0] / equity[-1]
    return pd.Series(equity, index=F.C.index).pct_change().fillna(0), holdings, trades


def run(F, cfg, cost=0.0005):
    fn = backtest_rotation if cfg["family"] == "rotation" else backtest_swing
    return fn(F, cfg, cost)
