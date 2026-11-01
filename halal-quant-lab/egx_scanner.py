"""EGX daily scanner: fresh green arrows across all halal EGX stocks (replaces the manual chart scan).

    python egx_scanner.py

Run after the EGX close (Sunday-Thursday, 14:30 Cairo). Best tested rule (reports/egx/REPORT.md):
  BUY   green arrow today (ML Adaptive SuperTrend turns bullish) AND Squeeze momentum > 0
        AND Lorentzian bullish, with >= EGP 1M daily traded value
  SELL  when the SuperTrend turns red (hold the whole trend - selling after 3-5 days tested far worse)
Also lists arrows that miss a confirmation (weaker) and every stock whose SuperTrend turned red today.
Writes reports/egx/scan_latest.md. Not financial advice; verify Shariah compliance (EGX33 Shariah index).
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from lab import tv
from lab.egx import halal_egx
from run_egx import MIN_VALUE, clean

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "egx"


def scan(args):
    tk, df = args
    df = clean(df.dropna(subset=["Open", "High", "Low", "Close"]))
    if len(df) < 300:
        return None
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    st = tv.adaptive_supertrend(o, h, l, c)[0]
    _, mom = tv.squeeze(o, h, l, c)
    pred = tv.lorentzian(o, h, l, c)[1]
    value = float((df.Close * df.Volume.fillna(0)).rolling(20).median().iloc[-1])
    run = 0
    for x in st[::-1]:
        if x != st[-1]:
            break
        run += 1
    return {"ticker": tk.replace(".CA", ""), "date": df.index[-1], "close": c[-1],
            "trend": "green" if st[-1] == 1 else "red", "days_in_trend": run,
            "arrow_today": bool(st[-1] == 1 and st[-2] == 0), "red_today": bool(st[-1] == 0 and st[-2] == 1),
            "squeeze_mom": float(mom[-1]), "lorentzian": float(pred[-1]), "value_egp": value}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tks = [t + ".CA" for t in halal_egx()]
    raw = yf.download(tks, period="3y", auto_adjust=True, progress=False, threads=True, group_by="column")
    jobs = [(t, pd.DataFrame({f: raw[f][t] for f in ("Open", "High", "Low", "Close", "Volume")}))
            for t in tks if t in raw["Close"] and raw["Close"][t].notna().sum() > 300]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        rows = [r for r in ex.map(scan, jobs) if r]
    df = pd.DataFrame(rows)
    day = df.date.max()
    df = df[df.date == day]                                 # stocks that traded on the latest session
    liquid = df.value_egp >= MIN_VALUE
    strong = df[df.arrow_today & liquid & (df.squeeze_mom > 0) & (df.lorentzian > 0)]
    weak = df[df.arrow_today & ~df.index.isin(strong.index)]
    red = df[df.red_today]
    green = df[(df.trend == "green") & liquid].sort_values("days_in_trend")

    def table(d, cols):
        if d.empty:
            return ["None today."]
        head = "| " + " | ".join(cols) + " |"
        out = [head, "|" + "---|" * len(cols)]
        for _, r in d.iterrows():
            out.append(f"| **{r.ticker}** | {r.close:.2f} | {'+' if r.squeeze_mom > 0 else '-'} | "
                       f"{'bullish' if r.lorentzian > 0 else 'bearish' if r.lorentzian < 0 else 'neutral'} | "
                       f"{r.value_egp / 1e6:.1f}M | {r.days_in_trend} |")
        return out
    cols = ["Stock", "Close (EGP)", "Squeeze", "Lorentzian", "Daily value", "Days in trend"]
    md = [f"# EGX halal scanner - session of {day:%A %d %b %Y}", "",
          "Rule tested best on 2016-2026: buy the green arrow only when Squeeze momentum is green and Lorentzian is "
          "bullish, then **hold until the SuperTrend turns red**.", "",
          "## STRONG BUY - arrow + squeeze + Lorentzian (liquid)", *table(strong, cols), "",
          "## Weaker arrows - missing a confirmation or illiquid", *table(weak, cols), "",
          "## SELL if you hold them - SuperTrend turned red today", *table(red, cols), "",
          f"## Still green ({len(green)} liquid stocks, newest trends first)", *table(green.head(25), cols), "",
          "> Not financial advice. Verify Shariah compliance (EGX33 Shariah index) before buying."]
    (OUT / "scan_latest.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    s = ", ".join(strong.ticker) or "none"
    print(f"\nEGX scan {day:%d %b}: STRONG BUY {s} | SELL (red today) {', '.join(red.ticker) or 'none'}")


if __name__ == "__main__":
    main()
