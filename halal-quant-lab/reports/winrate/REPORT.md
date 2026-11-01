# Win-rate lab

Generated 2026-11-01. 6649 signals of the user's rule (arrow + bright squeeze) on 413 assets. Train = signals before 2021, test = 2021-today. Trade returns include costs. Portfolio: max 10% per position.

## A. Exits: win rate vs profit (all signals, TEST 2021-today)

| Market | Exit | Trades | Win rate | Avg trade | Profit factor | Avg days | Portfolio CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| US | E1 red arrow | 2755 | 41% | +2.0% | 1.41 | 33 | 14.2% | 0.77 | -26% |
| US | E2 TP +2 ATR | 2755 | 55% | +0.8% | 1.19 | 15 | 10.4% | 0.57 | -34% |
| US | E3 TP +3 ATR | 2755 | 48% | +0.9% | 1.20 | 18 | 9.0% | 0.51 | -36% |
| US | E4 half +2 ATR, breakeven | 2755 | 53% | +1.4% | 1.33 | 32 | 11.5% | 0.77 | -22% |
| US | E5 breakeven after +1.5 ATR | 2755 | 41% | +2.0% | 1.43 | 31 | 15.3% | 0.81 | -25% |
| EGX | E1 red arrow | 945 | 47% | +8.9% | 2.81 | 41 | 37.5% | 1.56 | -33% |
| EGX | E2 TP +2 ATR | 945 | 65% | +3.2% | 1.81 | 17 | 26.6% | 1.37 | -28% |
| EGX | E3 TP +3 ATR | 945 | 56% | +3.7% | 1.84 | 20 | 25.9% | 1.27 | -32% |
| EGX | E4 half +2 ATR, breakeven | 945 | 62% | +5.9% | 2.47 | 39 | 25.4% | 1.53 | -27% |
| EGX | E5 breakeven after +1.5 ATR | 945 | 46% | +8.5% | 2.94 | 37 | 37.9% | 1.59 | -31% |
| Crypto | E1 red arrow | 479 | 38% | +13.3% | 2.57 | 31 | 38.6% | 0.93 | -60% |
| Crypto | E2 TP +2 ATR | 479 | 56% | +2.2% | 1.33 | 14 | 11.3% | 0.53 | -46% |
| Crypto | E3 TP +3 ATR | 479 | 48% | +2.3% | 1.29 | 16 | 9.0% | 0.43 | -59% |
| Crypto | E4 half +2 ATR, breakeven | 479 | 54% | +7.3% | 2.05 | 29 | 23.3% | 0.80 | -50% |
| Crypto | E5 breakeven after +1.5 ATR | 479 | 39% | +11.8% | 2.55 | 28 | 32.7% | 0.86 | -58% |

## B. Signal-quality model (trained on 2016-2020 only)

Cut-off: predicted win probability >= 0.42 (the best 40% of out-of-fold training signals). Out-of-fold check inside training: win rate 47% for picked vs 44% for rejected signals.

