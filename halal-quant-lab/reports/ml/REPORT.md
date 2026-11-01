# Walk-forward ML forecaster

Generated 2026-11-01. 413 assets, weekly predictions, 36 features. Retrained every January on earlier data only (30-day embargo). Label: beats its market's average over the next 20 trading days. Out-of-sample from 2019.

## Prediction quality (out-of-sample)

AUC 0.50 = coin flip; 0.55+ is useful for stock picking.

| Year | AUC | Training rows |
|---|---|---|
| 2019 | 0.531 | 76,229 |
| 2020 | 0.545 | 93,537 |
| 2021 | 0.533 | 111,353 |
| 2022 | 0.534 | 130,586 |
| 2023 | 0.529 | 150,575 |
| 2024 | 0.532 | 171,442 |
| 2025 | 0.540 | 192,441 |
| 2026 | 0.538 | 213,865 |

Hit rate (beat the market over 20 days) by predicted rank within each week:

| Market | Bottom 20% | 20-40% | 40-60% | 60-80% | Top 20% | Top 20% avg 20-day excess return |
|---|---|---|---|---|---|---|
| US | 44% | 45% | 46% | 46% | 47% | +0.32% |
| EGX | 37% | 40% | 41% | 43% | 44% | +0.79% |
| Crypto | 34% | 34% | 37% | 39% | 45% | +101.51% |

## Portfolio: hold the top-K predictions each week (next-close execution, costs, max 10% each)

| Market | Strategy | Period | Win | PF | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|
| US | ML top-K | 2019-today | 56% | 1.41 | 37.8% | 1.07 | -50% |
| US | ML top-K | 2021-today | 55% | 1.33 | 29.8% | 0.92 | -40% |
| US | ML top-K, only when market > 200-day | 2019-today | 54% | 1.32 | 22.4% | 0.90 | -34% |
| US | ML top-K, only when market > 200-day | 2021-today | 54% | 1.23 | 15.7% | 0.68 | -34% |
| US | Buy & hold (equal weight) | 2019-today | | | 31.9% | 1.27 | -39% |
| US | Buy & hold (equal weight) | 2021-today | | | 28.3% | 1.27 | -26% |
| EGX | ML top-K | 2019-today | 49% | 1.38 | 17.5% | 0.79 | -48% |
| EGX | ML top-K | 2021-today | 49% | 1.45 | 23.1% | 0.98 | -48% |
| EGX | ML top-K, only when market > 200-day | 2019-today | 50% | 1.57 | 21.8% | 1.10 | -30% |
| EGX | ML top-K, only when market > 200-day | 2021-today | 50% | 1.58 | 25.8% | 1.21 | -30% |
| EGX | Buy & hold (equal weight) | 2019-today | | | 37.2% | 1.73 | -39% |
| EGX | Buy & hold (equal weight) | 2021-today | | | 43.8% | 1.97 | -34% |
| Crypto | ML top-K | 2019-today | 50% | 1.69 | 33.7% | 0.95 | -42% |
| Crypto | ML top-K | 2021-today | 49% | 1.60 | 33.6% | 0.96 | -41% |
| Crypto | ML top-K, only when market > 200-day | 2019-today | 49% | 1.76 | 20.4% | 0.79 | -55% |
| Crypto | ML top-K, only when market > 200-day | 2021-today | 50% | 2.07 | 31.3% | 1.15 | -19% |
| Crypto | Buy & hold (equal weight) | 2019-today | | | 143.4% | 0.73 | -77% |
| Crypto | Buy & hold (equal weight) | 2021-today | | | 154.9% | 0.72 | -77% |

## What the model relies on (permutation importance, latest model)

| Feature | AUC drop when shuffled |
|---|---|
| is_US | 0.0366 |
| vol60_rank | 0.0157 |
| ret120 | 0.0089 |
| vol60 | 0.0067 |
| low52 | 0.0066 |
| breadth50 | 0.0057 |
| high52 | 0.0048 |
| atr_pct | 0.0047 |
| high52_rank | 0.0045 |
| vol20 | 0.0043 |
| ret60_rank | 0.0043 |
| mom12_1 | 0.0041 |

This week's ranking (2026-11-01): `latest_predictions.csv`. Top 5 per market:

- US: 
- EGX: 
- Crypto: XMR (46%), SOL (44%), RETH (43%), XRP (42%), ALGO (42%)
