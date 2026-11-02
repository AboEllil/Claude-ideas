# ML signal filter - does a model pick the winning signals?

Generated 2026-11-02. 16,664 signals on 408 halal assets (16,450 closed trades). 57 features. Trades managed as on the dashboard (half at +2 ATR, then stop at entry; else the rule's exit), costs included. Walk-forward: each year's model only saw trades that had closed before that year. Judged on 2021-today.

Pre-registered pass rule: in at least 4 of 6 market x rule groups the ENSEMBLE-kept signals have a win rate +5 points or more, a profit factor not lower and a portfolio Sharpe not lower than all signals.

## 1. Prediction quality, 2021-today (AUC: 0.50 = coin flip)

| Market | Trades | GBM | Pattern twin | Ensemble |
|---|---|---|---|---|
| US | 7,303 | 0.553 | 0.543 | 0.556 |
| EGX | 2,018 | 0.546 | 0.530 | 0.545 |
| Crypto | 548 | 0.508 | 0.362 | 0.458 |
| All | 9,869 | 0.566 | 0.553 | 0.570 |

Win rate by the ensemble's predicted chance (fifths of each market's test signals, low -> high):

| Market | Lowest 20% | 20-40% | 40-60% | 60-80% | Highest 20% | Avg trade, lowest | Avg trade, highest |
|---|---|---|---|---|---|---|---|
| US | 39% | 38% | 45% | 48% | 51% | +0.9% | +1.0% |
| EGX | 50% | 58% | 61% | 57% | 62% | +2.4% | +8.5% |
| Crypto | 59% | 57% | 51% | 64% | 42% | +5.2% | -0.6% |

## 2. All signals vs signals the model keeps (2021-today)

| Market | Rule | Signals | Trades | Win rate | Avg trade | Profit factor | Portfolio CAGR | Sharpe | Max DD | Pass? |
|---|---|---|---|---|---|---|---|---|---|---|
| US | Dashboard rule | All | 4630 | 40% | +1.1% | 1.42 | 4.4% | 0.40 | -24% |  |
| US | Dashboard rule | Weekly green only | 1858 | 38% | +0.7% | 1.28 | 3.4% | 0.32 | -23% |  |
| US | Dashboard rule | ML keeps | 1252 | 41% | +1.6% | 1.57 | 8.0% | 0.63 | -19% | no |
| US | Dashboard rule | ML skips | 3378 | 39% | +0.9% | 1.36 | 4.0% | 0.37 | -24% |  |
| US | Your rule | All | 2673 | 53% | +1.2% | 1.28 | 8.2% | 0.59 | -23% |  |
| US | Your rule | Weekly green only | 1267 | 53% | +1.3% | 1.34 | 9.6% | 0.72 | -22% |  |
| US | Your rule | ML keeps | 2508 | 53% | +1.2% | 1.28 | 7.8% | 0.57 | -23% | no |
| US | Your rule | ML skips | 165 | 56% | +1.3% | 1.31 | 3.0% | 0.40 | -12% |  |
| EGX | Dashboard rule | All | 1074 | 54% | +5.0% | 2.18 | 27.6% | 1.57 | -20% |  |
| EGX | Dashboard rule | Weekly green only | 703 | 56% | +5.9% | 2.42 | 29.3% | 1.71 | -19% |  |
| EGX | Dashboard rule | ML keeps | 934 | 56% | +5.5% | 2.37 | 30.8% | 1.71 | -19% | no |
| EGX | Dashboard rule | ML skips | 140 | 39% | +1.6% | 1.29 | 4.5% | 0.57 | -11% |  |
| EGX | Your rule | All | 944 | 62% | +5.7% | 2.41 | 25.1% | 1.51 | -27% |  |
| EGX | Your rule | Weekly green only | 474 | 63% | +7.0% | 2.86 | 26.5% | 1.78 | -14% |  |
| EGX | Your rule | ML keeps | 778 | 62% | +6.2% | 2.57 | 29.0% | 1.73 | -20% | no |
| EGX | Your rule | ML skips | 166 | 58% | +3.4% | 1.76 | 8.4% | 0.85 | -23% |  |
| Crypto | Dashboard rule | All | 91 | 56% | +8.3% | 2.19 | 9.9% | 0.71 | -21% |  |
| Crypto | Dashboard rule | Weekly green only | 91 | 56% | +8.3% | 2.19 | 9.9% | 0.71 | -21% |  |
| Crypto | Dashboard rule | ML keeps | 84 | 55% | +8.6% | 2.19 | 9.6% | 0.70 | -21% | no |
| Crypto | Dashboard rule | ML skips | 7 | 71% | +4.6% | 2.15 | 0.7% | 0.33 | -3% |  |
| Crypto | Your rule | All | 457 | 54% | +7.6% | 2.09 | 23.5% | 0.81 | -49% |  |
| Crypto | Your rule | Weekly green only | 91 | 56% | +8.3% | 2.19 | 9.9% | 0.71 | -21% |  |
| Crypto | Your rule | ML keeps | 445 | 54% | +7.9% | 2.13 | 23.2% | 0.81 | -49% | no |
| Crypto | Your rule | ML skips | 12 | 50% | -1.1% | 0.84 | -0.1% | -0.03 | -6% |  |

