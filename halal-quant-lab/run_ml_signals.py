"""ML signal filter: learn from every past buy signal which setups tend to win, and keep only the good ones.

    python run_ml_signals.py            # walk-forward test + report (reports/ml_signals/REPORT.md)
    python run_ml_signals.py --final    # train on every closed trade and save reports/ml_signals/model.pkl

Candidates (decided at the close, bought at the next close, costs per side US 0.05% / EGX 0.25% / crypto 0.10%):
  "Dashboard rule"  US: close crosses above the 200-day SMA (exit: close below it)
                    EGX: swing stack entry (EMA50 > EMA200, ADX > 20, close > 20-day high;
                         exit 3 x ATR trail from the highest close or close < EMA50)
                    Crypto: user's arrow + bright squeeze with the weekly SuperTrend green (exit red arrow)
  "Your rule"       AlgoAlpha green arrow + bright green squeeze, exit red arrow (all markets)
Every trade is managed the way the dashboard says: sell half at +2 ATR, then stop the rest at the entry
price; otherwise the rule's exit. Label = the trade made money after costs.

Features (all known at the signal close): ~50 numbers on trend, momentum, volatility, volume, candle
shape, market mood and the shape of the last 30 days (10 price points scaled by ATR = the "pattern").
Models: gradient boosting (GBM), a pattern-twin model (k nearest neighbours: how often the 100 most
similar past setups won) and their average (ENSEMBLE - the one judged, chosen before the test).

Walk-forward: for every year from 2019 the models are trained only on trades that had already CLOSED
before 1 January of that year, then predict that year. The keep/skip cut-off is the median of
out-of-fold predictions inside the training data (no peeking at the test year).

PRE-REGISTERED PASS RULE (written before the first run): on 2021-today, for each market x rule group
(6 groups), the signals the ENSEMBLE keeps must have (a) a win rate at least 5 points higher than all
signals, (b) a profit factor not lower and (c) a portfolio Sharpe not lower. The model passes if
(a)-(c) all hold in at least 4 of the 6 groups.
"""
import os
import pickle
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

from lab import tv
from lab.metrics import stats
from run_signal_lab import MIN_VALUE, load, supertrend_set

