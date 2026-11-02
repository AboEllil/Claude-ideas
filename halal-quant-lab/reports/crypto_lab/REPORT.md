# Crypto lab - machine learning, adaptive indicators and ML-filtered signals

Generated 2026-11-02. 75 halal-filtered coins (today's list: survivorship bias flatters every line, buy & hold included), 170,897 coin-days from 2016, 44 features. Next-close execution, 0.10% per side. Rules and pass conditions fixed before the run (see run_crypto_lab.py).

## 1. Can the model tell which coins will be up in 10 days? (out-of-sample)

| Year | AUC (0.50 = coin flip) | Training coin-days | Share up in training |
|---|---|---|---|
| 2019 | 0.460 | 9,940 | 44% |
| 2020 | 0.479 | 20,890 | 46% |
| 2021 | 0.527 | 34,575 | 50% |
| 2022 | 0.491 | 52,577 | 51% |
| 2023 | 0.508 | 72,339 | 48% |
| 2024 | 0.550 | 94,108 | 49% |
| 2025 | 0.561 | 119,603 | 49% |
| 2026 | 0.480 | 146,392 | 47% |

Coin-days sorted by the model's chance, 2019-today (fifths, low -> high):

| | Lowest | 2 | 3 | 4 | Highest |
|---|---|---|---|---|---|
| Share up after 10 days | 49% | 45% | 46% | 47% | 47% |
| Average 10-day return | +14.3% | +2.7% | +32.3% | +24.6% | +6.9% |

## 2. Strategies

| Strategy | Period | CAGR | Sharpe | Max DD | Time invested | Beats BASE? |
|---|---|---|---|---|---|---|
| BASE (current crypto rule) | 2019-2020 | 23.3% | 1.58 | -10% | 28% |  |
| BASE (current crypto rule) | 2021-today | 27.3% | 0.94 | -51% | 63% |  |
| S1 ML timing | 2019-2020 | 92.9% | 1.34 | -62% | 76% | no |
| S1 ML timing | 2021-today | 35.1% | 0.79 | -73% | 79% | no |
| S2 ML rotation (top 5) | 2019-2020 | 78.6% | 1.12 | -58% | 76% | no |
| S2 ML rotation (top 5) | 2021-today | 31.0% | 0.73 | -79% | 79% | no |
| S3 per-coin adaptive settings | 2019-2020 | 25.3% | 1.58 | -10% | 39% | no |
| S3 per-coin adaptive settings | 2021-today | 34.6% | 1.23 | -41% | 64% | yes |
| S4 BASE + ML filter | 2019-2020 | 16.1% | 1.67 | -8% | 28% | yes |
| S4 BASE + ML filter | 2021-today | 30.9% | 1.13 | -42% | 49% | yes |
| Buy & hold, equal weight (max 10% each) | 2019-2020 | 209.8% | 1.89 | -61% | 100% | no |
| Buy & hold, equal weight (max 10% each) | 2021-today | 43.0% | 0.86 | -79% | 100% | no |

## 3. Verdict (pre-registered: higher Sharpe and drawdown no more than 5 points deeper, in both periods)

| Strategy | Result |
|---|---|
| S1 ML timing | **FAIL** |
| S2 ML rotation (top 5) | **FAIL** |
| S3 per-coin adaptive settings | **FAIL** |
| S4 BASE + ML filter | **PASS** |

## 4. Per-coin settings chosen (S3)

Default 3 / 10 chosen in 67% of coin-years. Most common: 3/10 (501), 2/7 (73), 2/10 (32), 2/14 (28), 2.5/7 (21).

## 5. Patterns the model leans on (permutation importance, in-sample, explanation only)

| Feature | AUC drop when shuffled |
|---|---|
| btc_ret30 | 0.0611 |
| stable_g30 | 0.0494 |
| chain_addr | 0.0456 |
| fed_vs13w | 0.0437 |
| chain_tx | 0.0265 |
| btc_vol30 | 0.0232 |
| btc_ret7 | 0.0212 |
| chain_hash | 0.0207 |
| ret30_rank | 0.0078 |
| vol7 | 0.0068 |
| ret60 | 0.0051 |
| dist20 | 0.0049 |

## 6. Simple patterns: share of coin-days up after 10 days, by fifth of each feature (2016-today)

| Feature | Lowest | 2 | 3 | 4 | Highest |
|---|---|---|---|---|---|
| btc_ret30 | 44% | 44% | 43% | 43% | 59% |
| stable_g30 | 43% | 43% | 48% | 49% | 50% |
| chain_addr | 46% | 50% | 40% | 48% | 49% |
| fed_vs13w | 41% | 46% | 49% | 45% | 52% |
| chain_tx | 48% | 45% | 44% | 44% | 52% |
| btc_vol30 | 42% | 46% | 47% | 48% | 49% |
| btc_ret7 | 48% | 47% | 44% | 42% | 53% |
| chain_hash | 49% | 42% | 46% | 48% | 48% |

## 7. Reading the result (plain language) - re-test on 75 coins, 2 Nov 2026

- First run: 33 coins (reports/crypto_lab/REPORT_33coins.md). This run: the bigger 81-coin list (75 with
  enough history), with bad price prints removed (e.g. Bittensor's first Yahoo quote of $0.13 before $87.78).
- The model still cannot tell which coin will rise (AUC about 0.50), so ML timing / rotation fail again.
- S4 (current rule + ML mood filter) PASSES again: Sharpe 1.67 vs 1.58 (2019-2020) and 1.13 vs 0.94
  (2021-today), worst drop -42% vs -51%. It held on more than twice as many coins.
- S3 (per-coin adaptive settings) now FAILS: equal Sharpe in 2019-2020 (1.58 vs 1.58), better only in
  2021-today (1.23 vs 0.94). Kept on the board as information only.
- Several strategies tested, today's coin list (survivorship bias): track forward before relying on it.
