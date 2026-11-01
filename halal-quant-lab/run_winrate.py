"""Win-rate lab: raise the share of winning trades without killing profit.

    python run_winrate.py

Signals: the user's rule (AlgoAlpha green arrow + bright green Squeeze, liquid assets) on US halal stocks,
halal EGX stocks and halal crypto (same assets as run_signal_lab.py). Decided at the close, traded at
the next close; an exit condition seen at a close is executed at the next close. Costs per side
US 0.05% / EGX 0.25% / crypto 0.10%.

Part A - exits (entries unchanged):
  E1 red arrow (current)                  E4 sell half at +2 ATR, then breakeven stop on the rest, else red
  E2 take profit at +2 ATR, else red      E5 once +1.5 ATR, move the stop to breakeven, else red
  E3 take profit at +3 ATR, else red
Part B - signal-quality model: gradient boosting on 20 features measured at the signal close, trained
  ONLY on signals from 2016-2020 (label: the E1 trade made money). The cut-off keeps the best 40% of
  signals by predicted win probability, set from out-of-fold predictions inside 2016-2020.
  Judged ONLY on 2021-today.
Part C - which conditions win more often (win rate by feature quintile, train and test).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit

from lab import tv
from lab.metrics import stats
from run_signal_lab import MIN_VALUE, load, supertrend_set

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "winrate"
COST = {"US": 0.0005, "EGX": 0.0025, "Crypto": 0.001}
SPLIT = pd.Timestamp("2021-01-01")
EXITS = ["E1 red arrow", "E2 TP +2 ATR", "E3 TP +3 ATR", "E4 half +2 ATR, breakeven", "E5 breakeven after +1.5 ATR"]
FEATURES = ["mom_atr", "mom_slope", "sqz_days", "adx", "rsi", "dist_atr", "vol_ratio", "weekly_up", "mkt_up",
            "rs126", "high52", "atr_pct", "ret5", "ret20", "ret60", "lor_pred", "lor_arrow", "ob_touch",
            "red_days", "cluster_up"]


def simulate(c, st, t, a0, kind):
    """Return (gross return, [(fraction, exit decision bar)])."""
    T = len(c)
    if t + 1 >= T:
        return None
    e = c[t + 1]
    half_done, be_armed = False, False
    legs = []
    for j in range(t + 2, T):
        red = st[j] == 0
        gain = c[j] - e
        if kind == "E2 TP +2 ATR" and gain >= 2 * a0:
            legs.append((1.0, j)); break
        if kind == "E3 TP +3 ATR" and gain >= 3 * a0:
            legs.append((1.0, j)); break
        if kind == "E4 half +2 ATR, breakeven":
            if not half_done and gain >= 2 * a0:
                legs.append((0.5, j)); half_done = True
                continue
            if half_done and c[j] < e:
                legs.append((0.5, j)); break
        if kind == "E5 breakeven after +1.5 ATR":
            if gain >= 1.5 * a0:
                be_armed = True
            if be_armed and c[j] < e:
                legs.append((1.0, j)); break
        if red:
            legs.append((1.0 - sum(f for f, _ in legs), j)); break
    else:
        legs.append((1.0 - sum(f for f, _ in legs), T - 1))
    ret = sum(f * (c[min(j + 1, T - 1)] / e) for f, j in legs) - 1
    return ret, legs


def analyse(args):
    tk, df, market, bench = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if market == "EGX":
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 400:
        return None
    idx = df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df["Volume"].fillna(0).to_numpy(float)
    b = bench.reindex(idx).ffill().to_numpy(float)
    st, line = supertrend_set(h, l, c, 10, 3.0)
    sq_on, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    bright = (m > 0) & np.r_[False, m[1:] > m[:-1]]
    flip = np.r_[False, (st[1:] == 1) & (st[:-1] == 0)]
    lpos, pred = tv.lorentzian(o, h, l, c)
    larrow = np.r_[False, (lpos[1:] == 1) & (lpos[:-1] == 0)]
    _, _, _, zb, zt, _, _ = tv.smc_state(h, l, c, 10, False)
    ob_touch = ~np.isnan(zb) & (l <= zt * 1.01) & (c >= zb)
    a14 = tv.atr(h, l, c, 14)
    value = pd.Series(c * v).rolling(20).median().to_numpy()
    vol_ratio = v / pd.Series(v).rolling(20).mean().shift(1).to_numpy()
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = tv.rma(tv.tr(h, l, c), 14)
    adx = tv.rma(100 * np.abs(tv.rma(pdm, 14) - tv.rma(mdm, 14)) / (tv.rma(pdm, 14) + tv.rma(mdm, 14)), 14)
    rsi = tv.rsi(c, 14)
    cs = pd.Series(c)
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    if len(wk) > 120:
        wst = tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0]
        weekly = pd.Series(wst, index=wk.index).shift(1).reindex(idx, method="ffill").fillna(0).to_numpy()
    else:
        weekly = np.zeros(len(c))
    bs = pd.Series(b)
    feats = pd.DataFrame({
        "mom_atr": m / a14, "mom_slope": (m - np.r_[np.nan, m[:-1]]) / a14,
        "sqz_days": pd.Series(sq_on.astype(float)).rolling(20).sum().to_numpy(), "adx": adx, "rsi": rsi,
        "dist_atr": (c - line) / a14, "vol_ratio": vol_ratio, "weekly_up": weekly,
        "mkt_up": (bs > bs.rolling(200).mean()).astype(float).to_numpy(),
        "rs126": (cs / cs.shift(126) - 1 - (bs / bs.shift(126) - 1)).to_numpy(),
        "high52": (cs / pd.Series(h).rolling(252, min_periods=120).max()).to_numpy(), "atr_pct": a14 / c,
        "ret5": (cs / cs.shift(5) - 1).to_numpy(), "ret20": (cs / cs.shift(20) - 1).to_numpy(),
        "ret60": (cs / cs.shift(60) - 1).to_numpy(), "lor_pred": pred,
        "lor_arrow": pd.Series(larrow.astype(float)).rolling(6, min_periods=1).max().to_numpy(),
        "ob_touch": pd.Series(ob_touch.astype(float)).rolling(6, min_periods=1).max().to_numpy(),
    })
    run_red = np.zeros(len(c))
    for t in range(1, len(c)):
        run_red[t] = run_red[t - 1] + 1 if st[t] == 0 else 0
    feats["red_days"] = np.r_[0, run_red[:-1]]
    feats["cluster_up"] = np.nan                                  # filled per market later (breadth)
    entries = np.where(flip & bright & (value >= MIN_VALUE[market]))[0]
    rows = []
    for t in entries:
        if t < 260 or not np.isfinite(a14[t]):
            continue
        rec = {"ticker": tk, "market": market, "date": idx[t], "t": int(t), **feats.iloc[t].to_dict()}
        ok = True
        for ex in EXITS:
            s = simulate(c, st, t, a14[t], ex)
            if s is None:
                ok = False
                break
            ret, legs = s
            rec[ex] = ret - 2 * COST[market]
            rec[ex + "|legs"] = legs
            rec[ex + "|days"] = max(j for _, j in legs) - t
        if ok:
            rows.append(rec)
    return tk, market, idx, c, st, rows


def portfolio(events, idx_map, closes, market, ex, period):
    """Equal weight over open positions (max 10% each). Positions are decided at a close (signal bar t up
    to the exit decision bar) and executed at the next close."""
    pos = {}
    for tk, g in events.groupby("ticker"):
        p = np.zeros(len(idx_map[tk]))
        for _, e in g.iterrows():
            start, frac = int(e.t), 1.0
            for f, j in e[ex + "|legs"]:
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
    a, b = period
    return stats(r.loc[a:b], year=365 if market == "Crypto" else 252)


def trade_stats(ev, col):
    r = ev[col].to_numpy()
    if len(r) == 0:
        return dict(n=0, win=np.nan, avg=np.nan, pf=np.nan)
    g, lo = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=float((r > 0).mean()), avg=float(r.mean()), pf=g / lo if lo > 0 else np.nan)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = load()
    res = []
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for i, r in enumerate(ex.map(analyse, jobs, chunksize=4), 1):
            if r:
                res.append(r)
            if i % 100 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    ev = pd.DataFrame([row for r in res for row in r[5]])
    # breadth: share of the market's assets that flipped green in the last 10 days (crowd confirmation)
    for mk in ev.market.unique():
        rs = [r for r in res if r[1] == mk]
        flips = pd.DataFrame({r[0]: pd.Series(np.r_[0, (r[4][1:] == 1) & (r[4][:-1] == 0)].astype(float), index=r[2])
                              for r in rs}).sort_index()
        breadth = flips.rolling(10, min_periods=1).max().mean(axis=1)
        sel = ev.market == mk
        ev.loc[sel, "cluster_up"] = breadth.reindex(ev.loc[sel, "date"]).to_numpy()
    ev = ev.sort_values("date").reset_index(drop=True)
    for mk in ("US", "EGX", "Crypto"):
        ev[f"is_{mk}"] = (ev.market == mk).astype(float)
    X_cols = FEATURES + ["is_US", "is_EGX", "is_Crypto"]
    tr, te = ev[ev.date < SPLIT], ev[ev.date >= SPLIT]
    y_tr = (tr["E1 red arrow"] > 0).astype(int)

    # out-of-fold scores inside the training period -> cut-off for the best 40%
    oof = np.full(len(tr), np.nan)
    for a, b in TimeSeriesSplit(n_splits=5).split(tr):
        mdl = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
                                             min_samples_leaf=40, random_state=0)
        mdl.fit(tr.iloc[a][X_cols], y_tr.iloc[a])
        oof[b] = mdl.predict_proba(tr.iloc[b][X_cols])[:, 1]
    cut = np.nanquantile(oof, 0.60)
    model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
                                           min_samples_leaf=40, random_state=0).fit(tr[X_cols], y_tr)
    ev["p_win"] = model.predict_proba(ev[X_cols])[:, 1]
    ev.loc[tr.index[~np.isnan(oof)], "p_oof"] = oof[~np.isnan(oof)]
    ev["ml_pick"] = ev.p_win >= cut
    te = ev[ev.date >= SPLIT]
    oof_tr = ev[(ev.date < SPLIT) & ev.p_oof.notna()]

    selections = {"All signals (your rule)": lambda d: d, "Weekly trend green": lambda d: d[d.weekly_up > 0.5],
                  "ML best 40%": lambda d: d[d.ml_pick], "ML best 40% + weekly green": lambda d: d[d.ml_pick & (d.weekly_up > 0.5)]}
    md = ["# Win-rate lab\n", f"Generated {pd.Timestamp.now():%Y-%m-%d}. {len(ev)} signals of the user's rule "
          f"(arrow + bright squeeze) on {len(res)} assets. Train = signals before 2021, test = 2021-today. "
          "Trade returns include costs. Portfolio: max 10% per position.\n"]
    md += ["## A. Exits: win rate vs profit (all signals, TEST 2021-today)", "",
           "| Market | Exit | Trades | Win rate | Avg trade | Profit factor | Avg days | Portfolio CAGR | Sharpe | Max DD |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    closes = {mk: pd.DataFrame({r[0]: pd.Series(r[3], index=r[2]) for r in res if r[1] == mk}).sort_index()
              for mk in ("US", "EGX", "Crypto")}
    idx_map = {r[0]: r[2] for r in res}
    for mk in ("US", "EGX", "Crypto"):
        d = te[te.market == mk]
        for exn in EXITS:
            s = trade_stats(d, exn)
            p = portfolio(d, idx_map, closes[mk], mk, exn, ("2021", "2100"))
            md.append(f"| {mk} | {exn} | {s['n']} | {s['win']:.0%} | {s['avg']:+.1%} | {s['pf']:.2f} | "
                      f"{d[exn + '|days'].mean():.0f} | {p['cagr']:.1%} | {p['sharpe']:.2f} | {p['max_dd']:.0%} |")
    md += ["", "## B. Signal-quality model (trained on 2016-2020 only)", "",
           f"Cut-off: predicted win probability >= {cut:.2f} (the best 40% of out-of-fold training signals). "
           f"Out-of-fold check inside training: win rate {((oof_tr['E1 red arrow'] > 0)[oof_tr.p_oof >= cut]).mean():.0%} "
           f"for picked vs {((oof_tr['E1 red arrow'] > 0)[oof_tr.p_oof < cut]).mean():.0%} for rejected signals.", "",
           "| Market | Signals kept | Exit | Trades | Win rate | Avg trade | Profit factor | Portfolio CAGR | Sharpe | Max DD |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for mk in ("US", "EGX", "Crypto"):
        for sname, fn in selections.items():
            d = fn(te[te.market == mk])
            for exn in ("E1 red arrow", "E4 half +2 ATR, breakeven", "E5 breakeven after +1.5 ATR"):
                s = trade_stats(d, exn)
                if s["n"] < 5:
                    continue
                p = portfolio(d, idx_map, closes[mk], mk, exn, ("2021", "2100"))
                md.append(f"| {mk} | {sname} | {exn} | {s['n']} | {s['win']:.0%} | {s['avg']:+.1%} | {s['pf']:.2f} | "
                          f"{p['cagr']:.1%} | {p['sharpe']:.2f} | {p['max_dd']:.0%} |")
    md += ["", "## C. When do signals win more often? (red-arrow exit, win rate by quintile: lowest -> highest)", "",
           "| Feature | Train Q1 | Q2 | Q3 | Q4 | Q5 | Test Q1 | Q2 | Q3 | Q4 | Q5 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for fcol in FEATURES:
        cells = []
        for d in (ev[ev.date < SPLIT], te):
            x = d[[fcol, "E1 red arrow"]].dropna()
            if x[fcol].nunique() < 5:
                q = x.groupby(x[fcol].round(0))["E1 red arrow"].apply(lambda r: (r > 0).mean())
                cells += [f"{v:.0%}" for v in q.to_numpy()[:5]] + [""] * (5 - min(5, len(q)))
            else:
                q = x.groupby(pd.qcut(x[fcol], 5, duplicates="drop"), observed=True)["E1 red arrow"].apply(lambda r: (r > 0).mean())
                cells += [f"{v:.0%}" for v in q.to_numpy()] + [""] * (5 - len(q))
        md.append(f"| {fcol} | " + " | ".join(cells) + " |")
    ev.drop(columns=[c for c in ev.columns if c.endswith("|legs")]).to_csv(OUT / "signals.csv", index=False)
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