warnings.filterwarnings("ignore", category=RuntimeWarning)
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "ml_signals"
COST = {"US": 0.0005, "EGX": 0.0025, "Crypto": 0.001}
MARKETS = ("US", "EGX", "Crypto")
SOURCES = ("Dashboard rule", "Your rule")
FIRST_TEST_YEAR, TEST_FROM = 2019, pd.Timestamp("2021-01-01")
PATH = [f"path{k}" for k in range(1, 11)]                          # price 3, 6, ... 30 days ago (ATR units)
PATTERN = PATH + ["vol_contract", "range20", "close_loc", "vol_ratio", "atr_pct"]


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def bar_features(df, bench):
    """One row of features per bar, every value known at that bar's close."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df["Volume"].fillna(0).to_numpy(float)
    T = len(c)
    cs, vs = pd.Series(c), pd.Series(v)
    r1 = cs.pct_change()
    a14 = tv.atr(h, l, c, 14)
    st, line = supertrend_set(h, l, c, 10, 3.0)
    sq_on, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    lpos, pred = tv.lorentzian(o, h, l, c)
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdi, mdi = tv.rma(pdm, 14), tv.rma(mdm, 14)
    adx = tv.rma(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
    sma50, sma200 = cs.rolling(50).mean(), cs.rolling(200).mean()
    hi252 = pd.Series(h).rolling(252, min_periods=120).max()
    days_hi = pd.Series(h).rolling(252, min_periods=120).apply(lambda x: len(x) - 1 - np.argmax(x), raw=True)
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    weekly = (pd.Series(tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0],
                        index=wk.index).shift(1).reindex(df.index, method="ffill").fillna(0).to_numpy()
              if len(wk) > 120 else np.zeros(T))
    rng = np.where(h > l, h - l, np.nan)
    obv = (np.sign(r1.fillna(0)) * vs).cumsum()
    b = pd.Series(bench.reindex(df.index).ffill().to_numpy(float))
    br = b.pct_change()
    f = pd.DataFrame({
        "ret5": cs / cs.shift(5) - 1, "ret20": cs / cs.shift(20) - 1, "ret60": cs / cs.shift(60) - 1,
        "ret120": cs / cs.shift(120) - 1, "mom12_1": cs.shift(21) / cs.shift(252) - 1,
        "rsi14": tv.rsi(c, 14), "rsi2": tv.rsi(c, 2), "adx": adx, "di_spread": (pdi - mdi) / (pdi + mdi),
        "dist50": (cs - sma50) / a14, "dist200": (cs - sma200) / a14, "sma200_slope": sma200 / sma200.shift(20) - 1,
        "ema_stack": (_ema(c, 50) > _ema(c, 200)).astype(float), "high52": cs / hi252, "days_since_high": days_hi,
        "low52": cs / pd.Series(l).rolling(252, min_periods=120).min(),
        "st_up": st, "st_dist": (c - line) / a14, "weekly_up": weekly,
        "sq_mom": m / a14, "sq_slope": np.r_[np.nan, np.diff(m)] / a14,
        "sqz_days": pd.Series(sq_on.astype(float)).rolling(20).sum(), "lor_pred": pred,
        "lor_arrow5": pd.Series(larrow.astype(float)).rolling(6, min_periods=1).max(),
        "atr_pct": a14 / c, "vol20": r1.rolling(20).std() * np.sqrt(252), "vol60": r1.rolling(60).std() * np.sqrt(252),
        "vol_contract": pd.Series(tv.atr(h, l, c, 5)) / pd.Series(tv.atr(h, l, c, 50)),
        "range20": (pd.Series(h).rolling(20).max() - pd.Series(l).rolling(20).min()) / a14,
        "vol_ratio": vs / vs.rolling(20).mean().shift(1), "vol_trend": vs.rolling(5).mean() / vs.rolling(50).mean(),
        "up_vol_share": (vs * (r1 > 0)).rolling(20).sum() / vs.rolling(20).sum(),
        "obv_slope": (obv - obv.shift(20)) / vs.rolling(20).sum(),
        "body": (c - o) / rng, "close_loc": (c - l) / rng, "upper_wick": (h - np.maximum(o, c)) / rng,
        "gap": o / cs.shift(1) - 1, "up_days10": (r1 > 0).astype(float).rolling(10).sum(),
        "dd20": cs / cs.rolling(20).max() - 1,
        "mkt_ret20": b / b.shift(20) - 1, "mkt_up200": (b > b.rolling(200).mean()).astype(float),
        "mkt_vol20": br.rolling(20).std() * np.sqrt(252), "rs60": (cs / cs.shift(60)) - (b / b.shift(60)),
    })
    for k in range(1, 11):
        f[f"path{k}"] = (cs.shift(3 * k) / cs - 1) / (a14 / c)
    f.index = df.index
    f = f.replace([np.inf, -np.inf], np.nan)
    return f, dict(o=o, h=h, l=l, c=c, v=v, st=st, a14=a14, m=m, weekly=weekly,
                   value=(cs * vs).rolling(20).median().to_numpy())


def rule_positions(market, d):
    """Entry bars and exit-decision function for the dashboard rule and the user's rule."""
    c, h, l, st, a14 = d["c"], d["h"], d["l"], d["st"], d["a14"]
    T = len(c)
    m = d["m"]
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    user = flip & bright
    trades = {"Your rule": [], "Dashboard rule": []}
    for t in np.where(user)[0]:                                      # exit: first red close after entry
        trades["Your rule"].append((t, "red", None))
    if market == "Crypto":
        trades["Dashboard rule"] = [x for x in trades["Your rule"] if d["weekly"][x[0]] > 0.5]
    elif market == "US":
        sma = pd.Series(c).rolling(200).mean().to_numpy()
        above = np.nan_to_num(c > sma).astype(bool)
        for t in np.where(above & ~np.r_[False, above[:-1]])[0]:
            trades["Dashboard rule"].append((t, "sma", sma))
    else:
        e50, e200 = _ema(c, 50), _ema(c, 200)
        up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
        pdm = np.where((up > dn) & (up > 0), up, 0.0)
        mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
        adx = tv.rma(100 * np.abs(tv.rma(pdm, 14) - tv.rma(mdm, 14)) / (tv.rma(pdm, 14) + tv.rma(mdm, 14)), 14)
        don = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        pos = False
        hi = 0.0
        for t in range(1, T):
            if pos:
                hi = max(hi, c[t])
                if c[t] < hi - 3 * a14[t] or c[t] < e50[t]:
                    pos = False
            elif e50[t] > e200[t] and adx[t] > 20 and c[t] > don[t]:
                pos, hi = True, c[t]
                trades["Dashboard rule"].append((t, "stack", (e50,)))
    return trades


