"""Signal board: halal US stocks ($2B+), halal ETFs, top crypto coins and halal EGX stocks, with a verdict.

    python market_scanner.py      # writes reports/signal_board/signals.csv

Indicators (the ones that tested best, see reports/tv/INDICATORS.md and reports/exits/REPORT.md):
  trend      ML Adaptive SuperTrend (AlgoAlpha) - green / red, days in trend, stop line
  momentum   Squeeze Momentum (LazyBear) - bright green / dark green / red / maroon
  ML         Lorentzian Classification (jdehorty) - green arrow in the last 5 days, or bias
  structure  Market structure (last break of structure up or down, 5-bar swings)
Verdict - one rule per market, the best ones in reports/evidence, signal_lab and winrate:
  US stocks / ETFs  200-day trend: in while close > 200-day SMA (stop = the SMA)
  EGX               swing trend stack: EMA50 > EMA200, ADX > 20, close above the 20-day high; exit on a
                    3 x ATR trail from the highest close or a close below EMA50
  Crypto            the user's arrow + bright squeeze, only with the weekly SuperTrend green; exit red arrow
  STRONG BUY  new entry (last 3 days) confirmed by the weekly trend and the user's arrow / volume / Lorentzian
  BUY         new entry, or the user's arrow + bright squeeze + weekly green inside an existing uptrend
  HOLD        in the rule's uptrend - keep it, stop as shown; at +2 ATR from entry: sell half, stop to entry
  SELL        the rule exited in the last 3 days        AVOID   no uptrend
ML score: walk-forward-tested model's probability of beating the market over 20 days (tie-breaker only).
A buy signal on a thinly traded asset (20-day median traded value under $5M, or EGP 1M on EGX)
is downgraded to HOLD and flagged. Per asset it also reports how this system did on that asset's own
history vs buy & hold. Universe lists: reports/broad_screen.csv (large caps), reports/universe/
midcap_screen.csv and crypto_list.json (refresh with `python -m lab.expand`), lab/egx.py (EGX).
Not financial advice. Shariah status of crypto is debated; verify stocks with a Shariah screener.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import json

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.egx import halal_egx
from lab.metrics import stats
from lab.single import run_position

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "signal_board"
HIST_START = "2016-01-01"

ETFS = {"SPUS": "SP Funds S&P 500 Sharia ETF", "HLAL": "Wahed FTSE USA Shariah ETF",
        "UMMA": "Wahed Dow Jones Islamic World ex-US ETF", "SPRE": "SP Funds Global REIT Sharia ETF",
        "SPSK": "SP Funds Global Sukuk ETF", "SPTE": "SP Funds Global Technology ETF",
        "SPWO": "SP Funds World ex-US ETF"}
UNIVERSE = ROOT / "reports" / "universe"
# Restaurant / entertainment chains with large bar (alcohol) sales - excluded on top of the screen.
ALCOHOL_HEAVY = {"EAT", "DRI", "TXRH", "CAKE", "BJRI", "BLMN", "DIN", "PLAY", "CHUY", "RRGB", "KRUS", "FWRG",
                 "BH", "DENN", "CBRL", "STKS", "ARKR", "TAST", "NATH"}
COST = {"Crypto": 0.001, "EGX stock": 0.0025}
MIN_VALUE = {"EGX stock": 1_000_000}          # local currency per day; everything else uses $5M
CURRENCY = {"EGX stock": "EGP"}


RULE = {"US stock": "200-day trend", "Halal ETF": "200-day trend", "EGX stock": "Swing trend stack",
        "Crypto": "Arrow + squeeze + weekly"}


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def analyse(args):
    tk, df, kind = args
    vol_series = df["Volume"] if "Volume" in df else None
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if kind == "EGX stock":                                 # drop impossible daily moves (data errors)
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 300:
        return None
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    T = len(c)
    vol = tv.atr(h, l, c, 10)
    a = tv._kmeans_atr(vol, 100, 0.75, 0.5, 0.25)
    st = (tv.supertrend(h, l, c, a, 3.0) == 1).astype(float)
    _, mom = tv.squeeze(o, h, l, c)
    lpos, pred = tv.lorentzian(o, h, l, c)
    trend_s = tv.smc_state(h, l, c, 5)[0]
    a14 = tv.atr(h, l, c, 14)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip_up = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    flip_dn = np.r_[False, (st[1:] == 0) & (st[:-1] == 1)]
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]
    v = vol_series.reindex(df.index).fillna(0).to_numpy(float) if vol_series is not None else np.zeros(T)
    vol_ratio = v / pd.Series(v).rolling(20).mean().shift(1).to_numpy()
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    weekly = (pd.Series(tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0],
                        index=wk.index).shift(1).reindex(df.index, method="ffill").fillna(0).to_numpy() > 0.5
              if len(wk) > 120 else np.zeros(T, bool))

    # SuperTrend line (stop level)
    src = (h + l) / 2
    lo, up = src - 3 * a, src + 3 * a
    plo = pup = np.nan
    for t in range(T):
        if np.isnan(a[t]):
            continue
        if not np.isnan(plo):
            lo[t] = lo[t] if (lo[t] > plo or c[t - 1] < plo) else plo
            up[t] = up[t] if (up[t] < pup or c[t - 1] > pup) else pup
        plo, pup = lo[t], up[t]
    st_line = np.where(st == 1, lo, up)
    run = 1
    while run < T and st[-1 - run] == st[-1]:
        run += 1
    value = float((df.Close * pd.Series(v, index=df.index)).rolling(20).median().iloc[-1])
    liquid = not (value < MIN_VALUE.get(kind, 5_000_000))
    user_sig = flip_up & bright                                         # the user's green-arrow rule
    user_recent = bool(user_sig[-3:].any()) and st[-1] == 1
    lor5 = bool(larrow[-6:].any())

    # ---- position history of this market's rule (decided at each close) ----
    pos = np.zeros(T)
    entry_t = np.full(T, -1)
    if kind in ("US stock", "Halal ETF"):                               # 200-day rule
        sma200 = pd.Series(c).rolling(200).mean().to_numpy()
        pos = np.nan_to_num((c > sma200).astype(float))
        stop_now = sma200[-1]
    elif kind == "EGX stock":                                           # swing trend stack
        e50, e200 = _ema(c, 50), _ema(c, 200)
        up_, dn_ = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
        pdm = np.where((up_ > dn_) & (up_ > 0), up_, 0.0)
        mdm = np.where((dn_ > up_) & (dn_ > 0), dn_, 0.0)
        adx = tv.rma(100 * np.abs(tv.rma(pdm, 14) - tv.rma(mdm, 14)) / (tv.rma(pdm, 14) + tv.rma(mdm, 14)), 14)
        don = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        hi = 0.0
        trail = np.full(T, np.nan)
        for t in range(1, T):
            if pos[t - 1]:
                hi = max(hi, c[t])
                trail[t] = max(hi - 3 * a14[t], e50[t])
                pos[t] = 0 if (c[t] < hi - 3 * a14[t] or c[t] < e50[t]) else 1
            elif e50[t] > e200[t] and adx[t] > 20 and c[t] > don[t]:
                pos[t], hi = 1, c[t]
                trail[t] = max(hi - 3 * a14[t], e50[t])
        stop_now = trail[-1] if pos[-1] else st_line[-1]
    else:                                                               # crypto: arrow + squeeze + weekly
        for t in range(1, T):
            pos[t] = (1 if st[t] == 1 else 0) if pos[t - 1] else (1 if user_sig[t] and weekly[t] else 0)
        stop_now = st_line[-1]
    for t in range(1, T):
        entry_t[t] = (t if not pos[t - 1] else entry_t[t - 1]) if pos[t] else -1
    entered = pos[-1] == 1 and entry_t[-1] >= T - 3
    exited = pos[-1] == 0 and pos[-4:-1].any()

    if entered and not liquid:
        verdict = "HOLD"
    elif entered:
        confirm = weekly[-1] and (user_recent or (kind == "EGX stock" and np.nan_to_num(vol_ratio[-1]) >= 1.5)
                                  or (kind == "Crypto" and lor5))
        verdict = "STRONG BUY" if confirm else "BUY"
    elif pos[-1] == 1:
        verdict = "HOLD"
    elif exited:
        verdict = "SELL"
    else:
        verdict = "AVOID"
    # The user's own green-arrow signal while this market's rule is already in an uptrend: still a buy
    if verdict == "HOLD" and user_recent and weekly[-1] and liquid and kind != "Crypto":
        verdict = "BUY"

    # Take-profit (+2 ATR: sell half) and breakeven (move the stop to entry) only for fresh positions
    if verdict in ("BUY", "STRONG BUY"):
        e_px, e_atr = c[-1], a14[-1]
    elif pos[-1] == 1 and entry_t[-1] >= T - 126:
        e_px, e_atr = c[entry_t[-1]], a14[entry_t[-1]]
    else:
        e_px, e_atr = np.nan, np.nan
    tp = e_px + 2 * e_atr
    tp_hit = bool(pos[-1] == 1 and np.isfinite(tp) and c[-1] >= tp)
    sq = "bright green" if bright[-1] else "dark green" if m[-1] > 0 else "red" if m[-1] < m[-2] else "maroon"
    lor = "green arrow" if lor5 else "bullish" if pred[-1] > 0 else "bearish" if pred[-1] < 0 else "neutral"
    score = (40 * st[-1] + (20 if bright[-1] else 10 if m[-1] > 0 else 0)
             + (20 if lor5 else 10 if pred[-1] > 0 else 0) + (20 if trend_s[-1] == 1 else 0))
    rule = RULE[kind]
    reasons = {
        "STRONG BUY": f"New {rule} buy, confirmed by the weekly trend"
                      + (" and your green arrow + bright squeeze." if user_recent else "."),
        "BUY": (f"Your green arrow + bright squeeze with the weekly trend green." if pos[-1] == 1 and not entered
                else f"New {rule} buy signal."),
        "HOLD": (f"New buy signal, but thin trading (about {value / 1e6:.1f}M a day) makes it hard to buy and sell."
                 if entered and not liquid else
                 ("Take-profit level reached: sell half and move the stop to your entry price."
                  if tp_hit else f"In an uptrend ({rule}). Keep it; sell on a close below the stop.")),
        "SELL": f"{rule} exit in the last 3 days. Sell if you own it.",
        "AVOID": f"No {rule} uptrend. Wait.",
    }

    history = signal_history(df, kind, rule, c, a14, st, st_line, pos, weekly, user_sig, larrow, vol_ratio, v,
                             sma200 if kind in ("US stock", "Halal ETF") else None,
                             trail if kind == "EGX stock" else None)

    cost = COST.get(kind, 0.0005)
    r, p = run_position(o, c, pos, cost)
    rs = pd.Series(r, index=df.index).loc[HIST_START:]
    bh = df.Close.pct_change().loc[HIST_START:]
    year = 365 if kind == "Crypto" else 252
    s_sys, s_bh = stats(rs, year=year), stats(bh, year=year)
    n_tr = int(((p[1:] == 1) & (p[:-1] == 0))[df.index[1:] >= HIST_START].sum())
    return {
        "symbol": tk, "kind": kind, "strategy": rule, "verdict": verdict, "score": int(score),
        "currency": CURRENCY.get(kind, "USD"), "traded_value_m": round(value / 1e6, 2) if value == value else None,
        "close": round(float(c[-1]), 6), "change_1d": round(float(c[-1] / c[-2] - 1), 4),
        "trend": "up" if st[-1] == 1 else "down", "days_in_trend": int(run),
        "weekly": "green" if weekly[-1] else "red",
        "stop": round(float(stop_now), 6), "stop_distance": round(float(c[-1] / stop_now - 1), 4),
        "take_profit": round(float(tp), 6) if np.isfinite(tp) else None,
        "breakeven": round(float(e_px), 6) if np.isfinite(e_px) else None,
        "squeeze": sq, "lorentzian": lor, "structure": "bullish" if trend_s[-1] == 1 else "bearish",
        "reason": reasons[verdict],
        "hist_from": str(max(df.index[0], pd.Timestamp(HIST_START)).date()),
        "system_cagr": round(float(s_sys["cagr"]), 4), "system_max_dd": round(float(s_sys["max_dd"]), 4),
        "hold_cagr": round(float(s_bh["cagr"]), 4), "hold_max_dd": round(float(s_bh["max_dd"]), 4),
        "trades": n_tr, "as_of": str(df.index[-1].date()), "_history": history,
        # confirmations for the buy explanation (see build_signal_evidence.py)
        "chk_weekly": bool(weekly[-1]), "chk_trend": bool(st[-1] == 1), "chk_squeeze": bool(bright[-1]),
        "chk_lor": lor5,
        "signal_rule": ("Dashboard rule" if entered else "Your rule") if verdict in ("BUY", "STRONG BUY") else "",
    }


HISTORY_DAYS = 365


def signal_history(df, kind, rule, c, a14, st, st_line, pos, weekly, user_sig, larrow, vol_ratio, v, sma200, trail):
    """Every buy / sell this board would have shown in the last HISTORY_DAYS, rebuilt from prices up to each
    day's close only (no look-ahead), plus what happened afterwards (bought at the next close; outcome to the
    rule's exit or to today). Rows for the dashboard's signal calendar."""
    T, idx = len(c), df.index
    value = (pd.Series(c) * pd.Series(v)).rolling(20).median().to_numpy()
    if sma200 is not None:
        stop = sma200
    elif trail is not None:
        stop = np.where(pos == 1, trail, st_line)
    else:
        stop = st_line
    start = idx[-1] - pd.Timedelta(days=HISTORY_DAYS)
    out = []
    for t in range(max(1, T - 400), T):
        if idx[t] < start:
            continue
        liquid = not (np.nan_to_num(value[t]) < MIN_VALUE.get(kind, 5_000_000))
        entry = pos[t] == 1 and pos[t - 1] == 0
        arrow = (kind != "Crypto" and not entry and pos[t] == 1 and pos[t - 1] == 1 and user_sig[t] and weekly[t] > 0.5)
        exit_ = pos[t] == 0 and pos[t - 1] == 1
        if (entry or arrow) and liquid:
            user_recent = bool(user_sig[max(0, t - 2):t + 1].any()) and st[t] == 1
            lor5 = bool(larrow[max(0, t - 5):t + 1].any())
            if entry:
                confirm = weekly[t] > 0.5 and (user_recent or (kind == "EGX stock" and np.nan_to_num(vol_ratio[t]) >= 1.5)
                                               or (kind == "Crypto" and lor5))
                signal, why = ("STRONG BUY" if confirm else "BUY"), f"New {rule} buy"
            else:
                signal, why = "BUY", "Your green arrow + bright squeeze inside the uptrend"
            tp = c[t] + 2 * a14[t]
            j = next((k for k in range(t + 1, T) if pos[k] == 0), None)
            entry_px = c[t + 1] if t + 1 < T else np.nan
            if j is not None:
                exit_px, status, end = (c[j + 1] if j + 1 < T else c[j]), "Closed", j
            else:
                exit_px, status, end = c[-1], "Open", T - 1
            hit = bool(t + 1 < T and np.nanmax(c[t + 1:end + 1]) >= tp) if end > t else False
            out.append({"date": str(idx[t].date()), "signal": signal, "why": why, "close": round(float(c[t]), 6),
                        "stop": round(float(stop[t]), 6) if np.isfinite(stop[t]) else None,
                        "take_profit": round(float(tp), 6) if np.isfinite(tp) else None,
                        "result": round(float(exit_px / entry_px - 1), 4) if np.isfinite(entry_px) else None,
                        "status": status if np.isfinite(entry_px) else "Not bought yet",
                        "exit_date": str(idx[j].date()) if j is not None else "",
                        "hit_take_profit": "yes" if hit else "no", "days": int(end - t)})
        elif exit_:
            out.append({"date": str(idx[t].date()), "signal": "SELL", "why": f"{rule} exit",
                        "close": round(float(c[t]), 6), "stop": None, "take_profit": None,
                        "result": round(float(c[-1] / c[t] - 1), 4), "status": "Price change since the sell",
                        "exit_date": "", "hit_take_profit": "", "days": int(T - 1 - t)})
    return out


def ml_scores(raw, kinds):
    """Probability (0-1) that each asset beats its market over the next 20 trading days, from the model
    saved by `python run_ml_forecast.py --final` (walk-forward tested; see reports/ml/REPORT.md)."""
    import pickle
    from run_ml_forecast import features, finish_panel
    path = ROOT / "reports" / "ml" / "model.pkl"
    if not path.exists():
        return {}
    saved = pickle.loads(path.read_bytes())
    mk = {"US stock": "US", "Halal ETF": "US", "EGX stock": "EGX", "Crypto": "Crypto"}
    close = raw["Close"]
    egx_cols = [t for t, k in kinds.items() if k == "EGX stock" and t in close]
    bench = {"US": close["SPY"].ffill(), "Crypto": close["BTC-USD"].ffill(),
             "EGX": (1 + close[egx_cols].pct_change(fill_method=None).clip(-0.5, 0.5).mean(axis=1).fillna(0)).cumprod()}
    jobs = [(t, pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}), mk[k], bench[mk[k]])
            for t, k in kinds.items() if t in close]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        out = [r for r in ex.map(features, jobs, chunksize=8) if r]
    panel, _, _ = finish_panel(out, bench)
    latest = panel.loc[panel.groupby("ticker")["date"].idxmax()]
    p = saved["model"].predict_proba(latest[saved["X"]])[:, 1]
    return dict(zip(latest.ticker, p))


def crypto_extras(df, raw, kinds):
    """Crypto rows: the ML mood (crypto lab S4, passed: take signals only when positive) and each coin's adaptive
    AlgoAlpha setting for this year (crypto lab S3, passed). Information only, tracked forward from Nov 2026."""
    df["ml_mood"], df["ml_chance"], df["adaptive"] = "", None, ""
    try:
        from run_crypto_lab import score_latest
        from run_signal_lab import supertrend_set
        cr = [t for t, k in kinds.items() if k == "Crypto" and t in raw["Close"]]
        px = {t: pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}) for t in cr}
        sc = score_latest(px)
        st_path = ROOT / "reports" / "crypto_lab" / "settings.csv"
        settings = pd.read_csv(st_path).set_index("symbol") if st_path.exists() else pd.DataFrame()
        for i in df.index[df.kind == "Crypto"]:
            t = df.at[i, "symbol"]
            if t in sc:
                p, base = sc[t]
                df.at[i, "ml_chance"] = round(p, 3)
                df.at[i, "ml_mood"] = "Positive" if p > base else "Negative"
            if t in settings.index:
                fac, atr = float(settings.at[t, "factor"]), int(settings.at[t, "atr"])
                d = px[t].dropna(subset=["Open", "High", "Low", "Close"])
                st, _ = supertrend_set(*(d[k].to_numpy(float) for k in ("High", "Low", "Close")), atr, fac)
                df.at[i, "adaptive"] = f"{fac:g} / {atr}: {'green' if st[-1] == 1 else 'red'}"
        print(f"Crypto ML mood: {(df.ml_mood == 'Positive').sum()} positive, {(df.ml_mood == 'Negative').sum()} negative")
    except Exception as e:                                                # never block the daily scan
        print(f"warning: crypto ML mood unavailable ({e})")


# Crypto lab results (reports/crypto_lab/REPORT.md, pre-registered, passed): Sharpe 2019-2020 / 2021-today
CRYPTO_ML_FILTER = {"with": (1.57, 1.27), "without": (0.99, 1.13)}

def write_history(history, shown, names):
    """reports/signal_board/signal_history.csv: the signal calendar's rows (newest first)."""
    if not history:
        return
    h = pd.DataFrame(history)
    h["name"] = [names.get(s, s) for s in h.symbol]
    h["symbol"] = h.symbol.map(shown).fillna(h.symbol)
    cols = ["date", "symbol", "name", "kind", "strategy", "signal", "why", "close", "stop", "take_profit",
            "status", "result", "exit_date", "hit_take_profit", "days"]
    h = h[cols].sort_values(["date", "signal", "symbol"], ascending=[False, True, True])
    h.to_csv(OUT / "signal_history.csv", index=False)
    print(f"Signal history: {len(h):,} signals over {h.date.nunique()} days")


