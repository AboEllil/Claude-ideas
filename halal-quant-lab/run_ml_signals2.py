"""ML signal ranker v2: which of today's buy signals deserve the money first?

    SEC_USER_AGENT="Name email" python run_ml_signals2.py          # walk-forward test + report
    SEC_USER_AGENT="Name email" python run_ml_signals2.py --final  # save reports/ml_signals2/model.pkl

Same candidate signals and trade handling as run_ml_signals.py (dashboard rule + the user's arrow/squeeze
rule; sell half at +2 ATR, then stop at entry; costs included; decided at the close, bought next close).

Two questions per signal:
  1. HIT   - does the price reach +2 ATR above entry before the rule's exit? (that event is what makes a
             trade a winner under the user's exit plan). The stricter "before ever closing below entry"
             is reported too.
  2. SIZE  - how big is the trade's result, in ATR units (return / ATR% at entry, clipped -5..+15)?
Score = average of the two predictions' percentile ranks (chosen before the test).

New information on top of the 57 price features of v1:
  - earnings timing (SEC 8-K item 2.02): days since the last release, estimated days to the next one,
    the price reaction to the last release (a free proxy for the earnings surprise)       [US only]
  - company growth and quality (SEC XBRL, as filed - no look-ahead): revenue growth and acceleration,
    net-income growth, gross / operating / net margin, ROE, asset growth                  [US only]
  - sector strength: the sector's 20/60-day return, its rank among sectors, the share of its stocks
    above their 50-day average, the stock vs its sector                                  [US only]
  - the stock's 60-day strength rank in its market that day and how many signals fired (crowding)
Models: gradient boosting classifier (HIT) and regressor (SIZE), retrained every January on trades
that had CLOSED before that year (walk-forward from 2019). Judged on 2021-today.

Ranking test: a portfolio with a fixed number of slots (US 10, EGX 8, crypto 5; each slot = 1/N of
capital). Every day the new signals fill the free slots in score order. Compared with filling slots in
random order (average of 50 random orders) and with a simple ordering (weekly trend green first, then
strongest 60-day return).

PRE-REGISTERED PASS RULE (written before the first run), 2021-today:
  R1 signal quality : the top 20% of signals by score have a HIT rate at least 8 points higher AND a
                      higher average trade than the bottom 20%.
  R2 ranking value  : the score-ordered slot portfolio has a higher Sharpe AND a higher CAGR than the
                      random-order average, and a higher return in at least 4 of the 6 years 2021-2026.
  R3 beats simple   : the score-ordered slot portfolio's Sharpe >= the simple ordering's Sharpe.
  US (the market with the new data) PASSES if R1, R2 and R3 all hold. EGX passes if R1 and R2 hold.
  Crypto is reported only (too few signals).
  Extra check (does the new data earn its place?): the HIT model with the new features has a higher
  2021-today AUC in the US than the same model with price features only.
"""
import os
import pickle
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

from lab import sec_fundamentals as secf
from lab.metrics import stats
from run_ml_signals import COST, MARKETS, add_meta, bar_features, manage, rule_positions, trade_stats
from run_signal_lab import MIN_VALUE, load

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "ml_signals2"
SLOTS = {"US": 10, "EGX": 8, "Crypto": 5}
FIRST_TEST_YEAR, TEST_FROM = 2019, pd.Timestamp("2021-01-01")
SEC_COLS = ["days_since_earn", "days_to_next_earn_est", "earn_reaction", "rev_growth", "rev_accel", "ni_growth",
            "gross_margin", "op_margin", "net_margin", "roe", "asset_growth"]
SECTOR_COLS = ["sector_ret20", "sector_ret60", "sector_rank60", "sector_breadth50", "vs_sector60"]
CROSS_COLS = ["rs_rank60", "signals_today", "signals_5d"]
NEW_COLS = SEC_COLS + SECTOR_COLS + CROSS_COLS
SEC = {}


def strict_hit(c, t, a0, legs):
    """Reached +2 ATR before any close below the entry price?"""
    e = c[t + 1]
    end = max(j for _, j in legs)
    for j in range(t + 2, end + 1):
        if c[j] - e >= 2 * a0:
            return 1.0
        if c[j] < e:
            return 0.0
    return 0.0