def manage(c, st, a14, t, kind, extra):
    """Simulate one trade: half off at +2 ATR then breakeven stop, else the rule's exit.
    Returns (net-of-cost-free gross return, legs [(fraction, exit decision bar)], exit bar) or None."""
    T = len(c)
    if t + 1 >= T or not np.isfinite(a14[t]):
        return None
    e = c[t + 1]
    a0 = a14[t]
    half = False
    legs = []
    hi = c[t]
    for j in range(t + 2, T):
        if kind == "red":
            rule_exit = st[j] == 0
        elif kind == "sma":
            rule_exit = c[j] < extra[j]
        else:
            hi = max(hi, c[j])
            rule_exit = c[j] < hi - 3 * a14[j] or c[j] < extra[0][j]
        if not half and c[j] - e >= 2 * a0:
            legs.append((0.5, j))
            half = True
            continue
        if half and c[j] < e:
            legs.append((0.5, j))
            break
        if rule_exit:
            legs.append((1.0 - sum(f for f, _ in legs), j))
            break
    else:
        return None                                                  # still open: outcome unknown
    gross = sum(f * (c[min(j + 1, T - 1)] / e) for f, j in legs) - 1
    return gross, legs, max(j for _, j in legs) + 1


def analyse(args):
    tk, df, market, bench = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if market == "EGX":
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 400:
        return None
    feats, d = bar_features(df, bench)
    idx = df.index
    rows = []
    for src, lst in rule_positions(market, d).items():
        for t, kind, extra in lst:
            if t < 260 or not (d["value"][t] >= MIN_VALUE[market]):
                continue
            res = manage(d["c"], d["st"], d["a14"], t, kind, extra)
            open_trade = res is None and t + 1 < len(idx)
            if res is None and not open_trade:
                continue
            rec = {"ticker": tk, "market": market, "source": src, "date": idx[t], "t": int(t),
                   **feats.iloc[t].to_dict()}
            if res is None:
                rec.update(ret=np.nan, exit_date=pd.NaT, legs=None)
            else:
                g, legs, xb = res
                rec.update(ret=g - 2 * COST[market], exit_date=idx[min(xb, len(idx) - 1)], legs=legs,
                           days=xb - t)
            rows.append(rec)
    return tk, market, idx, d["c"], rows


def add_meta(ev):
    for mk in MARKETS:
        ev[f"is_{mk}"] = (ev.market == mk).astype(float)
    ev["is_dashboard"] = (ev.source == "Dashboard rule").astype(float)
    return ev


def x_cols(ev):
    skip = {"ticker", "market", "source", "date", "t", "ret", "exit_date", "legs", "days", "y"}
    return [c for c in ev.columns if c not in skip and not c.startswith("p_")]


def gbm():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=250, min_samples_leaf=60,
                                          l2_regularization=2.0, random_state=0)


class PatternTwin:
    """How often did the 100 most similar past setups (same market) win?"""
    def fit(self, X, y, market):
        self.models = {}
        for mk in MARKETS:
            s = market == mk
            if s.sum() < 200:
                continue
            sc = StandardScaler().fit(X[s])
            self.models[mk] = (sc, KNeighborsClassifier(n_neighbors=100).fit(sc.transform(X[s]), y[s]))
        self.base = float(np.mean(y))
        return self

    def predict(self, X, market):
        p = np.full(len(X), self.base)
        for mk, (sc, knn) in self.models.items():
            s = market == mk
            if s.any():
                p[s] = knn.predict_proba(sc.transform(X[s]))[:, 1]
        return p


def fit_predict(tr, te, X):
    Xtr = tr[X].astype(float)
    g = gbm().fit(Xtr, tr.y)
    pat_tr = tr[PATTERN].astype(float).fillna(0).to_numpy()
    pt = PatternTwin().fit(pat_tr, tr.y.to_numpy(), tr.market.to_numpy())
    pg = g.predict_proba(te[X].astype(float))[:, 1]
    pp = pt.predict(te[PATTERN].astype(float).fillna(0).to_numpy(), te.market.to_numpy())
    return pg, pp, (pg + pp) / 2, g, pt