RULE_WHY = {
    "US stock": "{s} closed back above its 200-day average: the buy signal of the 200-day trend rule, the rule that "
                "tested best for US stocks (it rides long uptrends and steps aside in downtrends).",
    "Halal ETF": "{s} closed back above its 200-day average: the buy signal of the 200-day trend rule.",
    "EGX stock": "{s} broke above its 20-day high while its 50-day average is above its 200-day and the trend is "
                 "strong (ADX above 20): the buy signal of the swing trend stack, the rule that tested best on EGX.",
    "Crypto": "{s} gave your AlgoAlpha green arrow with the squeeze momentum bright green, and the weekly trend is "
              "green: the crypto rule that tested best.",
}
USER_WHY = ("{s} is already in an uptrend and just gave your AlgoAlpha green arrow with the squeeze momentum bright "
            "green, with the weekly trend green: a fresh push inside an existing trend.")


def explain_buys(df, raw, kinds):
    """For every BUY / STRONG BUY: why buy, a 5-point strength meter, how past signals like it did, and the plan."""
    for c in ("strength", "strength_label", "why_buy", "checks", "evidence", "plan"):
        df[c] = None if c == "strength" else ""
    path = ROOT / "reports" / "signal_board" / "signal_evidence.csv"
    ev = pd.read_csv(path) if path.exists() else pd.DataFrame()
    close = raw["Close"]
    spy = close["SPY"].dropna()
    egx_cols = [t for t, k in kinds.items() if k == "EGX stock" and t in close]
    egx = (1 + close[egx_cols].pct_change(fill_method=None).clip(-0.5, 0.5).mean(axis=1).fillna(0)).cumprod()
    up200 = lambda x: bool(x.iloc[-1] > x.rolling(200).mean().iloc[-1])
    backdrop = {"US": up200(spy), "EGX": up200(egx)}
    market_of = {"US stock": "US", "Halal ETF": "US", "EGX stock": "EGX", "Crypto": "Crypto"}
    for i in df.index[df.verdict.isin(["BUY", "STRONG BUY"])]:
        r = df.loc[i]
        mk = market_of[r.kind]
        sym = r.symbol
        if mk == "Crypto":
            b_ok = r.get("liquidity") == "Rising"
            b_txt = ("Fed liquidity is rising" if b_ok else "Fed liquidity is falling" if r.get("liquidity") else
                     "Fed liquidity unknown")
        else:
            b_ok = backdrop[mk]
            b_txt = ("The " + ("US market (S&P 500)" if mk == "US" else "Egyptian market") +
                     (" is above its 200-day average" if b_ok else " is below its 200-day average"))
        checks = [(bool(r.chk_weekly), "Weekly trend green" if r.chk_weekly else "Weekly trend red"),
                  (bool(r.chk_trend), "Daily AlgoAlpha trend green" if r.chk_trend else "Daily AlgoAlpha trend red"),
                  (bool(r.chk_squeeze), "Squeeze momentum bright green" if r.chk_squeeze else "Squeeze momentum not bright green"),
                  (bool(r.chk_lor), "Lorentzian green arrow in the last 5 days" if r.chk_lor else "No Lorentzian green arrow in the last 5 days"),
                  (bool(b_ok), b_txt)]
        n = sum(ok for ok, _ in checks)
        label = "Strong" if n >= 4 else "Medium" if n == 3 else "Weak"
        rule_key = r.signal_rule or "Dashboard rule"
        why = (USER_WHY if rule_key == "Your rule" else RULE_WHY[r.kind]).format(s=sym)
        e = ev[(ev.market == mk) & (ev.rule == rule_key) & (ev.strength == label)] if len(ev) else ev
        if len(e):
            e = e.iloc[0]
            evid = (f"Since 2016, {int(e.trades):,} past {mk} signals like this ({label.lower()}) won "
                    f"{e.win_rate:.0%} of the time, average trade {e.avg_trade:+.1%}.")
            if int(e.trades) < 30:
                evid += " Few past cases, so treat this number with caution."
            if mk == "US":
                evid += " In US tests the strength meter did not change the win rate, so treat every US buy the same and follow the stop."
            else:
                evid += " In tests, stronger signals won more often in both 2016-2020 and 2021-today."
        if mk == "Crypto" and r.get("ml_mood"):
            w, wo = CRYPTO_ML_FILTER["with"], CRYPTO_ML_FILTER["without"]
            evid += (f" Crypto ML mood is {r.ml_mood.lower()}: in the crypto test, taking signals only when the mood was "
                     f"positive gave a steadier result (Sharpe {w[0]:.2f} vs {wo[0]:.2f} in 2019-2020, {w[1]:.2f} vs "
                     f"{wo[1]:.2f} in 2021-today)" + (", so this one has the model's support." if r.ml_mood == "Positive"
                                                      else ", so consider skipping this one or using a small position."))
        else:
            evid = ""
        risk = 1 - r.stop / r.close if r.close and r.stop == r.stop else np.nan   # share of price at risk
        plan = f"Buy at the next session. Sell if it closes below {r.stop:,.2f}"
        plan += f" ({risk:.0%} below today's price)." if np.isfinite(risk) else "."
        if r.take_profit == r.take_profit and r.take_profit:
            plan += (f" At {r.take_profit:,.2f} (+{r.take_profit / r.close - 1:.0%}) sell half and move the stop to "
                     "your entry price.")
        if np.isfinite(risk) and risk > 0.12:
            plan += (f" The stop is far away ({risk:.0%}): use a smaller position so that being stopped out costs no "
                     "more than 1-2% of your account.")
        df.loc[i, ["strength", "strength_label", "why_buy", "evidence", "plan"]] = [n, label, why, evid, plan]
        df.loc[i, "checks"] = ";".join(("yes|" if ok else "no|") + t for ok, t in checks)
    df.drop(columns=["chk_weekly", "chk_trend", "chk_squeeze", "chk_lor", "signal_rule"], inplace=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scr = pd.read_csv(ROOT / "reports" / "broad_screen.csv")
    us = scr[scr.compliant & (scr.marketCap >= 10e9)]
    us = us[~us.ticker.isin(ALCOHOL_HEAVY)]
    # All US large caps ($10B+) and small caps ($1-2B) from the screener (lab/expand.py), when screened.
    # Defense contractors are not screened out by name outside the original list, so drop the whole industry.
    def extra(name, taken):
        path = UNIVERSE / f"{name}_screen.csv"
        if not path.exists():
            return pd.DataFrame(columns=["ticker", "name", "sector", "industry"])
        x = pd.read_csv(path)
        return x[x.compliant & ~x.ticker.isin(taken) & (x.industry != "Aerospace & Defense") & ~x.ticker.isin(ALCOHOL_HEAVY)]
    large = extra("largecap", set(us.ticker))
    us = pd.concat([us, large], ignore_index=True)
    mid = pd.read_csv(UNIVERSE / "midcap_screen.csv")
    mid = mid[mid.compliant & ~mid.ticker.isin(us.ticker) & (mid.industry != "Aerospace & Defense")
              & ~mid.ticker.isin(ALCOHOL_HEAVY)]
    small = extra("smallcap", set(us.ticker) | set(mid.ticker))
    crypto = {c["symbol"]: c["name"] for c in json.loads((UNIVERSE / "crypto_list.json").read_text())}
    egx = [t + ".CA" for t in halal_egx()]
    names = (dict(zip(us.ticker, us.name)) | dict(zip(mid.ticker, mid.name)) | dict(zip(small.ticker, small.name)) | ETFS | crypto
             | {t: t[:-3] + " (EGX)" for t in egx})
    sectors = dict(zip(us.ticker, us.sector)) | dict(zip(mid.ticker, mid.sector)) | dict(zip(small.ticker, small.sector))
    size = {t: "Large cap" for t in us.ticker} | {t: "Mid cap" for t in mid.ticker} | {t: "Small cap" for t in small.ticker}
    kinds = ({t: "US stock" for t in list(us.ticker) + list(mid.ticker) + list(small.ticker)} | {t: "Halal ETF" for t in ETFS}
             | {t: "Crypto" for t in crypto} | {t: "EGX stock" for t in egx})
    # Full AAOIFI check from financial statements (lab/shariah.py): keep only stocks that pass.
    sh_path = UNIVERSE / "shariah_check.csv"
    shariah = {}
    funds_path = UNIVERSE / "shariah_funds.csv"      # certified Shariah fund holdings (lab/shariah_funds.py)
    funds = (pd.read_csv(funds_path).set_index("ticker")["funds"].to_dict() if funds_path.exists() else {})
    if sh_path.exists():
        sh = pd.read_csv(sh_path).set_index("ticker")
        for t, k in list(kinds.items()):
            if k in ("US stock", "EGX stock"):
                if t not in sh.index or sh.loc[t, "status"] != "pass":
                    kinds.pop(t)
                    continue
                row = sh.loc[t]
                ratios = (row.reason if row.reason != "pass" else
                          f"debt {row.debt_ratio:.0%}, cash {row.cash_ratio:.0%}, interest income {row.income_ratio:.1%}")
                shariah[t] = (f"Confirmed - held by {funds[t].replace(',', ', ')}; {ratios}" if t in funds
                              else f"Screened - {ratios}")
        print(f"Shariah check: {sum(1 for k in kinds.values() if k in ('US stock', 'EGX stock'))} stocks pass")
    for t, k in kinds.items():
        shariah.setdefault(t, {"Halal ETF": "Confirmed - certified Shariah fund", "Crypto": "debated among scholars"}.get(
            k, "business screen only - check with Zoya"))
    raw = yf.download(list(kinds) + ["SPY"], period="12y", auto_adjust=True, progress=False, threads=True,
                      group_by="column")
    jobs = [(t, pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}), k)
            for t, k in kinds.items() if t in raw["Close"]]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        rows = [r for r in ex.map(analyse, jobs) if r]
    history = [dict(h, symbol=r["symbol"], kind=r["kind"], strategy=r["strategy"]) for r in rows for h in r.pop("_history")]
    df = pd.DataFrame(rows)
    ml = ml_scores(raw, kinds)
    df.insert(df.columns.get_loc("score") + 1, "ml_score", [round(float(ml[t]), 3) if t in ml else None for t in df.symbol])
    grp = df.kind.replace({"Halal ETF": "US stock"})
    df.insert(df.columns.get_loc("ml_score") + 1, "ml_rank",
              (df.groupby(grp)["ml_score"].rank(pct=True) * 100).round(0))
    df.insert(1, "name", [names.get(s, s) for s in df.symbol])
    df.insert(3, "sector", [sectors.get(s, {"Crypto": "Crypto", "Halal ETF": "ETF", "EGX stock": "Egypt"}.get(k, ""))
                            for s, k in zip(df.symbol, df.kind)])
    df.insert(4, "size", [size.get(s, "") for s in df.symbol])
    df.insert(5, "shariah", [shariah.get(s, "") for s in df.symbol])
    crypto_extras(df, raw, kinds)
    # Display symbols without Yahoo suffixes, keeping them unique
    short = df.symbol.str.replace(r"\.CA$", "", regex=True).str.replace(r"\d*-USD$", "", regex=True)
    dup = short.duplicated(keep=False)
    shown = dict(zip(df.symbol, np.where(dup, df.symbol, short)))
    df["symbol"] = np.where(dup, df.symbol, short)
    write_history(history, shown, names)
    # Liquidity tag for crypto (forward-tracked, information only - see reports/liquidity2/REPORT.md)
    df["liquidity"] = ""
    try:
        from lab.liquidity import export_csv
        liq = export_csv()
        fed = liq.fed_rising.replace("", np.nan).dropna().iloc[-1]
        word = "Rising" if fed == "yes" else "Falling"
        crypto_rows = df.kind == "Crypto"
        df.loc[crypto_rows, "liquidity"] = word
        ev = pd.read_csv(ROOT / "reports" / "signal_board" / "liquidity_evidence.csv")
        ev = ev[ev.period == "2021-today"].set_index("liquidity").win_rate
        if word == "Falling":
            note = (f" Fed liquidity is falling: in tests crypto signals won {ev['Falling']:.0%} of the time then, vs "
                    f"{ev['Rising']:.0%} when rising - consider a smaller position.")
            buys = crypto_rows & df.verdict.isin(["BUY", "STRONG BUY"])
            df.loc[buys, "reason"] = df.loc[buys, "reason"] + note
        print(f"Liquidity: Fed {word.lower()}, stablecoins {'rising' if liq.stable_rising.iloc[-1] == 'yes' else 'falling'}, "
              f"Bitcoin on-chain {'rising' if liq.chain_rising.iloc[-1] == 'yes' else 'falling'}")
    except Exception as e:                                                # never block the daily scan
        print(f"warning: liquidity data unavailable ({e})")
    explain_buys(df, raw, kinds)
    order = {"STRONG BUY": 0, "BUY": 1, "SELL": 2, "HOLD": 3, "AVOID": 4}
    df = df.sort_values(["verdict", "score"], key=lambda s: s.map(order) if s.name == "verdict" else -s)
    df.to_csv(OUT / "signals.csv", index=False)
    print(df.verdict.value_counts().to_string())
    print(df.head(15)[["symbol", "kind", "strategy", "verdict", "ml_rank", "close", "stop", "take_profit", "weekly"]].to_string())


if __name__ == "__main__":
    main()
