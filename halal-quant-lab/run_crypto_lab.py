"""Crypto lab: machine learning on every coin-day, per-coin adaptive indicators and ML-filtered signals.

    python run_crypto_lab.py           # walk-forward test, writes reports/crypto_lab/REPORT.md
    python run_crypto_lab.py --final   # saves reports/crypto_lab/model.pkl + settings.csv for the daily board

Universe: the 34 halal-filtered coins in reports/universe/crypto_list.json (today's list, so coins that died are
missing - survivorship bias flatters every strategy, buy & hold included). Daily bars from Yahoo.
Decided at the close, traded at the next close, 0.10% cost per side, no leverage, cash earns nothing.

Features per coin-day (~45, all known at that close): returns 1-90 days, volatility, RSI 2/14, volume vs its
average and its z-score, OBV slope, Chaikin money flow, distance from 20/50/200-day averages (ATR units),
AlgoAlpha SuperTrend state and distance, weekly SuperTrend, squeeze momentum and slope, ADX, place in the 52-week
range, drawdown, strength vs Bitcoin (30/90 days), cross-coin ranks, Bitcoin's own trend and volatility,
Bitcoin network activity (value moved 30 vs 90 days, active addresses and hash-rate growth), stablecoin supply
growth (30 days; 0 before 2020, when the data is unreliable) and Fed net liquidity vs its 13-week average.
Label: the coin is higher 10 trading days after the next close. Gradient boosting, retrained every January on
rows whose 10-day outcome was known 15 days before that January (embargo); walk-forward from 2019.

Strategies (all fixed before the first run):
  BASE  current crypto rule: AlgoAlpha green arrow + bright squeeze + weekly SuperTrend green, exit red arrow
  S1    ML timing: each Friday hold every coin whose predicted chance of being up is above the training base rate
  S2    ML rotation: each Friday hold the 5 coins with the highest predicted chance, only those above the base rate
  S3    per-coin adaptive: BASE with each coin's SuperTrend factor (2-4) and ATR length (7/10/14) re-chosen every
        January as the best Sharpe over the previous 3 years (default 3 / 10 until 3 years of history exist)
  S4    BASE entries taken only when the model's chance at the signal close is above the base rate
  Positions: BASE / S1 / S3 / S4 equal weight across open positions, max 10% each; S2 5 slots of 20%.
PRE-REGISTERED PASS RULE: a strategy beats BASE if, in BOTH 2019-2020 and 2021-today, its Sharpe is higher and
its maximum drawdown is no more than 5 points deeper. S3 is also compared with BASE (the default settings).
"""
import json
import os
import pickle
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from lab import tv
from lab.liquidity import series as liq_series
from lab.metrics import stats
from lab.universe import DATA
from run_signal_lab import supertrend_set

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "crypto_lab"
COST, H, EMBARGO = 0.001, 10, 15
GRID = [(f, a) for f in (2.0, 2.5, 3.0, 3.5, 4.0) for a in (7, 10, 14)]
PERIODS = {"2019-2020": ("2019-01-01", "2020-12-31"), "2021-today": ("2021-01-01", "2100-01-01")}


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def weekly_st(df):
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    if len(wk) < 120:
        return np.zeros(len(df))
    w = tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0]
    return pd.Series(w, index=wk.index).shift(1).reindex(df.index, method="ffill").fillna(0).to_numpy()


def rule_position(st, bright, weekly):
    """BASE rule: enter on green arrow + bright squeeze with weekly green; exit when SuperTrend turns red."""
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    entry = flip & bright & (weekly > 0.5)
    pos = np.zeros(len(st))
    for t in range(1, len(st)):
        pos[t] = (1.0 if st[t] == 1 else 0.0) if pos[t - 1] else (1.0 if entry[t] else 0.0)
    return pos, entry


def clean(df):
    """Drop bad prints: a 10x jump or crash in one day is a data error (e.g. a coin's first Yahoo quote).
    Bad prints in the first 30 bars trim the start; later ones drop that bar."""
    for _ in range(3):
        jump = (df.Close / df.Close.shift(1)).apply(lambda x: x > 10 or x < 0.1)
        if not jump.any():
            break
        first = int(np.argmax(jump.to_numpy()))
        df = df.iloc[first:] if first < 30 else df[~jump]
    return df


