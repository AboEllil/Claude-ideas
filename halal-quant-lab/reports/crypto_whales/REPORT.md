# Whale / crowd data for crypto - Coinbase premium and Fear & Greed (pre-registered)

Generated 2026-11-02. 674 closed crypto trades from March 2018. Coinbase premium from 2015-07-21, Fear & Greed from 2018-02-02. Days ON since 2018-03: PREMIUM 35%, NO-GREED 90%. Funding rates (Binance refuses this server's location), ETF flows (bot check) and wallet flows (paid) could not be tested.

## Filter: Coinbase premium positive (7-day average)

| Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| 2018-2020 | All | 126 | 66% | +28.7% | 6.33 | 44.5% | 1.47 | -22% |
| 2018-2020 | Regime ON | 43 | 79% | +66.6% | 23.27 | 20.1% | 1.14 | -11% |
| 2018-2020 | Regime OFF | 83 | 59% | +9.1% | 2.37 | 22.6% | 1.09 | -20% |
| 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| 2021-today | Regime ON | 269 | 56% | +11.1% | 2.70 | 20.5% | 0.91 | -27% |
| 2021-today | Regime OFF | 279 | 53% | +4.5% | 1.61 | 6.3% | 0.39 | -40% |

**Verdict: FAIL**

## Filter: Fear & Greed below 75 (no extreme greed)

| Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| 2018-2020 | All | 126 | 66% | +28.7% | 6.33 | 44.5% | 1.47 | -22% |
| 2018-2020 | Regime ON | 103 | 63% | +16.5% | 3.72 | 37.5% | 1.40 | -22% |
| 2018-2020 | Regime OFF | 23 | 78% | +83.4% | 37.24 | 5.1% | 0.55 | -10% |
| 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| 2021-today | Regime ON | 489 | 52% | +4.6% | 1.62 | 11.3% | 0.51 | -49% |
| 2021-today | Regime OFF | 59 | 73% | +34.0% | 11.32 | 14.5% | 1.23 | -15% |

**Verdict: FAIL**

## Timing: hold Bitcoin only while the regime is ON (else cash)

| Period | Strategy | CAGR | Sharpe | Max DD | Time invested |
|---|---|---|---|---|---|
| 2018-2020 | Buy & hold | 43.5% | 0.88 | -72% | 100% |
| 2018-2020 | PREMIUM ON | 57.3% | 1.54 | -35% | 19% |
| 2021-today | Buy & hold | 18.5% | 0.58 | -77% | 100% |
| 2021-today | PREMIUM ON | 29.4% | 0.91 | -47% | 43% |
| 2018-2020 | NO-GREED ON | 4.6% | 0.40 | -72% | 89% |
| 2021-today | NO-GREED ON | 7.2% | 0.39 | -76% | 90% |

## Verdicts (pre-registered)

| Test | Result |
|---|---|
| PREMIUM filter | **FAIL** |
| NO-GREED filter | **FAIL** |
| PREMIUM timing (BTC) | **PASS** |
| NO-GREED timing (BTC) | **FAIL** |

Latest: Coinbase premium (7-day) -0.101%; Fear & Greed 37.

## Reading the result (plain language)

- PASSED: holding Bitcoin only while US buyers on Coinbase pay a premium beat buy & hold in both periods
  (2018-2020: 57% a year, Sharpe 1.54, worst drop -35% vs 43%, 0.88, -72%; 2021-today: 29%, 0.91, -47% vs
  19%, 0.58, -77%), while invested only 19% / 43% of the time. Shown on the dashboard as "Bitcoin timing".
- As a filter on crypto signals the premium made trades better (79% vs 66% won in 2018-2020) but fewer, so the
  Sharpe did not rise in 2018-2020: FAIL by the rule, same pattern as Fed liquidity.
- Fear & Greed: the idea "avoid extreme greed" was WRONG for this trend-following system - signals in extreme greed
  won more often (73-78%). Not used as a filter.
- One test of several passed; the result is strong but should still be tracked forward.