def analyse(args):
    tk, df, market, bench = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if market == "EGX":
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 400:
        return None
    feats, d = bar_features(df, bench)
    idx = df.index
    if market == "US":
        sf = secf.features(SEC.get(tk), idx, df.Close)
        for col in SEC_COLS:
            feats[col] = sf[col].to_numpy() if col in sf else np.nan
        feats["earn_reaction"] = feats["earn_reaction"] / feats["atr_pct"]
    rows = []
    for src, lst in rule_positions(market, d).items():
        for t, kind, extra in lst:
            if t < 260 or not (d["value"][t] >= MIN_VALUE[market]):
                continue
            res = manage(d["c"], d["st"], d["a14"], t, kind, extra)
            rec = {"ticker": tk, "market": market, "source": src, "date": idx[t], "t": int(t), **feats.iloc[t].to_dict()}
            if res is None:
                if t + 1 >= len(idx):
                    continue
                rec.update(ret=np.nan, exit_date=pd.NaT, legs=None, hit=np.nan, hit_strict=np.nan)
            else:
                g, legs, xb = res
                rec.update(ret=g - 2 * COST[market], exit_date=idx[min(xb, len(idx) - 1)], legs=legs,
                           hit=float(legs[0][0] == 0.5), hit_strict=strict_hit(d["c"], t, d["a14"][t], legs))
            rows.append(rec)
    return tk, market, idx, d["c"], rows


def sector_map():
    m = {}
    for f in ("reports/universe/midcap_screen.csv", "reports/broad_screen.csv", "reports/top100_halal.csv"):
        p = ROOT / f
        if p.exists():
            d = pd.read_csv(p)
            m.update(dict(zip(d.ticker if "ticker" in d else d.iloc[:, 0], d.sector)))
    return m


def add_cross_features(ev, closes):
    """Sector strength, 60-day strength rank and signal crowding - all from data up to the signal day."""
    secs = sector_map()
    for mk in MARKETS:
        cl = closes[mk]
        sel = ev.market == mk
        dates = ev.loc[sel, "date"]
        r60 = cl / cl.shift(60) - 1
        rank = r60.rank(axis=1, pct=True)
        ev.loc[sel, "rs_rank60"] = [rank.at[d, t] if t in rank.columns else np.nan
                                    for d, t in zip(dates, ev.loc[sel, "ticker"])]
        n_day = ev[sel].groupby("date").size()
        daily = n_day.reindex(cl.index, fill_value=0)
        ev.loc[sel, "signals_today"] = n_day.reindex(dates).to_numpy()
        ev.loc[sel, "signals_5d"] = daily.rolling(5).sum().reindex(dates).to_numpy()
        if mk != "US":
            continue
        rets = cl.pct_change(fill_method=None).clip(-0.5, 0.5)
        above = (cl > cl.rolling(50).mean()).where(cl.notna())
        groups = {}
        for s in sorted({secs.get(t) for t in cl.columns} - {None, np.nan}):
            mem = [t for t in cl.columns if secs.get(t) == s]
            if len(mem) < 3:
                continue
            idx_ = (1 + rets[mem].mean(axis=1).fillna(0)).cumprod()
            groups[s] = pd.DataFrame({"sector_ret20": idx_ / idx_.shift(20) - 1, "sector_ret60": idx_ / idx_.shift(60) - 1,
                                      "sector_breadth50": above[mem].mean(axis=1)})
        r60s = pd.DataFrame({s: g.sector_ret60 for s, g in groups.items()})
        rk = r60s.rank(axis=1, pct=True)
        for i in ev.index[sel]:
            s, d = secs.get(ev.at[i, "ticker"]), ev.at[i, "date"]
            if s in groups and d in groups[s].index:
                g = groups[s].loc[d]
                ev.loc[i, ["sector_ret20", "sector_ret60", "sector_breadth50"]] = g.to_numpy()
                ev.at[i, "sector_rank60"] = rk.at[d, s]
                ev.at[i, "vs_sector60"] = ev.at[i, "ret60"] - g.sector_ret60
    return ev


def x_cols(ev, new=True):
    skip = {"ticker", "market", "source", "date", "t", "ret", "exit_date", "legs", "days", "y", "hit", "hit_strict",
            "y_size", "keep"}
    cols = [c for c in ev.columns if c not in skip and not c.startswith(("p_", "s_", "score"))]
    return cols if new else [c for c in cols if c not in NEW_COLS]


