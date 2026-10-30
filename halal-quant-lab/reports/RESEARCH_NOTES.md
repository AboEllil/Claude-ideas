# Research round: how professionals and "whales" do it

Four independent research personas were run in parallel (web research, cited
sources), then their ideas were tested in `run_v2.py`. Summary of what they said
and what our data showed.

## 1. The Institutional Quant (AQR, Two Sigma, DFA, Man, Bridgewater)
- Few, well-documented factors: momentum (12-1), quality/profitability,
  low risk, value, investment. Combined per stock into ONE z-scored composite,
  not as separate sleeves or voting rules.
- Portfolio construction is where much of the edge is kept: diversified
  holdings, inverse-volatility weights, name/sector caps, rebalance bands,
  turnover control ("craftsmanship alpha", AQR; DFA trades daily, uses
  momentum only to delay trades).
- Risk: volatility scaling (Barroso & Santa-Clara: momentum Sharpe 0.53 -> 0.97),
  slow trend following (Hurst-Ooi-Pedersen, century of evidence).
- Long-only keeps only 30-80% of the unconstrained edge (Clarke et al. 2002).
  Renaissance's long-biased fund targeted only +4-6%/yr over the S&P and often missed.
- **Realistic out-of-sample target, long-only unlevered large caps:** Sharpe
  0.5-0.7 over a full cycle (0.9-1.1 in 2012-2026), +1.5-3%/yr over the
  benchmark at best. A backtest Sharpe above ~1.3 is a red flag.

## 2. The Whale Tracker (what smart money footprints really predict)
Evidence-backed and buildable from daily prices:
- 52-week-high proximity (George & Hwang 2004), as a rank, not a breakout trigger.
- Overnight momentum (Lou, Polk & Skouras 2019): momentum is earned overnight.
- Earnings-reaction drift (Chan, Jegadeesh & Lakonishok 1996); contested in large caps since ~2006.
- Month-end "dash for cash" (Etula et al. 2020): funds sell days -8..-4, prices recover from -3.
- Earnings-announcement premium (Frazzini & Lamont) - needs the earnings calendar (blocked here).
Need SEC EDGAR (currently blocked): buybacks/share shrinkage, opportunistic insider cluster buys (Cohen-Malloy-Pomorski).
**Mostly myth for us:** dark-pool prints, unusual options flow, copying 13F
filings (45-day lag; "best ideas" did no better in a 1,500-fund study),
front-running index inclusions (7.4% -> 0.3%), OBV/"institutional VWAP levels".

## 3. The Academic (what survives out of sample)
- Anomaly returns fall ~26% out of sample and ~58% after publication (McLean & Pontiff).
  65-82% of 452 anomalies fail in value-weighted tests (Hou-Xue-Zhang).
- Survivors in large caps: momentum (esp. volatility-scaled and residual),
  low volatility, profitability/quality. Most mispricing is on the SHORT side
  (Stambaugh-Yu-Yuan), which halal investors cannot use.
- Portfolio-level vol targeting is hit-and-miss in real time (Cederburg et al. 2020).
  Trend filters cut 2000-02 and 2008 drawdowns but whipsaw in V-shaped crashes.
- A Sharpe difference of 0.1-0.2 over 14 years is statistically noise (SE ~0.27).

## 4. What our tests showed (`reports/v2/REPORT.md`)
1. **Stock selection added no reliable value inside this universe.** Every
   multi-factor variant had a Sharpe close to simply holding all 128 halal
   stocks equally, and the ablation signs flip between periods. The 128-stock
   list is today's survivors, which is a hard benchmark to beat - and a biased one.
2. **Risk overlays are the real improvement.** A slow trend filter (cut to 50%
   when the market is below its 10-month average AND down over 12 months) plus
   a volatility target roughly halved the worst drawdown in every test.
3. **On unbiased data (SPY 2006-today)** the overlay improved Sharpe 0.64 -> 0.75
   and max drawdown -55% -> -30%, at a cost of ~1.3%/yr return. On SPUS
   (2020-today, only V-shaped crashes) it reduced drawdown but also Sharpe.

## Bottom line
For a long-only halal investor, the professional-grade edge is not a magic
stock picker; it is (a) owning a broad, cheap, Shariah-screened portfolio and
(b) controlling crash risk with slow, partial risk overlays - accepting a bit
less return in strong bull markets for much smaller losses in bear markets.
Anyone promising 30-50%/yr with low drawdowns from indicators is overfitting
or selling something.

## 5. Debate round (optimist vs pessimist, impartial judge)
- Optimist: replace 0% cash with sukuk/gold, validate on survivorship-free
  Amana funds, dual momentum across halal asset classes, core + quality tilt.
- Pessimist: sukuk has only 6 years of history and fell with stocks in 2022;
  gold's Shariah status is debated and it has decade-long flat spells; ETF
  histories are too short for dual momentum; quality will likely fail like v2.
- Judge's realistic full-cycle targets for a long-only halal investor:
  buy-and-hold 8-11% CAGR, Sharpe 0.55-0.7, max DD -45 to -55%;
  with slow overlay 7-10%, Sharpe 0.65-0.85, max DD -25 to -35%.

## 6. Survivorship-free tests (`run_v3.py`, `reports/v3/REPORT.md`)
Pass/fail rules were fixed before running.
| Experiment | Result | Verdict |
|---|---|---|
| Overlay on Amana Growth (AMAGX), 0% cash | 12.2% -> 11.4% CAGR, Sharpe 0.73 -> 0.81, max DD -42% -> -23% | **PASS** (both halves) |
| Same overlay, freed weight in gold | 12.7% CAGR, Sharpe 0.84, max DD -31% | FAIL (DD cut 26% < 30% rule) - best return/risk, near miss |
| Static 70% equity / 15% gold / 15% sukuk | Sharpe 0.75 -> 0.85, max DD -42% -> -30% | FAIL (borderline) |
| Dual momentum across halal asset classes | Sharpe 0.73, below the static mix | FAIL |

## Final conclusion
The one result that survived every test - unbiased data, both halves of the
sample, a pre-registered rule - is: **hold a broad Shariah equity fund/ETF and
apply a slow, partial risk overlay** (cut to 50% only when the market is both
below its 10-month average AND down over 12 months; scale down when
volatility exceeds 20%). It roughly halves crash losses for under 1%/yr of
return. Stock picking, whale signals and asset rotation did not beat it.
