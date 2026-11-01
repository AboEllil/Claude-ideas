# Strategies from the research report vs the user's system

Generated 2026-11-01. Same assets and costs as the signal lab; max 10% per position. TRAIN 2016-2020 / TEST 2021-today.

## US (238 assets)

| Strategy | TEST win | TEST avg trade | TEST PF | TEST CAGR | TEST Sharpe | TEST max DD | TRAIN PF | TRAIN CAGR | TRAIN Sharpe | TRAIN max DD | TEST trades/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U0 your system | 41% | +2.1% | 1.43 | 14.2% | 0.76 | -27% | 2.01 | 18.4% | 1.02 | -28% | 493 |
| U1 your system + weekly green | 42% | +2.5% | 1.58 | 19.6% | 1.01 | -27% | 1.50 | 6.4% | 0.49 | -25% | 234 |
| U2 U1 + market & breadth regime | 40% | +2.2% | 1.50 | 16.2% | 0.96 | -18% | 1.51 | 8.3% | 0.66 | -18% | 176 |
| S1 200-day rule | 20% | +7.0% | 3.47 | 28.4% | 1.37 | -24% | 2.92 | 24.3% | 1.14 | -36% | 938 |
| S2 swing trend stack (EMA, ADX, Donchian, 3xATR) | 39% | +2.2% | 1.55 | 13.1% | 0.74 | -31% | 1.63 | 15.0% | 0.92 | -25% | 433 |
| S3 RSI(2) pullback | 66% | +0.5% | 1.39 | 7.2% | 0.42 | -35% | 1.18 | 12.4% | 0.67 | -41% | 1447 |
| S4 momentum rotation (monthly) | 48% | +5.5% | 1.78 | 27.9% | 0.80 | -46% | 3.40 | 27.6% | 1.10 | -33% | 38 |
| Buy & hold (equal weight) | | | | 28.3% | 1.27 | -26% | | 28.7% | 1.21 | -39% | |

## EGX (137 assets)

| Strategy | TEST win | TEST avg trade | TEST PF | TEST CAGR | TEST Sharpe | TEST max DD | TRAIN PF | TRAIN CAGR | TRAIN Sharpe | TRAIN max DD | TEST trades/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U0 your system | 47% | +8.8% | 2.92 | 38.0% | 1.58 | -34% | 1.53 | 6.4% | 0.44 | -37% | 166 |
| U1 your system + weekly green | 51% | +9.8% | 3.43 | 37.3% | 1.71 | -21% | 2.24 | 9.6% | 0.83 | -18% | 83 |
| U2 U1 + market & breadth regime | 50% | +7.3% | 2.80 | 19.8% | 1.13 | -29% | 2.64 | 8.9% | 0.84 | -13% | 67 |
| S1 200-day rule | 21% | +8.8% | 3.67 | 37.1% | 1.78 | -35% | 1.62 | 12.9% | 0.85 | -52% | 413 |
| S2 swing trend stack (EMA, ADX, Donchian, 3xATR) | 43% | +8.1% | 2.69 | 39.8% | 1.61 | -30% | 2.05 | 21.4% | 1.34 | -23% | 202 |
| S3 RSI(2) pullback | 57% | -0.4% | 0.81 | -20.8% | -0.86 | -76% | 0.56 | -10.3% | -0.69 | -50% | 770 |
| S4 momentum rotation (monthly) | 53% | +6.6% | 1.86 | 18.7% | 0.84 | -40% | 2.14 | 8.7% | 0.62 | -27% | 30 |
| Buy & hold (equal weight) | | | | 43.8% | 1.97 | -34% | | 20.1% | 1.20 | -44% | |

### Ramadan effect (equal-weight halal EGX index, 2010-today)

Average daily return in Ramadan -0.016% vs +0.111% on other days (t-stat -1.61); Ramadan beat the rest of the year in 4 of 13 years.

## Crypto (38 assets)

| Strategy | TEST win | TEST avg trade | TEST PF | TEST CAGR | TEST Sharpe | TEST max DD | TRAIN PF | TRAIN CAGR | TRAIN Sharpe | TRAIN max DD | TEST trades/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| U0 your system | 41% | +17.2% | 3.12 | 57.1% | 1.15 | -60% | 4.06 | 49.9% | 1.36 | -40% | 87 |
| U1 your system + weekly green | 49% | +29.7% | 5.03 | 30.2% | 1.13 | -30% | 16.53 | 14.0% | 1.45 | -9% | 17 |
| U2 U1 + market & breadth regime | 62% | +35.3% | 7.67 | 24.9% | 1.07 | -24% | 19.21 | 10.2% | 1.25 | -8% | 10 |
| S1 200-day rule | 15% | +911.5% | 170.63 | 145.0% | 0.52 | -67% | 5.40 | 41.1% | 1.06 | -55% | 178 |
| S2 swing trend stack (EMA, ADX, Donchian, 3xATR) | 37% | +13.4% | 2.72 | 57.7% | 1.30 | -37% | 3.65 | 28.5% | 1.24 | -23% | 58 |
| S3 RSI(2) pullback | 62% | +0.9% | 1.36 | 8.5% | 0.41 | -46% | 1.11 | -1.0% | 0.06 | -36% | 199 |
| S4 momentum rotation (monthly) | 43% | +24.6% | 3.30 | 18.8% | 0.70 | -31% | 12.17 | 21.8% | 0.99 | -41% | 16 |
| Buy & hold (equal weight) | | | | 154.9% | 0.72 | -77% | | 81.1% | 1.18 | -87% | |

## Conclusions
- **US: the plain 200-day rule (S1) beat the user's system in both periods** (TEST Sharpe 1.37 vs 0.76, CAGR
  28.4% vs 14.2%, max DD -24% vs -27%; TRAIN Sharpe 1.14 vs 1.02) and roughly matched buy & hold with a smaller
  drawdown. It holds every trending stock at once (up to 10% each), so it behaves like a trend-filtered index.
  Its per-trade win rate is low (20%) because price crosses the average often; the profit comes from long trends.
- **EGX: the swing trend stack (S2: EMA50>EMA200, ADX>20, 20-day breakout, 3xATR trail) was the most consistent**:
  TEST 39.8% / Sharpe 1.61 / -30%, TRAIN 21.4% / 1.34 / -23% - better than the user's system in both periods and
  better than buy & hold in TRAIN. The user's system + weekly filter (U1) was also solid.
- **RSI(2) pullback has a high win rate (57-66%) but loses money** (EGX -20.8%/yr): a high win rate alone is a trap.
- The market + breadth regime filter (U2) cut drawdowns in US and crypto but cost a lot of return on EGX.
- Monthly momentum rotation (S4) was weaker than the simple trend rules here.
- **Ramadan effect on EGX: not found** (Ramadan days averaged -0.016% vs +0.111%; Ramadan was better in 4 of 13 years).
- Crypto equal-weight numbers are dominated by a few coins that rose many-fold after listing; read them with care.
