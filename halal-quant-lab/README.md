# Halal Quant Lab

A Python research lab that screens US stocks for Shariah compliance, builds
trading strategies from many concepts at once, backtests thousands of variants
on 20+ years of daily data, and measures them **honestly** with walk-forward
testing. Free data (Yahoo Finance), no paid platform needed.

**Latest results:** [reports/v3/REPORT.md](reports/v3/REPORT.md) (v3 survivorship-free, final) ·
[reports/v2/REPORT.md](reports/v2/REPORT.md) (v2 multi-factor) ·
[reports/RESEARCH_NOTES.md](reports/RESEARCH_NOTES.md) (what institutions do, what we learned) ·
[reports/REPORT.md](reports/REPORT.md) (v1 random search, superseded)

`run_v3.py` and `run_v2.py` are the current pipelines. v1 (`run_research.py`) is kept for reference; a code
audit found its regime-to-cash switch whipsaws, its swing dip entries can collide with
short-SMA exits, and its `exposure` stat counts days with P&L rather than capital invested.

## Quick start
```bash
pip install -r requirements.txt
python run_v2.py                                         # v2 multi-factor, pre-registered (~2 min)
python run_v3.py                                         # v3 survivorship-free halal funds/ETFs (~1 min)
python run_research.py                                   # 400 + 400 configs, ~10 min
python run_research.py --n-rotation 1000 --n-swing 1000  # bigger search
python run_research.py --refresh                         # re-download data
```

## How it works

| Step | File | What it does |
|---|---|---|
| 1. Halal screen | `lab/universe.py` | AAOIFI-style: excludes banks/insurance/lending, alcohol, tobacco, gambling, pork, entertainment, real estate; requires debt/market cap < 30% and cash/market cap < 30% |
| 2. Data | `lab/data.py` | Adjusted daily OHLCV from 2005, cached in `data/` |
| 3. Indicators | `lab/indicators.py` | SMA/EMA, RSI, ATR, ADX, Bollinger, Donchian, ROC, 12-1 momentum, OBV, realised volatility, cross-sectional ranks |
| 4. Concepts | `lab/signals.py` | Trend, trend strength, momentum, relative strength vs SPY, RSI pullback, Bollinger dip, breakout, volume accumulation, low volatility, market regime (SPY trend + VIX) |
| 5. Engines | `lab/engine.py` | **Rotation**: rank the universe on a multi-factor score, hold the top N, rebalance weekly/monthly. **Swing**: enter when a weighted vote of concepts passes a threshold; exit on ATR trailing stop, time stop or trend break |
| 6. Search | `lab/search.py` | Random search over concept weights and parameters; walk-forward selection |
| 7. Metrics | `lab/metrics.py` | CAGR, Sharpe, Sortino, drawdown, Calmar, win rate, **Deflated Sharpe Ratio** |

### Guarding against fooling ourselves
- **No look-ahead**: signals use the close of day t; trades happen on day t+1.
  Tested with "cheating" canary signals that peek at the future - they produce
  absurd returns, while honest signals do not.
- **Costs**: 5 bps per side by default, plus a 3x cost stress test.
- **Walk-forward**: each year is traded by configs chosen only from the
  previous 5 years. This is the number to trust; the in-sample leaderboard is
  shown only to illustrate overfitting.
- **Deflated Sharpe Ratio**: corrects the best Sharpe for the number of configs tried.
- **Survivorship bias warning**: the universe is today's large caps, so past
  results are flattered. The equal-weight halal universe benchmark carries the
  same bias - beating *it*, not just SPY, is what matters.

## Limitations
- The halal screen is approximate (current market cap instead of a 36-month
  average; no non-permissible income check). Verify holdings with a dedicated
  Shariah screener or the SPUS / HLAL holdings before investing. If a stock
  earns any non-permissible income, purification (donating that share of
  dividends) still applies.
- Daily bars only; no intraday execution modelling.
- Not financial advice. Paper trade before risking money.
