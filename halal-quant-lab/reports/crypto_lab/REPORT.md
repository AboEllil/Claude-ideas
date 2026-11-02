# Crypto lab - machine learning, adaptive indicators and ML-filtered signals

Generated 2026-11-02. 33 halal-filtered coins (today's list: survivorship bias flatters every line, buy & hold included), 83,084 coin-days from 2016, 44 features. Next-close execution, 0.10% per side. Rules and pass conditions fixed before the run (see run_crypto_lab.py).

## 1. Can the model tell which coins will be up in 10 days? (out-of-sample)

| Year | AUC (0.50 = coin flip) | Training coin-days | Share up in training |
|---|---|---|---|
| 2019 | 0.448 | 6,584 | 46% |
| 2020 | 0.481 | 12,570 | 47% |
| 2021 | 0.486 | 19,899 | 50% |
| 2022 | 0.529 | 28,870 | 52% |
| 2023 | 0.509 | 38,184 | 50% |
| 2024 | 0.597 | 48,605 | 50% |
| 2025 | 0.558 | 60,260 | 50% |
| 2026 | 0.500 | 72,194 | 49% |

Coin-days sorted by the model's chance, 2019-today (fifths, low -> high):

| | Lowest | 2 | 3 | 4 | Highest |
|---|---|---|---|---|---|
| Share up after 10 days | 50% | 45% | 47% | 49% | 51% |
| Average 10-day return | +3.4% | +1.2% | +1.3% | +1.8% | +2.4% |

## 2. Strategies

| Strategy | Period | CAGR | Sharpe | Max DD | Time invested | Beats BASE? |
|---|---|---|---|---|---|---|
| BASE (current crypto rule) | 2019-2020 | 9.9% | 0.99 | -9% | 28% |  |
| BASE (current crypto rule) | 2021-today | 30.1% | 1.13 | -31% | 57% |  |
| S1 ML timing | 2019-2020 | 24.1% | 0.69 | -64% | 78% | no |
| S1 ML timing | 2021-today | 37.9% | 0.85 | -60% | 79% | no |
| S2 ML rotation (top 5) | 2019-2020 | 23.1% | 0.67 | -65% | 78% | no |
| S2 ML rotation (top 5) | 2021-today | 31.6% | 0.76 | -71% | 79% | no |
| S3 per-coin adaptive settings | 2019-2020 | 11.7% | 1.03 | -9% | 39% | yes |
| S3 per-coin adaptive settings | 2021-today | 31.1% | 1.32 | -24% | 59% | yes |
| S4 BASE + ML filter | 2019-2020 | 9.7% | 1.57 | -4% | 28% | yes |
| S4 BASE + ML filter | 2021-today | 29.1% | 1.27 | -29% | 43% | yes |
| Buy & hold, equal weight (max 10% each) | 2019-2020 | 112.8% | 1.38 | -66% | 100% | no |
| Buy & hold, equal weight (max 10% each) | 2021-today | 44.8% | 0.88 | -77% | 100% | no |

## 3. Verdict (pre-registered: higher Sharpe and drawdown no more than 5 points deeper, in both periods)

| Strategy | Result |
|---|---|
| S1 ML timing | **FAIL** |
| S2 ML rotation (top 5) | **FAIL** |
| S3 per-coin adaptive settings | **PASS** |
| S4 BASE + ML filter | **PASS** |

## 4. Per-coin settings chosen (S3)

Default 3 / 10 chosen in 61% of coin-years. Most common: 3/10 (200), 2/7 (32), 2/14 (21), 2/10 (13), 2.5/7 (11).

## 5. Patterns the model leans on (permutation importance, in-sample, explanation only)

| Feature | AUC drop when shuffled |
|---|---|
| btc_ret30 | 0.0551 |
| stable_g30 | 0.0525 |
| fed_vs13w | 0.0522 |
| chain_addr | 0.0498 |
| chain_hash | 0.0305 |
| chain_tx | 0.0259 |
| btc_ret7 | 0.0185 |
| btc_vol30 | 0.0169 |
| ret30_rank | 0.0160 |
| dist50 | 0.0077 |
| ret90_rank | 0.0070 |
| ret60 | 0.0051 |

## 6. Simple patterns: share of coin-days up after 10 days, by fifth of each feature (2016-today)

| Feature | Lowest | 2 | 3 | 4 | Highest |
|---|---|---|---|---|---|
| btc_ret30 | 46% | 45% | 45% | 46% | 59% |
| stable_g30 | 45% | 46% | 47% | 52% | 51% |
| fed_vs13w | 43% | 48% | 50% | 46% | 55% |
| chain_addr | 47% | 52% | 42% | 49% | 51% |
| chain_hash | 50% | 44% | 49% | 49% | 49% |
| chain_tx | 50% | 47% | 46% | 45% | 54% |
| btc_ret7 | 49% | 48% | 46% | 43% | 54% |
| btc_vol30 | 45% | 47% | 49% | 49% | 51% |

## 7. Reading the result (plain language)

- The model can NOT predict which coin will be up in 10 days (AUC about 0.50; below 0.50 in 2019-2021), so
  using it to time or rotate coins (S1, S2) loses to the current rule badly (drawdowns -60% to -71%).
- What it leans on is the crypto MARKET mood - Bitcoin's last 30 days, stablecoin growth, Fed liquidity, Bitcoin
  network activity - not coin-level patterns (RSI, volume, candles rank low).
- Used as a FILTER on the current rule's signals (S4) it passed: Sharpe 1.57 vs 0.99 (2019-2020) and 1.27 vs 1.13
  (2021-today), smaller drawdowns, slightly lower return, less time invested. This matches the liquidity finding.
- Per-coin adaptive AlgoAlpha settings (S3) passed too, but by a hair in 2019-2020 (Sharpe 1.03 vs 0.99); the
  clearer gain is 2021-today (1.32 vs 1.13, drawdown -24% vs -31%). 61% of coin-years kept the default 3 / 10.
- Four strategies were tested, so one could pass by luck; both passes should be tracked forward before money
  depends on them. Caveat: today's coin list (survivorship bias).
