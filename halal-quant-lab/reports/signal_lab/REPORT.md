# Signal lab: more accurate AND more profitable signals

Generated 2026-11-01. Exit for every version: AlgoAlpha red arrow. Trades at the next close, costs per side US 0.05% / EGX 0.25% / crypto 0.10%, max 10% per position, liquid assets only. **Choices are made on TRAIN (2016-2020); TEST (2021-today) is the honest result.**

Columns: trades per year, win rate, average trade, profit factor (gains / losses), whipsaw (losing trades closed within 5 days), portfolio CAGR, Sharpe, max drawdown.

## US (238 assets)

V10 uses the two filters with the best TRAIN Sharpe gain: **sqz + rs**.

| Version (TEST 2021-today) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 493 | 41% | +2.1% | 1.43 | 5% | 14.2% | 0.76 | -27% |
| V1 + Lorentzian arrow | 289 | 41% | +2.1% | 1.44 | 4% | 13.6% | 0.73 | -24% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 487 | 41% | +2.2% | 1.46 | 4% | 14.5% | 0.77 | -28% |
| V3 + order-block retest | 31 | 37% | +0.4% | 1.08 | 7% | -0.3% | 0.02 | -28% |
| V4 + market uptrend | 391 | 40% | +2.0% | 1.41 | 5% | 11.5% | 0.70 | -25% |
| V5 + stronger than market | 247 | 42% | +2.6% | 1.53 | 6% | 14.8% | 0.75 | -29% |
| V6 + volume surge | 127 | 41% | +2.5% | 1.47 | 6% | 8.7% | 0.50 | -39% |
| V7 + weekly trend green | 234 | 42% | +2.5% | 1.58 | 6% | 19.6% | 1.01 | -27% |
| V8 + real squeeze + ADX>20 | 110 | 39% | +2.0% | 1.40 | 4% | 8.2% | 0.50 | -33% |
| V9 + buy the pullback | 221 | 30% | +2.4% | 1.63 | 32% | 19.7% | 0.94 | -31% |
| V10 V0 + best 2 filters (from train) | 48 | 40% | +2.9% | 1.61 | 5% | 6.8% | 0.50 | -25% |
| Buy & hold (equal weight) | | | | | | 28.3% | 1.27 | -26% |

Same versions in TRAIN (2016-2020), for consistency:

| Version (TRAIN) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 355 | 46% | +3.5% | 2.01 | 6% | 18.4% | 1.02 | -28% |
| V1 + Lorentzian arrow | 209 | 45% | +3.1% | 1.86 | 6% | 17.4% | 0.99 | -26% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 353 | 46% | +3.3% | 1.94 | 6% | 16.2% | 0.92 | -31% |
| V3 + order-block retest | 28 | 42% | +3.0% | 1.94 | 5% | 6.6% | 0.78 | -14% |
| V4 + market uptrend | 288 | 42% | +2.2% | 1.59 | 5% | 9.1% | 0.62 | -26% |
| V5 + stronger than market | 187 | 44% | +3.2% | 1.93 | 6% | 18.5% | 1.06 | -26% |
| V6 + volume surge | 92 | 46% | +3.0% | 1.78 | 5% | 12.0% | 0.71 | -28% |
| V7 + weekly trend green | 165 | 43% | +1.8% | 1.50 | 4% | 6.4% | 0.49 | -25% |
| V8 + real squeeze + ADX>20 | 86 | 45% | +4.7% | 2.15 | 7% | 21.6% | 1.18 | -25% |
| V9 + buy the pullback | 135 | 35% | +2.4% | 1.82 | 32% | 20.6% | 1.11 | -24% |
| V10 V0 + best 2 filters (from train) | 44 | 44% | +3.9% | 1.88 | 9% | 9.6% | 0.70 | -30% |

### Settings sweep (V0 rule), chosen on TRAIN Sharpe

| Settings (factor / ATR / squeeze) | TRAIN Sharpe | TEST trades/yr | TEST win | TEST PF | TEST CAGR | TEST Sharpe | TEST Max DD |
|---|---|---|---|---|---|---|---|
| 3 / 10 / 20 (default) | 1.02 | 493 | 41% | 1.43 | 14.2% | 0.76 | -27% |
| 2 / 7 / 14 **(best in train)** | 1.20 | 730 | 39% | 1.29 | 11.4% | 0.61 | -37% |
| 2 / 10 / 14 | 1.19 | 732 | 39% | 1.30 | 14.5% | 0.74 | -34% |
| 2.5 / 14 / 14 | 1.19 | 718 | 40% | 1.39 | 16.4% | 0.83 | -29% |
| 2.5 / 14 / 20 | 1.18 | 484 | 40% | 1.34 | 13.0% | 0.69 | -28% |
| 2.5 / 10 / 14 | 1.16 | 724 | 40% | 1.38 | 17.1% | 0.86 | -28% |

## EGX (137 assets)

V10 uses the two filters with the best TRAIN Sharpe gain: **weekly + vol**.