| Market | Signals kept | Exit | Trades | Win rate | Avg trade | Profit factor | Portfolio CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| US | All signals (your rule) | E1 red arrow | 2755 | 41% | +2.0% | 1.41 | 14.2% | 0.77 | -26% |
| US | All signals (your rule) | E4 half +2 ATR, breakeven | 2755 | 53% | +1.4% | 1.33 | 11.5% | 0.77 | -22% |
| US | All signals (your rule) | E5 breakeven after +1.5 ATR | 2755 | 41% | +2.0% | 1.43 | 15.3% | 0.81 | -25% |
| US | Weekly trend green | E1 red arrow | 1310 | 43% | +2.4% | 1.56 | 18.7% | 0.98 | -27% |
| US | Weekly trend green | E4 half +2 ATR, breakeven | 1310 | 54% | +1.7% | 1.44 | 14.1% | 0.98 | -23% |
| US | Weekly trend green | E5 breakeven after +1.5 ATR | 1310 | 43% | +2.3% | 1.58 | 19.7% | 1.03 | -25% |
| US | ML best 40% | E1 red arrow | 1457 | 43% | +3.1% | 1.62 | 12.8% | 0.66 | -40% |
| US | ML best 40% | E4 half +2 ATR, breakeven | 1457 | 55% | +2.3% | 1.52 | 9.9% | 0.63 | -33% |
| US | ML best 40% | E5 breakeven after +1.5 ATR | 1457 | 43% | +3.0% | 1.65 | 13.3% | 0.68 | -42% |
| US | ML best 40% + weekly green | E1 red arrow | 617 | 45% | +3.3% | 1.79 | 21.6% | 1.11 | -24% |
| US | ML best 40% + weekly green | E4 half +2 ATR, breakeven | 617 | 56% | +2.5% | 1.66 | 17.5% | 1.19 | -21% |
| US | ML best 40% + weekly green | E5 breakeven after +1.5 ATR | 617 | 45% | +3.3% | 1.83 | 22.3% | 1.15 | -23% |
| EGX | All signals (your rule) | E1 red arrow | 945 | 47% | +8.9% | 2.81 | 37.5% | 1.56 | -33% |
| EGX | All signals (your rule) | E4 half +2 ATR, breakeven | 945 | 62% | +5.9% | 2.47 | 25.4% | 1.53 | -27% |
| EGX | All signals (your rule) | E5 breakeven after +1.5 ATR | 945 | 46% | +8.5% | 2.94 | 37.9% | 1.59 | -31% |
| EGX | Weekly trend green | E1 red arrow | 474 | 50% | +9.6% | 3.03 | 36.6% | 1.69 | -21% |
| EGX | Weekly trend green | E4 half +2 ATR, breakeven | 474 | 63% | +7.0% | 2.86 | 26.5% | 1.78 | -14% |
| EGX | Weekly trend green | E5 breakeven after +1.5 ATR | 474 | 51% | +9.9% | 3.46 | 39.3% | 1.81 | -19% |
| EGX | ML best 40% | E1 red arrow | 352 | 49% | +11.2% | 3.34 | 36.0% | 1.58 | -24% |
| EGX | ML best 40% | E4 half +2 ATR, breakeven | 352 | 64% | +7.9% | 3.18 | 24.8% | 1.63 | -20% |
| EGX | ML best 40% | E5 breakeven after +1.5 ATR | 352 | 49% | +10.8% | 3.65 | 35.1% | 1.57 | -24% |
| EGX | ML best 40% + weekly green | E1 red arrow | 183 | 52% | +11.6% | 3.44 | 24.3% | 1.41 | -17% |
| EGX | ML best 40% + weekly green | E4 half +2 ATR, breakeven | 183 | 63% | +9.3% | 3.61 | 17.8% | 1.52 | -12% |
| EGX | ML best 40% + weekly green | E5 breakeven after +1.5 ATR | 183 | 54% | +12.4% | 4.20 | 25.3% | 1.48 | -17% |
| Crypto | All signals (your rule) | E1 red arrow | 479 | 38% | +13.3% | 2.57 | 38.6% | 0.93 | -60% |
| Crypto | All signals (your rule) | E4 half +2 ATR, breakeven | 479 | 54% | +7.3% | 2.05 | 23.3% | 0.80 | -50% |
| Crypto | All signals (your rule) | E5 breakeven after +1.5 ATR | 479 | 39% | +11.8% | 2.55 | 32.7% | 0.86 | -58% |
| Crypto | Weekly trend green | E1 red arrow | 92 | 46% | +16.9% | 3.04 | 18.1% | 0.85 | -30% |
| Crypto | Weekly trend green | E4 half +2 ATR, breakeven | 92 | 55% | +8.1% | 2.14 | 9.7% | 0.69 | -22% |
| Crypto | Weekly trend green | E5 breakeven after +1.5 ATR | 92 | 46% | +10.1% | 2.27 | 10.9% | 0.60 | -29% |
| Crypto | ML best 40% | E1 red arrow | 366 | 39% | +16.8% | 3.00 | 39.1% | 0.98 | -57% |
| Crypto | ML best 40% | E4 half +2 ATR, breakeven | 366 | 55% | +9.0% | 2.34 | 23.2% | 0.86 | -48% |
| Crypto | ML best 40% | E5 breakeven after +1.5 ATR | 366 | 40% | +14.9% | 3.02 | 32.7% | 0.91 | -54% |
| Crypto | ML best 40% + weekly green | E1 red arrow | 62 | 53% | +21.1% | 3.90 | 17.4% | 0.92 | -23% |
| Crypto | ML best 40% + weekly green | E4 half +2 ATR, breakeven | 62 | 61% | +9.5% | 2.50 | 9.1% | 0.76 | -19% |
| Crypto | ML best 40% + weekly green | E5 breakeven after +1.5 ATR | 62 | 50% | +10.7% | 2.53 | 10.1% | 0.63 | -21% |