def coin(args):
    tk, df = args[0], args[1]
    with_grid = args[2] if len(args) > 2 else True
    df = clean(df.dropna(subset=["Open", "High", "Low", "Close"]))
    if len(df) < 400:
        return None
    idx = df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df.Volume.fillna(0).to_numpy(float)
    cs, vs = pd.Series(c, index=idx), pd.Series(v, index=idx)
    r1 = cs.pct_change()
    a14 = tv.atr(h, l, c, 14)
    st, line = supertrend_set(h, l, c, 10, 3.0)
    _, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    weekly = weekly_st(df)
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdi, mdi = tv.rma(pdm, 14), tv.rma(mdm, 14)
    rng = np.where(h > l, h - l, np.nan)
    mfm = ((c - l) - (h - c)) / rng
    obv = (np.sign(r1.fillna(0)) * vs).cumsum()
    f = pd.DataFrame({
        **{f"ret{n}": cs / cs.shift(n) - 1 for n in (1, 3, 7, 14, 30, 60, 90)},
        "vol7": r1.rolling(7).std(), "vol30": r1.rolling(30).std(),
        "rsi2": tv.rsi(c, 2), "rsi14": tv.rsi(c, 14),
        "vol_ratio": vs / vs.rolling(30).mean(), "vol_z": (vs - vs.rolling(90).mean()) / vs.rolling(90).std(),
        "obv_slope": (obv - obv.shift(14)) / vs.rolling(14).sum(),
        "cmf20": pd.Series(np.nan_to_num(mfm) * v, index=idx).rolling(20).sum() / vs.rolling(20).sum(),
        **{f"dist{n}": (cs - cs.rolling(n).mean()) / a14 for n in (20, 50, 200)},
        "st_up": st, "st_dist": (c - line) / a14, "weekly_up": weekly,
        "sq_mom": m / a14, "sq_slope": np.r_[np.nan, np.diff(m)] / a14,
        "adx": tv.rma(100 * np.abs(pdi - mdi) / (pdi + mdi), 14), "di_spread": (pdi - mdi) / (pdi + mdi),
        "range52": (cs - pd.Series(l, index=idx).rolling(365, min_periods=120).min()) /
                   (pd.Series(h, index=idx).rolling(365, min_periods=120).max() - pd.Series(l, index=idx).rolling(365, min_periods=120).min()),
        "dd90": cs / cs.rolling(90).max() - 1, "atr_pct": a14 / c,
    }, index=idx).replace([np.inf, -np.inf], np.nan)
    f["fwd"] = cs.shift(-1 - H) / cs.shift(-1) - 1
    base_pos, base_entry = rule_position(st, bright, weekly)
    # adaptive settings: rule position for every grid setting
    grid_pos = {}
    for fac, al in (GRID if with_grid else []):
        st2, _ = supertrend_set(h, l, c, al, fac)
        grid_pos[(fac, al)] = rule_position(st2, bright, weekly)[0]
    return tk, f, cs, pd.Series(base_pos, index=idx), pd.Series(base_entry, index=idx), \
        {k: pd.Series(p, index=idx) for k, p in grid_pos.items()}


def bitcoin_chain():
    out = {}
    for name in ("estimated-transaction-volume-usd", "n-unique-addresses", "hash-rate"):
        js = requests.get(f"https://api.blockchain.info/charts/{name}?timespan=all&format=json&sampled=false", timeout=120).json()
        s = pd.Series({pd.to_datetime(p["x"], unit="s"): p["y"] for p in js["values"]}, dtype=float).sort_index()
        s.index = s.index + pd.Timedelta(days=1)
        out[name] = s
    return out


def portfolio(P, closes, cap=0.10, slots=None):
    P = P.reindex(closes.index).fillna(0)
    Pe = P.shift(1).fillna(0)                                    # decided at a close, held from the next close
    if slots:
        W = Pe / slots
    else:
        k = (Pe > 0).sum(axis=1).replace(0, np.nan)
        W = Pe.mul(np.minimum(1 / k, cap), axis=0).fillna(0)
    R = closes.pct_change(fill_method=None).fillna(0)
    return (W.shift(1) * R).sum(axis=1) - COST * W.diff().abs().sum(axis=1).fillna(0)


def friday_hold(pred, col, rule):
    """Positions decided each Friday from predictions, held until the next Friday."""
    fr = pred[pred.date.dt.weekday == 4]
    rows = []
    for d, g in fr.groupby("date"):
        rows.append((d, rule(g)))
    return rows


def to_matrix(decisions, index, cols):
    P = pd.DataFrame(0.0, index=index, columns=cols)
    for i, (d, held) in enumerate(decisions):
        end = decisions[i + 1][0] if i + 1 < len(decisions) else index[-1] + pd.Timedelta(days=1)
        if held:
            P.loc[(P.index >= d) & (P.index < end), held] = 1.0
    return P