| Version (TEST 2021-today) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 166 | 47% | +8.8% | 2.92 | 3% | 38.0% | 1.58 | -34% |
| V1 + Lorentzian arrow | 86 | 49% | +8.8% | 3.03 | 3% | 36.1% | 1.55 | -33% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 158 | 49% | +9.2% | 3.03 | 3% | 32.8% | 1.37 | -38% |
| V3 + order-block retest | 20 | 56% | +8.3% | 2.89 | 3% | 14.6% | 1.24 | -15% |
| V4 + market uptrend | 154 | 48% | +9.0% | 3.03 | 3% | 37.2% | 1.60 | -30% |
| V5 + stronger than market | 83 | 46% | +7.0% | 2.36 | 3% | 28.7% | 1.31 | -33% |
| V6 + volume surge | 133 | 48% | +8.7% | 2.95 | 3% | 41.0% | 1.68 | -29% |
| V7 + weekly trend green | 83 | 51% | +9.8% | 3.43 | 3% | 37.3% | 1.71 | -21% |
| V8 + real squeeze + ADX>20 | 71 | 47% | +7.9% | 2.74 | 3% | 27.5% | 1.41 | -24% |
| V9 + buy the pullback | 72 | 35% | +4.9% | 2.07 | 23% | 22.0% | 1.16 | -31% |
| V10 V0 + best 2 filters (from train) | 67 | 53% | +8.8% | 3.24 | 3% | 35.1% | 1.69 | -22% |
| Buy & hold (equal weight) | | | | | | 43.8% | 1.97 | -34% |

Same versions in TRAIN (2016-2020), for consistency:

| Version (TRAIN) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 71 | 41% | +2.7% | 1.53 | 3% | 6.4% | 0.44 | -37% |
| V1 + Lorentzian arrow | 33 | 40% | +3.0% | 1.59 | 3% | 5.9% | 0.50 | -17% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 59 | 41% | +3.2% | 1.66 | 3% | 9.1% | 0.60 | -26% |
| V3 + order-block retest | 5 | 38% | +0.0% | 1.00 | 0% | -0.2% | -0.05 | -6% |
| V4 + market uptrend | 47 | 40% | +3.1% | 1.57 | 3% | 5.1% | 0.42 | -25% |
| V5 + stronger than market | 28 | 38% | +2.2% | 1.41 | 3% | 2.0% | 0.23 | -23% |
| V6 + volume surge | 51 | 45% | +3.8% | 1.81 | 3% | 11.0% | 0.75 | -28% |
| V7 + weekly trend green | 27 | 43% | +6.0% | 2.24 | 2% | 9.6% | 0.83 | -18% |
| V8 + real squeeze + ADX>20 | 26 | 38% | +2.1% | 1.38 | 4% | 1.2% | 0.16 | -22% |
| V9 + buy the pullback | 31 | 25% | -0.5% | 0.89 | 32% | -0.7% | -0.03 | -24% |
| V10 V0 + best 2 filters (from train) | 21 | 46% | +6.4% | 2.34 | 1% | 8.7% | 0.81 | -16% |

### Settings sweep (V0 rule), chosen on TRAIN Sharpe

| Settings (factor / ATR / squeeze) | TRAIN Sharpe | TEST trades/yr | TEST win | TEST PF | TEST CAGR | TEST Sharpe | TEST Max DD |
|---|---|---|---|---|---|---|---|
| 3 / 10 / 20 (default) | 0.44 | 166 | 47% | 2.92 | 38.0% | 1.58 | -34% |
| 3.5 / 14 / 14 **(best in train)** | 0.66 | 185 | 49% | 2.91 | 33.1% | 1.36 | -36% |
| 3 / 14 / 14 | 0.64 | 213 | 49% | 2.76 | 36.5% | 1.47 | -38% |
| 2.5 / 10 / 14 | 0.59 | 241 | 47% | 2.70 | 37.8% | 1.57 | -35% |
| 3.5 / 14 / 20 | 0.58 | 160 | 48% | 2.82 | 31.4% | 1.32 | -44% |
| 2.5 / 7 / 14 | 0.53 | 233 | 46% | 2.69 | 34.2% | 1.43 | -38% |

## Crypto (38 assets)

V10 uses the two filters with the best TRAIN Sharpe gain: **rs + sqz**.