**Verdict: FAILED** - the pass conditions held in 0 of 6 groups (needed 4).

## 3. Walk-forward training sizes and cut-offs

| Test year | Closed trades trained on | Keep if chance >= |
|---|---|---|
| 2019 | 3,862 | 0.413 |
| 2020 | 4,989 | 0.429 |
| 2021 | 6,314 | 0.453 |
| 2022 | 7,584 | 0.459 |
| 2023 | 9,267 | 0.469 |
| 2024 | 10,791 | 0.479 |
| 2025 | 12,721 | 0.481 |
| 2026 | 14,608 | 0.487 |

## 4. What the model looks at most (permutation importance, in-sample, for explanation only)

| Feature | AUC drop when shuffled |
|---|---|
| is_dashboard | 0.0526 |
| mkt_vol20 | 0.0321 |
| dist200 | 0.0111 |
| atr_pct | 0.0103 |
| mkt_ret20 | 0.0083 |
| dist50 | 0.0079 |
| adx | 0.0060 |
| ret60 | 0.0046 |
| low52 | 0.0046 |
| ret120 | 0.0045 |
| mkt_up200 | 0.0035 |
| path6 | 0.0030 |

## 5. After-the-fact check (NOT part of the pass rule)

The single cut-off was a design flaw: it kept 94% of the US "your rule" signals but only 27% of the US
dashboard signals. Re-checked with a separate cut-off per market x rule (the median of the previous
year's out-of-sample predictions, so still no look-ahead), 2021-today:

| Market | Rule | All: win / avg / PF | ML keeps: win / avg / PF | ML skips: win / avg / PF |
|---|---|---|---|---|
| US | Dashboard rule | 40% / +1.1% / 1.42 | 39% / +1.0% / 1.34 | 40% / +1.2% / 1.51 |
| US | Your rule | 53% / +1.2% / 1.28 | 50% / +0.6% / 1.12 | 55% / +1.7% / 1.44 |
| EGX | Dashboard rule | 54% / +5.0% / 2.18 | 59% / +6.8% / 2.77 | 48% / +2.6% / 1.56 |
| EGX | Your rule | 62% / +5.7% / 2.41 | 63% / +7.1% / 2.89 | 59% / +4.0% / 1.91 |
| Crypto | Your rule | 54% / +7.6% / 2.09 | 53% / +7.9% / 2.14 | 55% / +7.4% / 2.05 |

Same conclusion: no reliable win-rate gain. Only EGX shows a useful separation (kept signals earn more
per trade); in the US the model is no better than chance inside each rule. The broad AUC (0.57 overall)
comes mostly from telling the two rules and market moods apart, not from picking winners within a rule.
The weekly-trend filter does as well or better than the model and is far simpler.