def oof_cut(tr, X):
    """Median of out-of-fold ensemble predictions inside the training data (3 expanding time folds)."""
    tr = tr.sort_values("date")
    n = len(tr)
    preds = []
    for k in (1, 2, 3):
        a, b = int(n * k / 4), int(n * (k + 1) / 4)
        inner, outer = tr.iloc[:a], tr.iloc[a:b]
        inner = inner[inner.exit_date < outer.date.min()]
        if len(inner) < 300:
            continue
        preds.append(fit_predict(inner, outer, X)[2])
    return float(np.median(np.concatenate(preds))) if preds else 0.5


def portfolio(ev, idx_map, closes, market):
    pos = {}
    for tk, g in ev.groupby("ticker"):
        p = np.zeros(len(idx_map[tk]))
        for _, e in g.iterrows():
            start, frac = int(e.t), 1.0
            for f, j in e.legs:
                p[start:j] = np.maximum(p[start:j], frac)
                start, frac = j, frac - f
        pos[tk] = pd.Series(p, index=idx_map[tk])
    if not pos:
        return {"cagr": np.nan, "sharpe": np.nan, "max_dd": np.nan}
    P = pd.DataFrame(pos).reindex(closes.index).fillna(0).shift(1).fillna(0)
    R = closes[P.columns].pct_change(fill_method=None).fillna(0)
    k = (P > 0).sum(axis=1).replace(0, np.nan)
    W = P.mul(np.minimum(1 / k, 0.10), axis=0).fillna(0)
    r = (W.shift(1) * R).sum(axis=1) - COST[market] * W.diff().abs().sum(axis=1).fillna(0)
    return stats(r.loc["2021":], year=365 if market == "Crypto" else 252)


def trade_stats(d):
    r = d.ret.to_numpy()
    if len(r) == 0:
        return dict(n=0, win=np.nan, avg=np.nan, pf=np.nan)
    g, lo = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=float((r > 0).mean()), avg=float(r.mean()), pf=g / lo if lo > 0 else np.nan)


def build():
    jobs = load()
    res = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i, r in enumerate(ex.map(analyse, jobs, chunksize=2), 1):
            if r:
                res.append(r)
            if i % 50 == 0:
                print(f"  features {i}/{len(jobs)}", flush=True)
    ev = pd.DataFrame([row for r in res for row in r[4]]).sort_values("date").reset_index(drop=True)
    ev = add_meta(ev)
    ev["y"] = (ev.ret > 0).astype(float).where(ev.ret.notna())
    return ev, res