| Version (TEST 2021-today) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 87 | 41% | +17.2% | 3.12 | 3% | 57.1% | 1.15 | -60% |
| V1 + Lorentzian arrow | 51 | 42% | +18.5% | 3.30 | 3% | 44.8% | 1.11 | -52% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 82 | 40% | +16.2% | 2.89 | 2% | 48.3% | 1.04 | -53% |
| V3 + order-block retest | 9 | 30% | +36.1% | 5.02 | 6% | 13.7% | 0.97 | -16% |
| V4 + market uptrend | 46 | 44% | +22.4% | 3.86 | 3% | 47.8% | 1.17 | -57% |
| V5 + stronger than market | 27 | 39% | +14.3% | 2.48 | 3% | 14.8% | 0.63 | -46% |
| V6 + volume surge | 43 | 36% | +23.0% | 3.48 | 4% | 46.4% | 1.14 | -53% |
| V7 + weekly trend green | 17 | 49% | +29.7% | 5.03 | 1% | 30.2% | 1.13 | -30% |
| V8 + real squeeze + ADX>20 | 35 | 35% | +10.1% | 2.15 | 3% | 19.1% | 0.74 | -42% |
| V9 + buy the pullback | 48 | 32% | +19.3% | 3.88 | 26% | 43.1% | 1.16 | -44% |
| V10 V0 + best 2 filters (from train) | 9 | 32% | +2.1% | 1.23 | 0% | 2.1% | 0.23 | -20% |
| Buy & hold (equal weight) | | | | | | 154.9% | 0.72 | -77% |

Same versions in TRAIN (2016-2020), for consistency:

| Version (TRAIN) | Trades/yr | Win | Avg trade | Profit factor | Whipsaw | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|
| V0 arrow + bright squeeze (yours) | 29 | 52% | +21.0% | 4.06 | 6% | 49.9% | 1.36 | -40% |
| V1 + Lorentzian arrow | 15 | 51% | +17.5% | 3.40 | 9% | 21.0% | 0.99 | -23% |
| V2 3 of 4 (arrow, squeeze, Lorentzian, OB) | 22 | 47% | +17.7% | 3.22 | 7% | 26.3% | 1.03 | -29% |
| V3 + order-block retest | 4 | 50% | +58.8% | 12.66 | 17% | 12.0% | 1.42 | -7% |
| V4 + market uptrend | 14 | 46% | +20.1% | 3.71 | 11% | 23.5% | 1.12 | -28% |
| V5 + stronger than market | 9 | 67% | +35.1% | 7.70 | 4% | 25.9% | 1.42 | -19% |
| V6 + volume surge | 16 | 42% | +21.5% | 3.48 | 9% | 22.6% | 1.08 | -35% |
| V7 + weekly trend green | 3 | 59% | +63.1% | 16.53 | 12% | 14.0% | 1.45 | -9% |
| V8 + real squeeze + ADX>20 | 13 | 60% | +25.1% | 5.48 | 5% | 27.2% | 1.32 | -21% |
| V9 + buy the pullback | 16 | 48% | +27.5% | 6.52 | 19% | 35.2% | 1.53 | -20% |
| V10 V0 + best 2 filters (from train) | 4 | 82% | +50.0% | 21.14 | 0% | 17.5% | 1.57 | -13% |

### Settings sweep (V0 rule), chosen on TRAIN Sharpe

| Settings (factor / ATR / squeeze) | TRAIN Sharpe | TEST trades/yr | TEST win | TEST PF | TEST CAGR | TEST Sharpe | TEST Max DD |
|---|---|---|---|---|---|---|---|
| 3 / 10 / 20 (default) | 1.36 | 87 | 41% | 3.12 | 57.1% | 1.15 | -60% |
| 3 / 14 / 20 | 1.35 | 90 | 40% | 2.76 | 54.5% | 1.14 | -57% |
| 3 / 7 / 20 | 1.32 | 84 | 39% | 2.88 | 52.3% | 1.09 | -63% |
| 2.5 / 14 / 20 | 1.24 | 97 | 41% | 2.73 | 51.1% | 1.15 | -56% |
| 2.5 / 14 / 14 | 1.23 | 127 | 40% | 2.27 | 45.9% | 1.01 | -57% |

## Conclusions (a filter counts only if it helps in BOTH train and test)
- **Weekly trend green (V7)** is the most reliable accuracy filter: in EGX and crypto it raised profit factor and
  cut drawdown in both periods (EGX test PF 3.43 vs 2.92, max DD -21% vs -34%; crypto test PF 5.03 vs 3.12,
  max DD -30% vs -60%, at a lower crypto return). In US stocks it helped in test but hurt in train - not reliable.
- **EGX best: V0 + weekly green + volume surge (V10)**: win 53%, PF 3.24, Sharpe 1.69, max DD -22% in test;
  also better than V0 in train (Sharpe 0.81 vs 0.44).
- **US: no filter improved both periods consistently.** Buying the pullback (V9) raised Sharpe in both periods
  (0.94 vs 0.76 test, 1.11 vs 1.02 train) but stops out often (32% whipsaws).
- **3 of 4 with order blocks (V2)** performs about the same as V0 everywhere: the arrow and squeeze are usually
  present anyway, so the order block adds little. Requiring an OB retest (V3) gives very few trades.
- **Settings**: the default AlgoAlpha 10 / 3 and Squeeze 20 were as good as or better than the train-optimised
  settings in the test period in every market - changing the numbers mostly fits the past.
- In 2021-2026 simple buy & hold beat every signal version on return in US and EGX (EGX in EGP); the signals'
  value is smaller drawdowns and, with filters, fewer and better trades.