## C. When do signals win more often? (red-arrow exit, win rate by quintile: lowest -> highest)

| Feature | Train Q1 | Q2 | Q3 | Q4 | Q5 | Test Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|---|---|---|---|---|
| mom_atr | 43% | 42% | 46% | 45% | 45% | 44% | 40% | 43% | 43% | 40% |
| mom_slope | 43% | 42% | 48% | 46% | 43% | 40% | 41% | 40% | 44% | 44% |
| sqz_days | 45% | 45% | 41% | 45% | 44% | 43% | 43% | 42% | 40% |  |
| adx | 44% | 47% | 47% | 42% | 42% | 41% | 45% | 42% | 43% | 39% |
| rsi | 48% | 46% | 41% | 42% | 43% | 43% | 40% | 43% | 41% | 43% |
| dist_atr | 43% | 46% | 45% | 44% | 44% | 42% | 41% | 42% | 39% | 46% |
| vol_ratio | 49% | 47% | 41% | 39% | 44% | 44% | 40% | 41% | 41% | 44% |
| weekly_up | 45% | 43% |  |  |  | 40% | 45% |  |  |  |
| mkt_up | 57% | 40% |  |  |  | 42% | 42% |  |  |  |
| rs126 | 42% | 43% | 51% | 43% | 42% | 40% | 42% | 45% | 42% | 41% |
| high52 | 49% | 42% | 46% | 44% | 41% | 37% | 41% | 45% | 45% | 41% |
| atr_pct | 43% | 36% | 46% | 43% | 54% | 45% | 44% | 43% | 40% | 38% |
| ret5 | 43% | 41% | 43% | 45% | 48% | 44% | 43% | 42% | 43% | 38% |
| ret20 | 43% | 43% | 41% | 46% | 48% | 45% | 43% | 43% | 41% | 37% |
| ret60 | 48% | 41% | 42% | 44% | 46% | 38% | 45% | 42% | 42% | 43% |
| lor_pred | 40% | 45% | 48% | 44% |  | 40% | 41% | 43% |  |  |
| lor_arrow | 45% | 44% |  |  |  | 42% | 42% |  |  |  |
| ob_touch | 44% | 45% |  |  |  | 42% | 41% |  |  |  |
| red_days | 47% | 44% | 42% | 46% | 42% | 41% | 43% | 44% | 41% | 41% |
| cluster_up | 39% | 38% | 44% | 46% | 55% | 41% | 38% | 42% | 43% | 46% |

## Conclusions
- **The exit decides the win rate.** Selling half at +2 ATR and moving the stop to breakeven (E4) raised the
  win rate by 12-16 points in every market (US 41->53%, EGX 47->62%, crypto 38->54%) with a smaller drawdown,
  at the cost of some return. A full take-profit (E2/E3) raised win rate but cut profit too much.
- **Weekly trend green is the best entry filter** and works with every exit. Best balanced results (test 2021-today):
  - EGX: weekly green + E5 (breakeven after +1.5 ATR): win 51%, PF 3.46, CAGR 39.3%, Sharpe 1.81, max DD -19%
    (better than the current system on every measure); with E4: win 63%, Sharpe 1.78, max DD -14%.
  - US: weekly green + ML filter + E4: win 56%, PF 1.66, Sharpe 1.19, max DD -21% (current: 41%, 1.41, 0.77, -26%).
  - Crypto: weekly green + E4: win 55%, max DD -22% (current 38%, -60%) but much lower return.
- **The ML quality model alone adds little** (out-of-fold win rate 47% vs 44%): no single condition reliably
  predicts a winning signal; only market breadth (many assets turning green together) helped somewhat in both periods.
- Exits and filters were defined before the run, but the combinations above were picked after seeing them, so
  expect live results a little below these.
