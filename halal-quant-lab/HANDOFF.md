# Handoff - Halal Quant Lab (2 Nov 2026)

## Goal
A halal trading signal system for US stocks, Egyptian stocks (EGX) and crypto that tells me what to
buy and sell each day - every asset Shariah-verified, every rule tested honestly - shown on a dashboard
with daily phone alerts.

## Current status
- Done:
  - Backtest lab (v1-v3, TradingView indicator ports, 24 community indicators, timeframes, exits,
    win-rate lab, signal lab, report strategies, ML forecaster, insider test) - all in `reports/`.
  - Best rule per market chosen and live: US 200-day trend, EGX swing trend stack, crypto arrow +
    squeeze + weekly. Take-profit (+2 ATR, sell half, stop to entry) and ML rank on every signal.
  - Shariah: full AAOIFI financial check (603 US pass) + confirmation from 8 certified Shariah funds'
    SEC holdings (307 "Confirmed"). Failed stocks removed and replaced (top-100 updated).
  - Dashboard "Halal Signal Board" live (630 assets), 4 scheduled tasks (daily US/all, daily EGX,
    quarterly Shariah refresh, top-20 monitor).
- In progress: fixing the EGX halal list - only 17 EGX stocks can be verified from Yahoo data.
- Next step: get the official EGX halal list (screenshot of my broker app's Sharia-compliant list or the
  EGX33 Shariah index constituents) and make it the EGX universe in `lab/egx.py` / `market_scanner.py`.

## Decisions already made (don't reopen)
- Halal constraints: long-only, no leverage, no shorting, no derivatives; strict Shariah check wins over
  funds' looser lists (stocks failing our check stay out even if a fund holds them).
- Daily timeframe; keep the default indicator settings (tuning overfit in tests).
- US = 200-day trend, EGX = swing trend stack, crypto = arrow + bright squeeze + weekly green; exit with
  half profit at +2 ATR and breakeven stop. ML score is a tie-breaker only.
- Free data only (Yahoo + SEC EDGAR); no paid QuantConnect or Zoya API.

## Key facts / constraints
- Repo AboEllil/Claude-ideas, branch `ccr-d992bbe8-x2j2mh` (not merged to main).
- Dashboard: https://claude.ai/artifact/Rc4NV26bDuMgsScydDX8op
- Scheduled tasks: trig_01KT4kmZohrrgTnorC6Mwcut (daily Mon-Fri 17:23 NY), trig_01EMUPDukBB2d68einbRLdBL
  (EGX Sun-Thu 17:13 Cairo), trig_012GnjrM2txdVhgEyLpPvN5N (quarterly 15 Feb/May/Aug/Nov),
  trig_01LkVb1eDFu29opxLAbKq2id (top-20 monitor, Mon-Fri 17:13 NY).
- Blocked domains: zoya.finance, nsave.com, musaffa.com, egx.com.eg, quiverquant.com.
- SEC needs `SEC_USER_AGENT="Name email"`; the email is stored only in the quarterly task.
- Costs used: US 0.05%/side, EGX 0.25%/side, crypto 0.10%/side.

## Files / code (all under halal-quant-lab/)
- `market_scanner.py` - daily scan: rules, verdicts, stops, take-profit, ML rank, Shariah label -> signals.csv
- `reports/signal_board/index.html` - dashboard page source; `signals.csv` - latest scan
- `lab/tv.py`, `lab/tv2.py` - Python ports of the TradingView indicators
- `lab/shariah.py` - AAOIFI financial check; `lab/shariah_funds.py` - Shariah fund holdings (SEC N-PORT)
- `lab/universe.py`, `lab/expand.py`, `lab/egx.py` - stock/crypto universes and business screens
- `run_ml_forecast.py` + `reports/ml/model.pkl` - ML forecaster (`--final` retrains the saved model)
- `run_signal_lab.py`, `run_winrate.py`, `run_evidence.py`, `run_exits.py`, `run_egx.py` - the tests
- `monitor.py`, `egx_scanner.py` - older single-market scanners; `top100.py` - top-100 halal list
- `pine/halal_confluence_strategy.pine` - TradingView strategy with alerts
- `reports/*/REPORT.md` - every test result; `../CLAUDE.md` - project knowledge for any new session

## Open questions
- Official EGX halal list (EGX33 or broker list) - needed from me.
- Two US-close notifications (daily refresh + top-20 monitor): keep both or turn one off?
- Merge the branch into main (open a pull request)?
- EGX results in USD terms are weak because of the pound's devaluation - keep part of savings in USD halal ETFs?