def best_settings(gp, hist):
    """Best (factor, ATR) by Sharpe of the rule over `hist` (daily returns); default 3 / 10 if < 3 years of data."""
    if hist.notna().sum() < 3 * 300:
        return (3.0, 10)
    sc = {}
    for k, p in gp.items():
        r = (p.shift(1).reindex(hist.index).fillna(0) * hist).fillna(0)
        sc[k] = r.mean() / r.std() if r.std() > 0 else -9
    return max(sc, key=sc.get)


def final(res, closes, panel, X):
    """Save the model trained on every labelled coin-day and this year's per-coin settings (for the daily board)."""
    lab = panel[panel.y.notna()]
    mdl = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=300, min_samples_leaf=200,
                                         l2_regularization=2.0, random_state=0).fit(lab[X], lab.y)
    yr = pd.Timestamp.today().year
    rets = closes.pct_change(fill_method=None)
    a, b = pd.Timestamp(f"{yr - 3}-01-01"), pd.Timestamp(f"{yr}-01-01")
    settings = [(tk, *best_settings(gp, rets[tk].loc[a:b - pd.Timedelta(days=1)])) for tk, f, cs, bp, be, gp in res]
    pd.DataFrame(settings, columns=["symbol", "factor", "atr"]).to_csv(OUT / "settings.csv", index=False)
    with open(OUT / "model.pkl", "wb") as fh:
        pickle.dump({"model": mdl, "X": X, "base": float(lab.y.mean()), "trained_to": str(lab.date.max().date()),
                     "settings_year": yr}, fh)
    print(f"saved crypto model ({len(lab):,} coin-days, base rate {lab.y.mean():.1%}) and {len(settings)} coin settings for {yr}")


def score_latest(prices):
    """{symbol: (chance up in 10 days, base rate)} for the latest day, from the saved model.
    `prices` maps a Yahoo crypto symbol to its OHLCV DataFrame."""
    path = OUT / "model.pkl"
    if not path.exists():
        return {}
    saved = pickle.loads(path.read_bytes())
    _, _, panel, _ = build([(t, df, False) for t, df in prices.items()])
    latest = panel.loc[panel.groupby("ticker")["date"].idxmax()]
    p = saved["model"].predict_proba(latest[saved["X"]])[:, 1]
    return {t: (float(q), saved["base"]) for t, q in zip(latest.ticker, p)}