def clf():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=250, min_samples_leaf=60,
                                          l2_regularization=2.0, random_state=0)


def reg():
    return HistGradientBoostingRegressor(loss="absolute_error", max_depth=3, learning_rate=0.04, max_iter=250,
                                         min_samples_leaf=60, l2_regularization=2.0, random_state=0)


def fit_predict(tr, te, X):
    c = clf().fit(tr[X].astype(float), tr.hit)
    r = reg().fit(tr[X].astype(float), tr.y_size)
    ref_h = np.sort(c.predict_proba(tr[X].astype(float))[:, 1])
    ref_s = np.sort(r.predict(tr[X].astype(float)))
    ph, ps = c.predict_proba(te[X].astype(float))[:, 1], r.predict(te[X].astype(float))
    score = (np.searchsorted(ref_h, ph) / len(ref_h) + np.searchsorted(ref_s, ps) / len(ref_s)) / 2
    return ph, ps, score, c, r


def slot_pick(cands, key, n_slots, rng=None):
    """Fill free slots each day in `key` order (descending) or random order. Returns the chosen trades."""
    open_ = {}
    chosen = []
    for d, g in cands.groupby("date", sort=True):
        open_ = {t: x for t, x in open_.items() if x > d}
        free = n_slots - len(open_)
        if free <= 0:
            continue
        g = g[~g.ticker.isin(open_)]
        g = g.sample(frac=1, random_state=rng) if rng is not None else g.sort_values(key, ascending=False)
        for i, r in g.head(free).iterrows():
            open_[r.ticker] = r.exit_date
            chosen.append(i)
    return cands.loc[chosen]


def slot_returns(trades, idx_map, closes, market, n_slots):
    pos = {}
    for tk, g in trades.groupby("ticker"):
        p = np.zeros(len(idx_map[tk]))
        for _, e in g.iterrows():
            start, frac = int(e.t), 1.0
            for f, j in e.legs:
                p[start:j] = np.maximum(p[start:j], frac)
                start, frac = j, frac - f
        pos[tk] = pd.Series(p, index=idx_map[tk])
    P = pd.DataFrame(pos).reindex(closes.index).fillna(0).shift(1).fillna(0) / n_slots
    R = closes[P.columns].pct_change(fill_method=None).fillna(0)
    r = (P.shift(1) * R).sum(axis=1) - COST[market] * P.diff().abs().sum(axis=1).fillna(0)
    return r.loc["2021":]


def summarize(r, market):
    s = stats(r, year=365 if market == "Crypto" else 252)
    yearly = (1 + r).groupby(r.index.year).prod() - 1
    return s, yearly


