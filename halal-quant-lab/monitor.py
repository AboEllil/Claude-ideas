"""Daily buy/sell monitor for the Halal Confluence strategy (variant A).

    python monitor.py                         # top 20 halal stocks, $10,000 capital
    python monitor.py --capital 25000 --top 30
    python monitor.py --tickers AAPL MSFT NVDA

Run it after the US close (data for the day must be final). It downloads fresh daily data,
applies exactly the backtested rules (lab/tv.py confluence + lab/risk_engine.py: 1% risk per
trade, 3 x ATR14 chandelier stop, max 20% per stock) and prints orders for the NEXT open:

  BUY   new signal today - shares for your capital, initial stop
  SELL  trailing stop hit, or trend/structure turned bearish
  HOLD  open positions with today's (raised) trailing stop

Positions: by default it tracks the strategy's own model portfolio (replayed from 2009).
To track YOUR real positions, create my_positions.json next to this file:
  {"AAPL": {"shares": 10, "entry_price": 230.5, "entry_date": "2026-09-15"}}
Then HOLD/SELL use your positions and BUY lists signals for stocks you don't own.

Writes reports/monitor/latest.md, latest.txt (one-line summary for notifications) and a dated copy.
Not financial advice. Verify Shariah compliance of each stock before buying.
"""
import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lab import risk_engine
from lab.data import load_prices
from run_tv import market_ok
from run_tv_rotation import signals

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "monitor"
RISK, K, MAX_W = 0.01, 3.0, 0.20


def atr14(H, L, C):
    tr = np.fmax(H - L, np.fmax((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    return tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=10_000)
    ap.add_argument("--top", type=int, default=20, help="use the top N of reports/top100_halal.csv")
    ap.add_argument("--tickers", nargs="*")
    ap.add_argument("--positions", default=str(ROOT / "my_positions.json"))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    tickers = a.tickers or list(pd.read_csv(ROOT / "reports" / "top100_halal.csv", index_col=0).index[:a.top])
    px = load_prices(tickers, refresh=True, cache_name="monitor_prices.pkl")
    tickers = [t for t in tickers if px["Close"][t].notna().sum() > 300]
    mkt = market_ok(px["Close"]["SPY"].ffill())
    jobs = [(t, pd.DataFrame({f: px[f][t] for f in ("Open", "High", "Low", "Close")}), mkt) for t in tickers]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        sig = dict(ex.map(signals, jobs))

    sl = slice("2009-01-01", None)
    O, H, L, C, V = (px[f][tickers].loc[sl] for f in ("Open", "High", "Low", "Close", "Volume"))
    on = pd.DataFrame({t: sig[t]["cf_nm"] for t in tickers}).reindex(C.index).fillna(0)
    st = pd.DataFrame({t: sig[t]["st"] for t in tickers}).reindex(C.index).fillna(0)
    *_, state = risk_engine.run(O, H, L, C, V, on, risk=RISK, k=K, max_weight=MAX_W, return_state=True)
    day = state["date"]
    atr = atr14(H, L, C)

    mine_path = Path(a.positions)
    mine = json.loads(mine_path.read_text()) if mine_path.exists() else None
    if mine:
        # Your real positions: chandelier stop from the highest close since your entry.
        holds, sells = [], []
        for t, p in mine.items():
            if t not in C:
                continue
            since = C[t].loc[p.get("entry_date", C.index[0]):]
            stop = since.cummax().iloc[-1] - K * atr[t].iloc[-1]
            last = C[t].iloc[-1]
            row = {"ticker": t, "last_close": last, "stop": stop, "entry_price": p["entry_price"],
                   "gain": last / p["entry_price"] - 1, "shares": p["shares"]}
            if last < stop:
                sells.append({**row, "reason": "trailing stop hit"})
            elif not on[t].iloc[-1]:
                sells.append({**row, "reason": "trend/structure turned bearish"})
            else:
                holds.append(row)
        buys = [b for b in state["buys"] if b["ticker"] not in mine]
        mode = f"your positions ({mine_path.name})"
    else:
        holds, sells, buys = state["holdings"], state["sells"], state["buys"]
        mode = "model portfolio (replayed from 2009)"

    lines = [f"# Halal monitor - signals at the close of {day:%A %d %b %Y}", "",
             f"Orders are for the **next market open**. Capital ${a.capital:,.0f}, risk {RISK:.0%} per trade, "
             f"stop {K:g} x ATR14, max {MAX_W:.0%} per stock. Tracking: {mode}.", ""]
    mkt_ok = bool(mkt.reindex(C.index).ffill().iloc[-1])
    lines += [f"Market regime (SPY trend): **{'healthy' if mkt_ok else 'bearish - be cautious'}**", ""]

    lines += ["## BUY", ""]
    if buys:
        lines += ["| Stock | Last close | Shares | Amount | Initial stop | Risk if stopped |", "|---|---|---|---|---|---|"]
        for b in buys:
            amt = a.capital * b["weight"]
            sh = int(amt // b["last_close"])
            lines.append(f"| **{b['ticker']}** | ${b['last_close']:.2f} | {sh} | ${sh * b['last_close']:,.0f} | "
                         f"${b['stop']:.2f} | ${sh * (b['last_close'] - b['stop']):,.0f} |")
    else:
        lines.append("No new buy signals today.")
    lines += ["", "## SELL", ""]
    if sells:
        lines += ["| Stock | Last close | Reason |", "|---|---|---|"]
        lines += [f"| **{s['ticker']}** | ${s['last_close']:.2f} | {s['reason']} |" for s in sells]
    else:
        lines.append("No sell signals today.")
    lines += ["", "## HOLD (move your stop to the new level)", ""]
    if holds:
        lines += ["| Stock | Last close | Trailing stop | Distance to stop | Gain since entry |", "|---|---|---|---|---|"]
        for h in sorted(holds, key=lambda x: x["ticker"]):
            lines.append(f"| {h['ticker']} | ${h['last_close']:.2f} | ${h['stop']:.2f} | "
                         f"{h['last_close'] / h['stop'] - 1:.1%} | {h['gain']:+.1%} |")
    else:
        lines.append("No open positions.")
    lines += ["", "## Watchlist status", "", "| Stock | Close | SuperTrend | Strategy signal |", "|---|---|---|---|"]
    for t in tickers:
        lines.append(f"| {t} | ${C[t].iloc[-1]:.2f} | {'bullish' if st[t].iloc[-1] else 'bearish'} | "
                     f"{'ON' if on[t].iloc[-1] else 'off'} |")
    lines += ["", "> Not financial advice. Verify Shariah compliance before buying; purify dividends."]

    def buy_txt(b):
        shares = int(a.capital * b["weight"] // b["last_close"])
        return f"{b['ticker']} {shares}sh stop {b['stop']:.2f}"

    buy_list = ", ".join(buy_txt(b) for b in buys) or "none"
    sell_list = ", ".join(s["ticker"] for s in sells) or "none"
    summary = f"Halal monitor {day:%d %b}: BUY {buy_list} | SELL {sell_list} | holding {len(holds)}"
    md = "\n".join(lines) + "\n"
    (OUT / "latest.md").write_text(md)
    (OUT / f"{day:%Y-%m-%d}.md").write_text(md)
    (OUT / "latest.txt").write_text(summary + "\n")
    print(md)
    print(summary)


if __name__ == "__main__":
    main()