def build(jobs):
    """Features for every coin-day: coin features + Bitcoin / network / stablecoin / Fed market features."""
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        res = [r for r in ex.map(coin, jobs) if r]
    print(f"  features for {len(res)} coins", flush=True)
    closes = pd.DataFrame({r[0]: r[2] for r in res}).sort_index()
    btc = closes["BTC-USD"].dropna()
    chain = bitcoin_chain()
    liq = liq_series()
    days = closes.index
    al = lambda s: s.reindex(s.index.union(days)).ffill().reindex(days)
    tx = chain["estimated-transaction-volume-usd"]
    market = pd.DataFrame({
        "btc_ret7": btc / btc.shift(7) - 1, "btc_ret30": btc / btc.shift(30) - 1,
        "btc_up200": (btc > btc.rolling(200).mean()).astype(float), "btc_vol30": btc.pct_change().rolling(30).std(),
        "chain_tx": al(tx.rolling(30).mean() / tx.rolling(90).mean()),
        "chain_addr": al(chain["n-unique-addresses"].rolling(30).mean() / chain["n-unique-addresses"].rolling(90).mean()),
        "chain_hash": al(chain["hash-rate"].rolling(30).mean() / chain["hash-rate"].rolling(90).mean()),
        "stable_g30": al(liq["STABLE"][0] / liq["STABLE"][1] - 1).where(days >= "2020-01-01").fillna(0),  # 0 = unknown
        "fed_vs13w": al(liq["FED"][0] / liq["FED"][1] - 1),
    }, index=days)
    panel = []
    for tk, f, cs, *_ in res:
        g = f.join(market, how="left")
        g["rs30"] = g.ret30 - g.btc_ret30
        g["rs90"] = cs / cs.shift(90) - btc.reindex(cs.index) / btc.reindex(cs.index).shift(90)
        g["ticker"] = tk
        panel.append(g)
    panel = pd.concat(panel).reset_index().rename(columns={"index": "date", "Date": "date"})
    panel["date"] = pd.to_datetime(panel.date)
    for col in ("ret30", "ret90", "vol30", "rs90", "vol_ratio"):
        panel[col + "_rank"] = panel.groupby("date")[col].rank(pct=True)
    panel["y"] = (panel.fwd > 0).astype(float).where(panel.fwd.notna())
    panel = panel[panel.date >= "2016-01-01"].reset_index(drop=True)
    X = [c for c in panel.columns if c not in ("date", "ticker", "fwd", "y")]

    return res, closes, panel, X


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    crypto = [c["symbol"] for c in json.loads((ROOT / "reports" / "universe" / "crypto_list.json").read_text())]
    px = pd.read_pickle(DATA / "lab_prices.pkl") if (DATA / "lab_prices.pkl").exists() else None
    if px is None or any(t not in px["Close"] for t in crypto):  # fresh machine or new coins: download
        import yfinance as yf
        raw = yf.download(crypto, start="2014-01-01", auto_adjust=True, progress=False, threads=True, group_by="column")
        px = {k: raw[k] for k in ("Open", "High", "Low", "Close", "Volume")}
    jobs = [(t, pd.DataFrame({k: px[k][t] for k in ("Open", "High", "Low", "Close", "Volume")})) for t in crypto if t in px["Close"]]
    res, closes, panel, X = build(jobs)
    if "--final" in sys.argv:
        final(res, closes, panel, X)
        return
    days = closes.index

    preds, aucs = [], []
    for yr in range(2019, panel.date.dt.year.max() + 1):
        start = pd.Timestamp(f"{yr}-01-01")
        tr = panel[(panel.date < start - pd.Timedelta(days=EMBARGO + H)) & panel.y.notna()]
        te = panel[(panel.date >= start) & (panel.date < pd.Timestamp(f"{yr + 1}-01-01"))].copy()
        mdl = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=300, min_samples_leaf=200,
                                             l2_regularization=2.0, random_state=0).fit(tr[X], tr.y)
        te["p"] = mdl.predict_proba(te[X])[:, 1]
        te["base"] = tr.y.mean()
        preds.append(te)
        lab = te.dropna(subset=["y"])
        if len(lab) > 200:
            aucs.append((yr, roc_auc_score(lab.y, lab.p), len(tr), tr.y.mean()))
        print(f"  {yr}: trained on {len(tr):,} coin-days", flush=True)
    pr = pd.concat(preds)
    cols = list(closes.columns)

    # ---------------- strategies ----------------
    base_P = pd.DataFrame({r[0]: r[3] for r in res}).reindex(days).fillna(0)
    entries = pd.DataFrame({r[0]: r[4] for r in res}).reindex(days).fillna(False)
    S1 = to_matrix(friday_hold(pr, "p", lambda g: list(g[g.p > g.base].ticker)), days, cols)
    S2 = to_matrix(friday_hold(pr, "p", lambda g: list(g[g.p > g.base].nlargest(5, "p").ticker)), days, cols)
    # S3: per-coin settings re-chosen each January on the previous 3 years
    S3 = pd.DataFrame(0.0, index=days, columns=cols)
    chosen = []
    rets = closes.pct_change(fill_method=None)
    for tk, f, cs, bp, be, gp in res:
        for yr in range(2017, days.year.max() + 1):
            a, b = pd.Timestamp(f"{yr - 3}-01-01"), pd.Timestamp(f"{yr}-01-01")
            best = best_settings(gp, rets[tk].loc[a:b - pd.Timedelta(days=1)])
            chosen.append((tk, yr, *best))
            sel = (days >= b) & (days < pd.Timestamp(f"{yr + 1}-01-01"))
            S3.loc[sel, tk] = gp[best].reindex(days[sel]).fillna(0).to_numpy()
    # S4: BASE entries only where the model's chance at the signal close is above the base rate
    pmap = pr.set_index(["date", "ticker"])[["p", "base"]]
    S4 = pd.DataFrame(0.0, index=days, columns=cols)
    for tk in cols:
        e = entries[tk].to_numpy()
        st_in = base_P[tk].to_numpy()
        pos = np.zeros(len(days))
        for t in range(1, len(days)):
            if pos[t - 1]:
                pos[t] = st_in[t]
            elif e[t] and (days[t], tk) in pmap.index:
                q = pmap.loc[(days[t], tk)]
                pos[t] = 1.0 if q.p > q.base else 0.0
        S4[tk] = pos
    bh = closes.notna().astype(float)

    strategies = {"BASE (current crypto rule)": (base_P, None), "S1 ML timing": (S1, None), "S2 ML rotation (top 5)": (S2, 5),
                  "S3 per-coin adaptive settings": (S3, None), "S4 BASE + ML filter": (S4, None),
                  "Buy & hold, equal weight (max 10% each)": (bh, None)}
    md = ["# Crypto lab - machine learning, adaptive indicators and ML-filtered signals\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(res)} halal-filtered coins (today's list: survivorship bias "
          f"flatters every line, buy & hold included), {len(panel):,} coin-days from 2016, {len(X)} features. Next-close "
          "execution, 0.10% per side. Rules and pass conditions fixed before the run (see run_crypto_lab.py).\n",
          "## 1. Can the model tell which coins will be up in 10 days? (out-of-sample)", "",
          "| Year | AUC (0.50 = coin flip) | Training coin-days | Share up in training |", "|---|---|---|---|"]
    md += [f"| {y} | {a:.3f} | {n:,} | {b:.0%} |" for y, a, n, b in aucs]
    lab = pr.dropna(subset=["y"])
    lab = lab.assign(q=pd.qcut(lab.p.rank(method="first"), 5, labels=False))
    g = lab.groupby("q").agg(up=("y", "mean"), fwd=("fwd", "mean"))
    md += ["", "Coin-days sorted by the model's chance, 2019-today (fifths, low -> high):", "",
           "| | Lowest | 2 | 3 | 4 | Highest |", "|---|---|---|---|---|---|",
           "| Share up after 10 days | " + " | ".join(f"{x:.0%}" for x in g.up) + " |",
           "| Average 10-day return | " + " | ".join(f"{x:+.1%}" for x in g.fwd) + " |"]
    md += ["", "## 2. Strategies", "", "| Strategy | Period | CAGR | Sharpe | Max DD | Time invested | Beats BASE? |", "|---|---|---|---|---|---|---|"]
    base_s = {}
    verdict = {}
    for name, (P, slots) in strategies.items():
        r = portfolio(P, closes, slots=slots)
        expo = P.shift(1).reindex(days).fillna(0).sum(axis=1).gt(0)
        ok = []
        for per, (a, b) in PERIODS.items():
            s = stats(r.loc[a:b], year=365)
            if name.startswith("BASE"):
                base_s[per] = s
            better = (not name.startswith("BASE")) and s["sharpe"] > base_s[per]["sharpe"] and s["max_dd"] >= base_s[per]["max_dd"] - 0.05
            ok.append(better)
            md.append(f"| {name} | {per} | {s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} | {expo.loc[a:b].mean():.0%} | "
                      f"{'' if name.startswith('BASE') else ('yes' if better else 'no')} |")
        if not name.startswith(("BASE", "Buy")):
            verdict[name] = all(ok)
    md += ["", "## 3. Verdict (pre-registered: higher Sharpe and drawdown no more than 5 points deeper, in both periods)", "",
           "| Strategy | Result |", "|---|---|"] + [f"| {k} | **{'PASS' if v else 'FAIL'}** |" for k, v in verdict.items()]
    ch = pd.DataFrame(chosen, columns=["coin", "year", "factor", "atr"])
    md += ["", "## 4. Per-coin settings chosen (S3)", "",
           f"Default 3 / 10 chosen in {((ch.factor == 3.0) & (ch.atr == 10)).mean():.0%} of coin-years. "
           f"Most common: " + ", ".join(f"{f:g}/{a} ({n})" for (f, a), n in ch.groupby(['factor', 'atr']).size().nlargest(5).items()) + "."]
    from sklearn.inspection import permutation_importance
    last = panel[panel.y.notna()]
    mdl = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=300, min_samples_leaf=200,
                                         l2_regularization=2.0, random_state=0).fit(last[X], last.y)
    smp = last.sample(n=min(15000, len(last)), random_state=0)
    imp = permutation_importance(mdl, smp[X], smp.y, n_repeats=3, random_state=0, scoring="roc_auc")
    top = sorted(zip(X, imp.importances_mean), key=lambda x: -x[1])[:12]
    md += ["", "## 5. Patterns the model leans on (permutation importance, in-sample, explanation only)", "",
           "| Feature | AUC drop when shuffled |", "|---|---|"] + [f"| {n} | {v:.4f} |" for n, v in top]
    md += ["", "## 6. Simple patterns: share of coin-days up after 10 days, by fifth of each feature (2016-today)", "",
           "| Feature | Lowest | 2 | 3 | 4 | Highest |", "|---|---|---|---|---|---|"]
    for col in [n for n, _ in top[:8]]:
        x = last[[col, "y"]].dropna()
        if x[col].nunique() < 5:
            continue
        q = x.groupby(pd.qcut(x[col], 5, duplicates="drop"), observed=True).y.mean()
        md.append(f"| {col} | " + " | ".join(f"{v:.0%}" for v in q) + " |")
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
