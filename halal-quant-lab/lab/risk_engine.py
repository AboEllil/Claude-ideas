"""Portfolio engine with ATR risk sizing and chandelier trailing stops (long-only, no leverage).

Per stock, a signal array `sig` (1 = setup valid) decided at the close. Rules:
  entry   : sig turns on (and optional RVOL footprint) -> buy at next open
  size    : weight = risk_per_trade / (k * ATR14 / close), capped at max_weight and by cash
            (so a stop-out loses ~risk_per_trade of equity, before gaps)
  stop    : chandelier trailing stop = highest close since entry - k * ATR14, never lowered
  exit    : close below the stop, or sig turns off -> sell at next open
Costs per side apply to every trade. Cash earns 0% (no interest).
"""
import numpy as np
import pandas as pd


def run(O, H, L, C, V, SIG, risk=0.01, k=3.0, max_weight=0.20, cost=0.0005, rvol_min=0.0, risk_scale=None,
        return_state=False):
    """All inputs are DataFrames (dates x tickers) on the same index. Returns daily returns,
    invested fraction and trade list; with `return_state`, also the open positions and the
    orders decided at the last close (to execute at the next open) - used by monitor.py."""
    idx = C.index
    o, c = O.to_numpy(float), C.to_numpy(float)
    tr = np.fmax(H - L, np.fmax((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().to_numpy()
    rvol = (V / V.rolling(20, min_periods=20).mean().shift(1)).to_numpy()
    sig = SIG.reindex(idx).fillna(0).to_numpy() > 0.5
    # Optional per-day multiplier on the risk budget for NEW entries (e.g. market-volatility scaling).
    scale = np.ones(len(idx)) if risk_scale is None else risk_scale.reindex(idx).ffill().fillna(1).to_numpy()
    T, N = c.shape
    cash, sh = 1.0, np.zeros(N)
    stop, hi, entry_px = np.zeros(N), np.zeros(N), np.zeros(N)
    entry_t = np.zeros(N, int)
    why = {}
    buy, sell = [], []
    eq_out, inv_out, trades = np.ones(T), np.zeros(T), []
    lp = np.full(N, np.nan)                       # last known price (for missing bars)
    for t in range(T):
        op = np.where(np.isnan(o[t]), lp, o[t])
        sell = [j for j in sell if op[j] > 0]     # cannot trade without a price; keep holding
        for j in sell:
            cash += sh[j] * op[j] * (1 - cost)
            trades.append(op[j] * (1 - cost) / (entry_px[j] * (1 + cost)) - 1)
            sh[j] = 0
        if buy:
            eq = cash + np.nansum(sh * op)
            for j, w in buy:
                amt = min(w * eq, cash)
                if amt <= 0 or not op[j] > 0:
                    continue
                sh[j] = amt * (1 - cost) / op[j]
                cash -= amt
                entry_px[j] = hi[j] = op[j]
                stop[j] = op[j] - k * atr[t - 1, j]
                entry_t[j] = t
        buy, sell = [], []
        lp = np.where(np.isnan(c[t]), lp, c[t])
        val = np.nansum(sh * lp)
        eq_out[t] = cash + val
        inv_out[t] = val / eq_out[t] if eq_out[t] else 0
        if t + 1 >= T and not return_state:
            break
        why = {}
        for j in np.where(sh > 0)[0]:
            if np.isnan(c[t, j]):
                continue
            hi[j] = max(hi[j], c[t, j])
            if not np.isnan(atr[t, j]):
                stop[j] = max(stop[j], hi[j] - k * atr[t, j])
            if c[t, j] < stop[j] or not sig[t, j]:
                sell.append(j)
                why[j] = "trailing stop hit" if c[t, j] < stop[j] else "trend/structure turned bearish"
        new = [j for j in range(N) if sig[t, j] and sh[j] == 0 and t and not sig[t - 1, j]
               and not np.isnan(atr[t, j]) and (rvol_min == 0 or rvol[t, j] >= rvol_min)]
        # Strongest setups first: smallest ATR% (= largest allowed size) is NOT a ranking of
        # quality, so keep the order deterministic by ticker and let cash be the limit.
        for j in new:
            w = min(risk * scale[t] / (k * atr[t, j] / c[t, j]), max_weight)
            buy.append((j, w))
    r = pd.Series(eq_out, index=idx).pct_change().fillna(0)
    if not return_state:
        return r, pd.Series(inv_out, index=idx), trades
    cols = list(C.columns)
    held = [{"ticker": cols[j], "entry_date": idx[entry_t[j]], "entry_price": entry_px[j],
             "last_close": lp[j], "stop": stop[j], "weight": sh[j] * lp[j] / eq_out[-1],
             "gain": lp[j] / entry_px[j] - 1} for j in np.where(sh > 0)[0]]
    state = {"date": idx[-1], "holdings": held,
             "sells": [{"ticker": cols[j], "last_close": lp[j], "reason": why[j]} for j in sell],
             "buys": [{"ticker": cols[j], "last_close": c[-1, j], "weight": w, "atr": atr[-1, j],
                       "stop": c[-1, j] - k * atr[-1, j]} for j, w in buy],
             "equity": eq_out[-1]}
    return r, pd.Series(inv_out, index=idx), trades, state


def purification(tickers, fetch):
    """Estimated dividend purification per stock.
    impure share of income ~ interest income / total revenue (the main non-permissible source
    for screened companies); purify that share of each dividend received."""
    rows = []
    for t in tickers:
        try:
            tk = fetch(t)
            inc = tk.income_stmt
            rev = inc.loc["Total Revenue"].iloc[0] if "Total Revenue" in inc.index else np.nan
            ii = inc.loc["Interest Income"].iloc[0] if "Interest Income" in inc.index else 0.0
            dy = (tk.info or {}).get("dividendYield") or 0.0
            dy = dy / 100                                  # yfinance reports dividendYield in %
        except Exception:
            rev, ii, dy = np.nan, np.nan, np.nan
        ratio = ii / rev if rev and rev > 0 and not np.isnan(ii) else np.nan
        rows.append({"ticker": t, "dividend_yield": dy, "interest_income_pct_revenue": ratio,
                     "purify_pct_of_dividends": ratio,
                     "purify_per_10k_invested_usd": 10_000 * dy * ratio if ratio == ratio else np.nan})
    return pd.DataFrame(rows).set_index("ticker")