def build():
    global SEC
    jobs = load()
    us = [j[0] for j in jobs if j[2] == "US"]
    SEC = secf.fetch(us)
    res = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:          # forked workers share SEC
        for i, r in enumerate(ex.map(analyse, jobs, chunksize=2), 1):
            if r:
                res.append(r)
            if i % 100 == 0:
                print(f"  features {i}/{len(jobs)}", flush=True)
    ev = pd.DataFrame([row for r in res for row in r[4]]).sort_values("date").reset_index(drop=True)
    closes = {mk: pd.DataFrame({r[0]: pd.Series(r[3], index=r[2]) for r in res if r[1] == mk}).sort_index()
              for mk in MARKETS}
    ev = add_cross_features(add_meta(ev), closes)
    ev["y_size"] = (ev.ret / ev.atr_pct).clip(-5, 15)
    return ev, res, closes


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ev, res, closes = build()
    X, X_old = x_cols(ev), x_cols(ev, new=False)
    if "--final" in sys.argv:
        lab = ev[ev.hit.notna()]
        _, _, _, c, r = fit_predict(lab, lab.head(5), X)
        ref_h = np.sort(c.predict_proba(lab[X].astype(float))[:, 1])
        ref_s = np.sort(r.predict(lab[X].astype(float)))
        with open(OUT / "model.pkl", "wb") as f:
            pickle.dump({"clf": c, "reg": r, "X": X, "ref_hit": ref_h, "ref_size": ref_s,
                         "trained_to": str(lab.exit_date.max().date())}, f)
        print(f"saved model on {len(lab):,} closed trades")
        return
    parts = []
    for yr in range(FIRST_TEST_YEAR, ev.date.dt.year.max() + 1):
        start = pd.Timestamp(f"{yr}-01-01")
        tr = ev[(ev.exit_date < start) & ev.hit.notna()]
        te = ev[(ev.date >= start) & (ev.date < pd.Timestamp(f"{yr + 1}-01-01"))].copy()
        if te.empty:
            continue
        te["p_hit"], te["p_size"], te["score"], _, _ = fit_predict(tr, te, X)
        te["p_hit_old"] = clf().fit(tr[X_old].astype(float), tr.hit).predict_proba(te[X_old].astype(float))[:, 1]
        parts.append(te)
        print(f"  {yr}: trained on {len(tr):,} closed trades", flush=True)
    pr = pd.concat(parts)
    test = pr[(pr.date >= TEST_FROM) & pr.hit.notna()].copy()
    idx_map = {r[0]: r[2] for r in res}

    md = ["# ML signal ranker v2 - which signals deserve the money first?\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev):,} signals on {len(res)} halal assets, "
          f"{int(ev.hit.notna().sum()):,} closed trades, {len(X)} features ({len(NEW_COLS)} new: earnings timing, "
          "SEC growth and quality, sector strength, strength rank, crowding). Walk-forward from 2019 (each year's "
          "model only saw trades closed before that year); judged on 2021-today. Trades: half at +2 ATR, then "
          "stop at entry, else the rule's exit; costs included.\n",
          "Pre-registered pass rule - US: R1 top-20% HIT rate >= bottom-20% + 8 points and higher average trade; "
          "R2 score-ordered slot portfolio beats random order on Sharpe and CAGR and in >= 4 of 6 years; "
          "R3 Sharpe >= simple ordering (weekly green first, then 60-day return). EGX: R1 + R2. Crypto: info only.\n",
          "## 1. How well does it predict? (2021-today, AUC: 0.50 = coin flip)", "",
          "| Market | Trades | HIT: new model | HIT: price-only model | SIZE: rank correlation with real result |",
          "|---|---|---|---|---|"]
    for mk in MARKETS:
        d = test[test.market == mk]
        md.append(f"| {mk} | {len(d):,} | {roc_auc_score(d.hit, d.p_hit):.3f} | {roc_auc_score(d.hit, d.p_hit_old):.3f} | "
                  f"{d.p_size.corr(d.y_size, method='spearman'):+.3f} |")
    md += ["", "## 2. Signals by score (fifths within each market, 2021-today)", "",
           "| Market | Score fifth | Trades | HIT +2 ATR before exit | HIT before any close below entry | Win rate | Avg trade | Profit factor |",
           "|---|---|---|---|---|---|---|---|"]
    r1 = {}
    for mk in MARKETS:
        d = test[test.market == mk].copy()
        d["q"] = pd.qcut(d.score.rank(method="first"), 5, labels=["1 lowest", "2", "3", "4", "5 highest"])
        for q, g in d.groupby("q", observed=True):
            s = trade_stats(g)
            md.append(f"| {mk} | {q} | {s['n']} | {g.hit.mean():.0%} | {g.hit_strict.mean():.0%} | {s['win']:.0%} | "
                      f"{s['avg']:+.1%} | {s['pf']:.2f} |")
        lo, hi = d[d.q == "1 lowest"], d[d.q == "5 highest"]
        r1[mk] = (hi.hit.mean() - lo.hit.mean() >= 0.08) and (hi.ret.mean() > lo.ret.mean())

    md += ["", "## 3. Ranking test: fixed slots, new signals fill free slots each day (2021-today)", "",
           "| Market | Slots | Ordering | Trades | Win rate | Avg trade | CAGR | Sharpe | Max DD | " +
           " | ".join(str(y) for y in range(2021, 2027)) + " |", "|---" * 15 + "|"]
    verdicts = {}
    for mk in MARKETS:
        d = test[test.market == mk].sort_values("source").drop_duplicates(["ticker", "date"])
        d["simple"] = d.weekly_up * 10 + d.ret60.fillna(-1)
        N = SLOTS[mk]
        rows = {}
        for name, key in (("ML score", "score"), ("Simple: weekly green, then 60-day return", "simple")):
            ch = slot_pick(d, key, N)
            rows[name] = (ch, *summarize(slot_returns(ch, idx_map, closes[mk], mk, N), mk))
        rnd_s, rnd_y, rnd_tr = [], [], []
        for seed in range(50):
            ch = slot_pick(d, None, N, rng=seed)
            s, y = summarize(slot_returns(ch, idx_map, closes[mk], mk, N), mk)
            rnd_s.append(s)
            rnd_y.append(y)
            rnd_tr.append(trade_stats(ch))
        rs = {k: float(np.mean([s[k] for s in rnd_s])) for k in ("cagr", "sharpe", "max_dd")}
        ry = pd.concat(rnd_y, axis=1).mean(axis=1)
        rt = {k: float(np.nanmean([t[k] for t in rnd_tr])) for k in ("n", "win", "avg")}
        for name, (ch, s, y) in rows.items():
            t = trade_stats(ch)
            md.append(f"| {mk} | {N} | {name} | {t['n']} | {t['win']:.0%} | {t['avg']:+.1%} | {s['cagr']:.1%} | "
                      f"{s['sharpe']:.2f} | {s['max_dd']:.0%} | " + " | ".join(f"{y.get(yy, np.nan):+.0%}" for yy in range(2021, 2027)) + " |")
        md.append(f"| {mk} | {N} | Random order (avg of 50) | {rt['n']:.0f} | {rt['win']:.0%} | {rt['avg']:+.1%} | "
                  f"{rs['cagr']:.1%} | {rs['sharpe']:.2f} | {rs['max_dd']:.0%} | " +
                  " | ".join(f"{ry.get(yy, np.nan):+.0%}" for yy in range(2021, 2027)) + " |")
        _, s_ml, y_ml = rows["ML score"]
        _, s_simple, _ = rows["Simple: weekly green, then 60-day return"]
        years_better = int(sum(y_ml.get(yy, -9) > ry.get(yy, 9) for yy in range(2021, 2027)))
        R2 = s_ml["sharpe"] > rs["sharpe"] and s_ml["cagr"] > rs["cagr"] and years_better >= 4
        R3 = s_ml["sharpe"] >= s_simple["sharpe"]
        verdicts[mk] = (r1[mk], R2, R3, years_better)

    md += ["", "## 4. Verdict (pre-registered)", "", "| Market | R1 signal quality | R2 beats random | R3 beats simple | Result |",
           "|---|---|---|---|---|"]
    yn = lambda b: "yes" if b else "no"
    for mk in MARKETS:
        a, b, c, yb = verdicts[mk]
        res_ = ("PASS" if (a and b and c) else "FAIL") if mk == "US" else ("PASS" if (a and b) else "FAIL") if mk == "EGX" else "info only"
        md.append(f"| {mk} | {yn(a)} | {yn(b)} (better in {yb} of 6 years) | {yn(c)} | **{res_}** |")
    us = test[test.market == "US"]
    md += ["", f"Extra check - new data earns its place (US HIT AUC new > price-only): "
               f"**{yn(roc_auc_score(us.hit, us.p_hit) > roc_auc_score(us.hit, us.p_hit_old))}**."]

    from sklearn.inspection import permutation_importance
    lab = ev[ev.hit.notna() & (ev.market == "US")]
    c = clf().fit(lab[X].astype(float), lab.hit)
    smp = lab.sample(n=min(6000, len(lab)), random_state=0)
    imp = permutation_importance(c, smp[X].astype(float), smp.hit, n_repeats=3, random_state=0, scoring="roc_auc")
    top = sorted(zip(X, imp.importances_mean), key=lambda x: -x[1])[:15]
    md += ["", "## 5. What the US HIT model looks at most (permutation importance, in-sample, explanation only)", "",
           "| Feature | New? | AUC drop when shuffled |", "|---|---|---|"] + \
          [f"| {n} | {'new' if n in NEW_COLS else ''} | {v:.4f} |" for n, v in top]
    pr.drop(columns=["legs"]).to_csv(ROOT / "data" / "ml_signals2_predictions.csv.gz", index=False)   # local only
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
