# Project knowledge: Halal Quant Lab (read this first)

Owner: Mo (AboEllil). Goal: a **halal (Shariah-compliant) trading signal system** for US stocks, Egyptian
stocks (EGX) and crypto - tested honestly on history, shown on a dashboard, with daily phone alerts.
All work lives in `halal-quant-lab/`. Active branch: `ccr-d992bbe8-x2j2mh` (not merged to main).

## Hard rules (the user's requirements)
- **Halal only**: long-only, no leverage/margin, no short selling, no options/futures, no interest.
  Every stock shown must pass the Shariah check; when something fails, replace it with a compliant one.
- **Honest testing**: no look-ahead (signals at the close, trades at the next bar), costs included,
  choose rules on 2016-2020 (train) and judge on 2021-today (test), pre-register pass/fail rules,
  report failures plainly. Never present hindsight (e.g. TradingView position-tool targets) as results.
- **Realistic expectations**: 25-50%/month is not achievable; long-only edge is mainly smaller drawdowns.
- Daily timeframe is the user's choice (1h/4h/weekly were tested; daily is the most reliable).
- Plain-language answers; the user trades on TradingView and an EGX broker app (manual orders).

## The user's own system (TradingView, daily)
Entry: **AlgoAlpha ML Adaptive SuperTrend green arrow** + **LazyBear Squeeze Momentum bright green**
(positive and rising); a **jdehorty Lorentzian Classification green arrow** (last 5 days) = high
confidence. Exit: **AlgoAlpha red arrow**. Defaults (AlgoAlpha ATR 10 / factor 3 / 100 training,
Squeeze 20 / 1.5) are best - tuning settings overfits.

## What the tests proved (see halal-quant-lab/reports/*)
| Market | Best rule (dashboard uses it) | TEST 2021-today CAGR / Sharpe / maxDD | vs user's system |
|---|---|---|---|
| US | 200-day trend: hold while close > SMA200 | 28.4% / 1.37 / -24% | 14.2% / 0.76 / -27% |
| EGX | Swing stack: EMA50>EMA200, ADX>20, close > 20-day high; exit 3xATR trail or < EMA50 | 39.8% / 1.61 / -30% | 38.0% / 1.58 / -34% |
| Crypto | User's arrow + bright squeeze + **weekly SuperTrend green**, exit red arrow | 30% / 1.13 / -30% | 57% / 1.15 / -60% |
- Win rate: selling **half at +2 ATR and moving the stop to entry** raises win rate ~12-16 points
  (US 41->53%, EGX 47->62%, crypto 38->54%). Weekly-trend filter is the best entry filter.
- Did NOT help: order-block "3 of 4" confluence, RSI(2) pullback (high win rate, loses money),
  Ramadan effect, market/breadth regime on EGX, insider buying (SEC Form 4), tighter ATR stops,
  vol-scaled risk, most TradingView community indicators (24 tested; none beat buy & hold).
- ML signal filter (run_ml_signals.py, Nov 2026): GBM + pattern-twin kNN on 57 features incl. 30-day price shape,
  16k trades, walk-forward: FAILED its pre-registered rule (0 of 6 groups). No reliable win-rate gain; small
  per-trade edge on EGX only. Weekly-trend filter is as good and simpler. Not used on the dashboard.
- ML forecaster (gradient boosting, walk-forward, yearly retrain, 30-day embargo): AUC 0.53-0.55
  every year - small steady edge; used only as a **0-100 ranking** (tie-breaker), not a signal.
- Buy & hold of halal stocks beat every signal on raw return in 2021-2026 (bull market).

## Shariah screening (how "halal" is decided)
1. Business screen (lab/universe.py + market_scanner.py): no conventional finance/insurance, alcohol,
   tobacco, gambling, pork, entertainment, hotels/cruise lines, weapons (defense industry for mid caps),
   alcohol-heavy restaurant chains, convenience stores.
2. **Financial check** (lab/shariah.py, AAOIFI): debt/mcap < 30%, cash+ST investments/mcap < 30%,
   interest income/revenue < 5%; missing data = excluded. Islamic banks (ADIB, FAIT, FAITA, SAUD) pass
   on their own Sharia board. Output: reports/universe/shariah_check.csv (603 US pass, 17 EGX pass).
3. **Fund confirmation** (lab/shariah_funds.py): full holdings of certified Shariah funds from SEC N-PORT
   (SPUS, HLAL, SPTE, MNZL, AMAGX, AMANX, IMANX, ADJEX) -> "Confirmed" vs "Screened" label.
   Needs env `SEC_USER_AGENT="Name email"` (SEC requirement).
- Zoya / NSave / Musaffa / egx.com.eg are blocked by the environment network policy; the user has no
  Zoya API. Crypto: excludes stablecoins, wrapped/staked, meme, interest/yield and margin-exchange
  tokens; marked "debated among scholars". Yahoo EGX fundamentals are poor (93 EGX unverified).

## Data and environment
- Prices: Yahoo Finance via yfinance (query1/query2.finance.yahoo.com, fc.yahoo.com allowed).
  EGX tickers use `.CA`; crypto `-USD`. SEC EDGAR (data.sec.gov, www.sec.gov) reachable.
- Python libs: pandas, numpy, yfinance, matplotlib, numba, scikit-learn, requests, hijri-converter.
- Local cache `halal-quant-lab/data/` is gitignored; anything a fresh scheduled session needs must be
  committed under `reports/` (universe lists, model.pkl).

## Live pieces
- Dashboard "Halal Signal Board": https://claude.ai/artifact/Rc4NV26bDuMgsScydDX8op (Dashboard type;
  page = store doc files/index.html, data = dataset "signals" pointing at an uploaded signals.csv blob).
  Source copy: halal-quant-lab/reports/signal_board/index.html. Private until shared.
- Scheduled tasks (fresh session each run, push notifications):
  - `trig_01KT4kmZohrrgTnorC6Mwcut` Halal Signal Board daily refresh - Mon-Fri 17:23 New York
    (retrains ML model in the first 7 days of each month)
  - `trig_01EMUPDukBB2d68einbRLdBL` EGX after-close signals - Sun-Thu 17:13 Cairo
  - `trig_012GnjrM2txdVhgEyLpPvN5N` Quarterly Shariah check refresh - 15 Feb/May/Aug/Nov 10:37 Cairo
  - `trig_01LkVb1eDFu29opxLAbKq2id` Halal daily buy/sell monitor (top-20 model portfolio) - Mon-Fri 17:13 NY

## Gotchas learned
- `pkill -f name` kills the very command that runs it; pipe through grep buffers output.
- yfinance `dividendYield` is already in %; `info` for EGX lacks sector/debt (use statements).
- Crypto names from Yahoo end with " USD" - strip before stablecoin filters.
- Pandas index from yfinance hourly data is in seconds, not ns.
- Treat TradingView chart "accuracy" with care: signals match ours exactly; targets drawn later are hindsight.
