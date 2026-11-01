"""Walk-forward machine-learning forecaster: which assets beat their market over the next 20 trading days?

    python run_ml_forecast.py

Every Friday close, for every asset (US halal stocks, halal EGX stocks, halal crypto), 30 features
describe trend, momentum, volatility, volume, the user's indicators and the market regime. The label is
1 if the asset's return from the next close to 20 trading days later beats the equal-weight average of
its market. A gradient-boosting classifier is retrained every January on all earlier weeks only, with a
30-day embargo (labels overlap 20 days), and predicts that whole year - so every prediction is made
without seeing its future. The portfolio holds, each week, the top-K predicted assets of each market
(US 10, EGX 8, crypto 5), liquid ones only, traded at the next close with costs.

Writes reports/ml/REPORT.md and reports/ml/latest_predictions.csv (this week's ranking).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

from lab import tv
from run_signal_lab import MIN_VALUE, evaluate, load, supertrend_set

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "ml"
TOPK = {"US": 10, "EGX": 8, "Crypto": 5}
H = 20
FIRST_TEST_YEAR = 2019


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def features(args):
    tk, df, market, bench = args
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if market == "EGX":
        df = df[~(df.Close.pct_change().abs() > 0.5)]
    if len(df) < 400:
        return None
    idx = df.index
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    v = df["Volume"].fillna(0).to_numpy(float)
    cs = pd.Series(c, index=idx)
    r1 = cs.pct_change()
    a14 = tv.atr(h, l, c, 14)
    st, line = supertrend_set(h, l, c, 10, 3.0)
    sq_on, mom = tv.squeeze(o, h, l, c)
    m = np.nan_to_num(mom)
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdi, mdi = tv.rma(pdm, 14), tv.rma(mdm, 14)
    adx = tv.rma(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
    run = np.zeros(len(c))
    for t in range(1, len(c)):
        run[t] = run[t - 1] + 1 if st[t] == st[t - 1] else 1
    wk = df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    weekly = (pd.Series(tv.adaptive_supertrend(*(wk[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")))[0],
                        index=wk.index).shift(1).reindex(idx, method="ffill").fillna(0).to_numpy()
              if len(wk) > 120 else np.zeros(len(c)))
    f = pd.DataFrame({
        "ret5": cs / cs.shift(5) - 1, "ret20": cs / cs.shift(20) - 1, "ret60": cs / cs.shift(60) - 1,
        "ret120": cs / cs.shift(120) - 1, "mom12_1": cs.shift(21) / cs.shift(252) - 1,
        "vol20": r1.rolling(20).std() * np.sqrt(252), "vol60": r1.rolling(60).std() * np.sqrt(252),
        "rsi14": tv.rsi(c, 14), "rsi2": tv.rsi(c, 2), "adx": adx, "di_spread": (pdi - mdi) / (pdi + mdi),
        "dist50": (cs - cs.rolling(50).mean()) / a14, "dist200": (cs - cs.rolling(200).mean()) / a14,
        "ema_cross": (ema(c, 50) > ema(c, 200)).astype(float), "high52": cs / pd.Series(h, index=idx).rolling(252, min_periods=120).max(),
        "low52": cs / pd.Series(l, index=idx).rolling(252, min_periods=120).min(), "atr_pct": a14 / c,
        "st_up": st, "st_days": run * np.where(st == 1, 1, -1), "st_dist": (c - line) / a14,
        "sq_mom": m / a14, "sq_rising": np.r_[0, (m[1:] > m[:-1]).astype(float)],
        "sq_days": pd.Series(sq_on.astype(float), index=idx).rolling(20).sum(),
        "vol_ratio": pd.Series(v, index=idx) / pd.Series(v, index=idx).rolling(50).mean(),
        "weekly_up": weekly,
    }, index=idx)
    f["value"] = (cs * pd.Series(v, index=idx)).rolling(20).median()
    f["fwd"] = cs.shift(-1 - H) / cs.shift(-1) - 1                 # from next close to 20 days later
    f["ticker"], f["market"] = tk, market
    weekly_idx = idx.to_series().groupby(idx.to_period("W-FRI")).max()
    return f.loc[weekly_idx.values], pd.Series(c, index=idx)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = load()
    bench = {}
    for _, _, mk, b in jobs:
        bench.setdefault(mk, b)
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        out = [r for r in ex.map(features, jobs, chunksize=4) if r]
    panel = pd.concat([f for f, _ in out]).reset_index().rename(columns={"index": "date", "Date": "date"})
    closes = {mk: pd.DataFrame({f.ticker.iloc[0]: c for f, c in out if f.market.iloc[0] == mk}).sort_index()
              for mk in TOPK}
    # market-level features and the label (beat the market's equal-weight forward return)
    panel["date"] = pd.to_datetime(panel["date"])
    for mk in TOPK:
        b = bench[mk].reindex(closes[mk].index).ffill()
        mf = pd.DataFrame({"mkt_ret20": b / b.shift(20) - 1, "mkt_up200": (b > b.rolling(200).mean()).astype(float),
                           "breadth50": (closes[mk] > closes[mk].rolling(50).mean()).where(closes[mk].notna()).mean(axis=1)})
        sel = panel.market == mk
        panel.loc[sel, mf.columns] = mf.reindex(panel.loc[sel, "date"]).to_numpy()
    panel["fwd_mkt"] = panel.groupby(["market", "date"])["fwd"].transform("mean")
    panel["y"] = (panel.fwd > panel.fwd_mkt).astype(float).where(panel.fwd.notna())
    for col in ("ret20", "ret60", "mom12_1", "vol60", "high52"):                      # cross-sectional ranks
        panel[col + "_rank"] = panel.groupby(["market", "date"])[col].rank(pct=True)
    for mk in TOPK:
        panel[f"is_{mk}"] = (panel.market == mk).astype(float)
    X = [c for c in panel.columns if c not in ("date", "ticker", "market", "fwd", "fwd_mkt", "y", "value")]
    panel = panel.sort_values("date").reset_index(drop=True)

    preds, aucs = [], []
    years = range(FIRST_TEST_YEAR, panel.date.dt.year.max() + 1)
    model = None
    for y in years:
        start = pd.Timestamp(f"{y}-01-01")
        tr = panel[(panel.date < start - pd.Timedelta(days=30)) & panel.y.notna()]
        te = panel[(panel.date >= start) & (panel.date < pd.Timestamp(f"{y + 1}-01-01"))].copy()
        model = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, min_samples_leaf=200,
                                               l2_regularization=1.0, random_state=0).fit(tr[X], tr.y)
        te["p"] = model.predict_proba(te[X])[:, 1]
        preds.append(te)
        lab = te.dropna(subset=["y"])
        if len(lab) > 100:
            aucs.append((y, roc_auc_score(lab.y, lab.p), len(tr)))
    pr = pd.concat(preds)

    md = ["# Walk-forward ML forecaster\n",
          f"Generated {pd.Timestamp.now():%Y-%m-%d}. {panel.ticker.nunique()} assets, weekly predictions, {len(X)} features. "
          f"Retrained every January on earlier data only (30-day embargo). Label: beats its market's average over "
          f"the next {H} trading days. Out-of-sample from {FIRST_TEST_YEAR}.\n",
          "## Prediction quality (out-of-sample)", "",
          "AUC 0.50 = coin flip; 0.55+ is useful for stock picking.", "",
          "| Year | AUC | Training rows |", "|---|---|---|"]
    md += [f"| {y} | {a:.3f} | {n:,} |" for y, a, n in aucs]
    lab = pr.dropna(subset=["y"]).copy()
    lab["q"] = lab.groupby(["market", "date"])["p"].rank(pct=True)
    md += ["", "Hit rate (beat the market over 20 days) by predicted rank within each week:", "",
           "| Market | Bottom 20% | 20-40% | 40-60% | 60-80% | Top 20% | Top 20% avg 20-day excess return |", "|---|---|---|---|---|---|---|"]
    for mk in TOPK:
        d = lab[lab.market == mk]
        g = d.groupby(pd.cut(d.q, [0, .2, .4, .6, .8, 1.0]), observed=True)
        hit = g.y.mean().to_numpy()
        ex = (d[d.q > 0.8].fwd - d[d.q > 0.8].fwd_mkt).mean()
        md.append(f"| {mk} | " + " | ".join(f"{x:.0%}" for x in hit) + f" | {ex:+.2%} |")

    md += ["", "## Portfolio: hold the top-K predictions each week (next-close execution, costs, max 10% each)", "",
           "| Market | Strategy | Period | Win | PF | CAGR | Sharpe | Max DD |", "|---|---|---|---|---|---|---|---|"]
    for mk in TOPK:
        d = pr[(pr.market == mk) & (pr.value >= MIN_VALUE[mk])]
        cl = closes[mk]
        picks = {dt: list(g.nlargest(TOPK[mk], "p").ticker) for dt, g in d.groupby("date")}
        picks_reg = {dt: (v if d[d.date == dt].mkt_up200.iloc[0] > 0.5 else []) for dt, v in picks.items()}
        for name, pk in (("ML top-K", picks), ("ML top-K, only when market > 200-day", picks_reg)):
            P = pd.DataFrame(0.0, index=cl.index, columns=cl.columns)
            dates = sorted(pk)
            for i, dt in enumerate(dates):
                end = dates[i + 1] if i + 1 < len(dates) else cl.index[-1] + pd.Timedelta(days=1)
                if pk[dt]:
                    P.loc[(P.index >= dt) & (P.index < end), pk[dt]] = 1.0
            pos = {t: P[t] for t in P.columns}
            for per in ((str(FIRST_TEST_YEAR), "2100"), ("2021", "2100")):
                s = evaluate(pos, cl, mk, per)
                md.append(f"| {mk} | {name} | {per[0]}-today | {s['win']:.0%} | {s['pf']:.2f} | {s['cagr']:.1%} | "
                          f"{s['sharpe']:.2f} | {s['max_dd']:.0%} |")
        bh = {t: pd.Series(1.0, index=cl.index).where(cl[t].notna(), 0.0) for t in cl.columns}
        for per in ((str(FIRST_TEST_YEAR), "2100"), ("2021", "2100")):
            s = evaluate(bh, cl, mk, per)
            md.append(f"| {mk} | Buy & hold (equal weight) | {per[0]}-today | | | {s['cagr']:.1%} | {s['sharpe']:.2f} | {s['max_dd']:.0%} |")

    # what the last model relies on
    last = panel[(panel.date >= pd.Timestamp(f"{years[-1] - 1}-01-01")) & panel.y.notna()].sample(
        n=min(20000, int(panel.y.notna().sum())), random_state=0)
    imp = permutation_importance(model, last[X], last.y, n_repeats=3, random_state=0, scoring="roc_auc")
    top = sorted(zip(X, imp.importances_mean), key=lambda x: -x[1])[:12]
    md += ["", "## What the model relies on (permutation importance, latest model)", "",
           "| Feature | AUC drop when shuffled |", "|---|---|"] + [f"| {n} | {v:.4f} |" for n, v in top]

    latest = panel[panel.date == panel.date.max()].copy()
    latest = latest[latest.value >= latest.market.map(MIN_VALUE)]
    latest["p_beat_market"] = model.predict_proba(latest[X])[:, 1]
    latest.sort_values(["market", "p_beat_market"], ascending=[True, False])[
        ["market", "ticker", "date", "p_beat_market", "ret20", "mom12_1", "st_up", "weekly_up"]].to_csv(
        OUT / "latest_predictions.csv", index=False)
    md += ["", f"This week's ranking ({latest.date.max():%Y-%m-%d}): `latest_predictions.csv`. Top 5 per market:", ""]
    for mk in TOPK:
        t5 = latest[latest.market == mk].nlargest(5, "p_beat_market")
        md.append(f"- {mk}: " + ", ".join(f"{r.ticker.replace('.CA', '').replace('-USD', '')} ({r.p_beat_market:.0%})"
                                          for r in t5.itertuples()))
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