def save_final(ev, X):
    lab = ev[ev.y.notna()]
    _, _, _, g, pt = fit_predict(lab, lab.head(5), X)
    cut = oof_cut(lab, X)
    with open(OUT / "model.pkl", "wb") as f:
        pickle.dump({"gbm": g, "pattern": pt, "X": X, "pattern_cols": PATTERN, "cut": cut,
                     "trained_to": str(lab.exit_date.max().date())}, f)
    print(f"saved model: {len(lab):,} closed trades up to {lab.exit_date.max():%Y-%m-%d}, keep if p >= {cut:.3f}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev, res = build()
    X = x_cols(ev)
    if "--final" in sys.argv:
        save_final(ev, X)
        return
    parts, cuts = [], []
    for yr in range(FIRST_TEST_YEAR, ev.date.dt.year.max() + 1):
        start = pd.Timestamp(f"{yr}-01-01")
        tr = ev[(ev.exit_date < start) & ev.y.notna()]
        te = ev[(ev.date >= start) & (ev.date < pd.Timestamp(f"{yr + 1}-01-01"))].copy()
        if te.empty:
            continue
        te["p_gbm"], te["p_pat"], te["p_ens"], _, _ = fit_predict(tr, te, X)
        cut = oof_cut(tr, X)
        te["keep"] = te.p_ens >= cut
        cuts.append((yr, len(tr), cut))
        parts.append(te)
        print(f"  {yr}: trained on {len(tr):,} closed trades, cut {cut:.3f}", flush=True)
    pr = pd.concat(parts)
    test = pr[(pr.date >= TEST_FROM) & pr.y.notna()]
    closes = {mk: pd.DataFrame({r[0]: pd.Series(r[3], index=r[2]) for r in res if r[1] == mk}).sort_index()
              for mk in MARKETS}
    idx_map = {r[0]: r[2] for r in res}

    from sklearn.metrics import roc_auc_score
    md = ["# ML signal filter - does a model pick the winning signals?\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev):,} signals on {len(res)} halal assets "
          f"({int(ev.y.notna().sum()):,} closed trades). {len(X)} features. Trades managed as on the dashboard "
          "(half at +2 ATR, then stop at entry; else the rule's exit), costs included. Walk-forward: each year's "
          "model only saw trades that had closed before that year. Judged on 2021-today.\n",
          "Pre-registered pass rule: in at least 4 of 6 market x rule groups the ENSEMBLE-kept signals have a win "
          "rate +5 points or more, a profit factor not lower and a portfolio Sharpe not lower than all signals.\n",
          "## 1. Prediction quality, 2021-today (AUC: 0.50 = coin flip)", "",
          "| Market | Trades | GBM | Pattern twin | Ensemble |", "|---|---|---|---|---|"]
    for mk in MARKETS + ("All",):
        d = test if mk == "All" else test[test.market == mk]
        md.append(f"| {mk} | {len(d):,} | " + " | ".join(f"{roc_auc_score(d.y, d[p]):.3f}" for p in ("p_gbm", "p_pat", "p_ens")) + " |")
    md += ["", "Win rate by the ensemble's predicted chance (fifths of each market's test signals, low -> high):", "",
           "| Market | Lowest 20% | 20-40% | 40-60% | 60-80% | Highest 20% | Avg trade, lowest | Avg trade, highest |",
           "|---|---|---|---|---|---|---|---|"]
    for mk in MARKETS:
        d = test[test.market == mk]
        q = pd.qcut(d.p_ens.rank(method="first"), 5, labels=False)
        w = d.groupby(q).y.mean().to_numpy()
        a = d.groupby(q).ret.mean().to_numpy()
        md.append(f"| {mk} | " + " | ".join(f"{x:.0%}" for x in w) + f" | {a[0]:+.1%} | {a[-1]:+.1%} |")

    md += ["", "## 2. All signals vs signals the model keeps (2021-today)", "",
           "| Market | Rule | Signals | Trades | Win rate | Avg trade | Profit factor | Portfolio CAGR | Sharpe | Max DD | Pass? |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    passes = 0
    for mk in MARKETS:
        for src in SOURCES:
            d = test[(test.market == mk) & (test.source == src)]
            rows = {}
            for name, dd in (("All", d), ("Weekly green only", d[d.weekly_up > 0.5]), ("ML keeps", d[d.keep]),
                             ("ML skips", d[~d.keep])):
                s, p = trade_stats(dd), portfolio(dd, idx_map, closes[mk], mk)
                rows[name] = (s, p)
            sa, pa = rows["All"]
            sk, pk = rows["ML keeps"]
            ok = (sk["n"] >= 20 and sk["win"] - sa["win"] >= 0.05 and sk["pf"] >= sa["pf"]
                  and pk["sharpe"] >= pa["sharpe"])
            passes += ok
            for name, (s, p) in rows.items():
                flag = ("YES" if ok else "no") if name == "ML keeps" else ""
                md.append(f"| {mk} | {src} | {name} | {s['n']} | {s['win']:.0%} | {s['avg']:+.1%} | {s['pf']:.2f} | "
                          f"{p['cagr']:.1%} | {p['sharpe']:.2f} | {p['max_dd']:.0%} | {flag} |")
    verdict = "PASSED" if passes >= 4 else "FAILED"
    md += ["", f"**Verdict: {verdict}** - the pass conditions held in {passes} of 6 groups (needed 4).", "",
           "## 3. Walk-forward training sizes and cut-offs", "", "| Test year | Closed trades trained on | Keep if chance >= |",
           "|---|---|---|"] + [f"| {y} | {n:,} | {c:.3f} |" for y, n, c in cuts]

    from sklearn.inspection import permutation_importance
    last = ev[ev.y.notna()]
    g = gbm().fit(last[X].astype(float), last.y)
    smp = last.sample(n=min(6000, len(last)), random_state=0)
    imp = permutation_importance(g, smp[X].astype(float), smp.y, n_repeats=3, random_state=0, scoring="roc_auc")
    top = sorted(zip(X, imp.importances_mean), key=lambda x: -x[1])[:12]
    md += ["", "## 4. What the model looks at most (permutation importance, in-sample, for explanation only)", "",
           "| Feature | AUC drop when shuffled |", "|---|---|"] + [f"| {n} | {v:.4f} |" for n, v in top]
    pr.drop(columns=["legs"]).to_csv(ROOT / "data" / "ml_signals_predictions.csv.gz", index=False)  # local only
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
