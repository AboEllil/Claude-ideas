# Walk-forward ML forecaster

Generated 2026-11-01. 408 assets, weekly predictions, 36 features. Retrained every January on earlier data only (30-day embargo). Label: beats its market's average over the next 20 trading days. Out-of-sample from 2019.

## Prediction quality (out-of-sample)

AUC 0.50 = coin flip; 0.55+ is useful for stock picking.

| Year | AUC | Training rows |
|---|---|---|
| 2019 | 0.536 | 76,229 |
| 2020 | 0.547 | 93,537 |
| 2021 | 0.538 | 111,353 |
| 2022 | 0.536 | 130,585 |
| 2023 | 0.530 | 150,496 |
| 2024 | 0.532 | 171,257 |
| 2025 | 0.539 | 192,097 |
| 2026 | 0.536 | 213,297 |

Hit rate (beat the market over 20 days) by predicted rank within each week:

| Market | Bottom 20% | 20-40% | 40-60% | 60-80% | Top 20% | Top 20% avg 20-day excess return |
|---|---|---|---|---|---|---|
| US | 45% | 45% | 46% | 46% | 47% | +0.31% |
| EGX | 37% | 39% | 41% | 43% | 45% | +0.70% |
| Crypto | 35% | 33% | 38% | 41% | 45% | +1.10% |

## Portfolio: hold the top-K predictions each week (next-close execution, costs, max 10% each)

| Market | Strategy | Period | Win | PF | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|
| US | ML top-K | 2019-today | 55% | 1.31 | 32.0% | 0.94 | -50% |
| US | ML top-K | 2021-today | 54% | 1.22 | 22.8% | 0.76 | -44% |
| US | ML top-K, only when market > 200-day | 2019-today | 54% | 1.26 | 21.6% | 0.89 | -37% |
| US | ML top-K, only when market > 200-day | 2021-today | 53% | 1.16 | 14.4% | 0.64 | -37% |
| US | Buy & hold (equal weight) | 2019-today | | | 31.9% | 1.27 | -39% |
| US | Buy & hold (equal weight) | 2021-today | | | 28.3% | 1.27 | -26% |
| EGX | ML top-K | 2019-today | 47% | 1.24 | 11.2% | 0.56 | -55% |
| EGX | ML top-K | 2021-today | 48% | 1.29 | 15.5% | 0.72 | -55% |
| EGX | ML top-K, only when market > 200-day | 2019-today | 48% | 1.46 | 18.1% | 0.94 | -25% |
| EGX | ML top-K, only when market > 200-day | 2021-today | 48% | 1.45 | 22.1% | 1.07 | -25% |
| EGX | Buy & hold (equal weight) | 2019-today | | | 37.2% | 1.73 | -39% |
| EGX | Buy & hold (equal weight) | 2021-today | | | 43.8% | 1.97 | -34% |
| Crypto | ML top-K | 2019-today | 50% | 1.74 | 35.2% | 0.97 | -49% |
| Crypto | ML top-K | 2021-today | 50% | 1.66 | 35.5% | 0.99 | -44% |
| Crypto | ML top-K, only when market > 200-day | 2019-today | 49% | 1.86 | 21.9% | 0.81 | -62% |
| Crypto | ML top-K, only when market > 200-day | 2021-today | 50% | 2.09 | 32.2% | 1.14 | -35% |
| Crypto | Buy & hold (equal weight) | 2019-today | | | 59.8% | 1.01 | -77% |
| Crypto | Buy & hold (equal weight) | 2021-today | | | 44.8% | 0.88 | -77% |

## What the model relies on (permutation importance, latest model)

| Feature | AUC drop when shuffled |
|---|---|
| is_US | 0.0362 |
| vol60_rank | 0.0200 |
| vol60 | 0.0101 |
| breadth50 | 0.0071 |
| ret120 | 0.0071 |
| high52_rank | 0.0046 |
| ret60 | 0.0045 |
| high52 | 0.0045 |
| mom12_1 | 0.0042 |
| low52 | 0.0039 |
| st_days | 0.0039 |
| mom12_1_rank | 0.0034 |

This week's ranking (2026-11-01): `latest_predictions.csv`. Top 5 per market:

- US: FTNT (55%), POWL (54%), AAON (53%), OUST (53%), AUR (52%)
- EGX: ORHD (52%), EFID (51%), ISMA (51%), GGCC (51%), UEGC (50%)
- Crypto: XMR (54%), ALGO (44%), ICP (43%), RENDER (43%), TAO22974 (43%)

## Conclusions
- The model has a small but steady edge: out-of-sample AUC 0.530-0.547 in all 8 years (0.50 = coin flip), and
  the hit rate rises from the bottom to the top predicted fifth in every market (US 45->47%, EGX 37->45%,
  crypto 35->45%). It mostly uses volatility (lower volatility ranks better), 6-12 month momentum,
  closeness to the 52-week high and market breadth - the classic factors, not the chart indicators.
- As a stand-alone strategy it did NOT beat buy & hold in US or EGX. In crypto it gave a better risk-adjusted
  result than holding everything (2021-today Sharpe 0.99 vs 0.88, max DD -44% vs -77%).
- Best use: a ranking score to choose between signals that fire on the same day, not a buy/sell signal.
