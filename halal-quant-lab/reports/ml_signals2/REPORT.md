# ML signal ranker v2 - which signals deserve the money first?

Generated 2026-11-02. 16,664 signals on 408 halal assets, 16,450 closed trades, 76 features (19 new: earnings timing, SEC growth and quality, sector strength, strength rank, crowding). Walk-forward from 2019 (each year's model only saw trades closed before that year); judged on 2021-today. Trades: half at +2 ATR, then stop at entry, else the rule's exit; costs included.

Pre-registered pass rule - US: R1 top-20% HIT rate >= bottom-20% + 8 points and higher average trade; R2 score-ordered slot portfolio beats random order on Sharpe and CAGR and in >= 4 of 6 years; R3 Sharpe >= simple ordering (weekly green first, then 60-day return). EGX: R1 + R2. Crypto: info only.

## 1. How well does it predict? (2021-today, AUC: 0.50 = coin flip)

| Market | Trades | HIT: new model | HIT: price-only model | SIZE: rank correlation with real result |
|---|---|---|---|---|
| US | 7,303 | 0.668 | 0.673 | -0.008 |
| EGX | 2,018 | 0.567 | 0.564 | +0.041 |
| Crypto | 548 | 0.566 | 0.560 | +0.057 |

## 2. Signals by score (fifths within each market, 2021-today)

| Market | Score fifth | Trades | HIT +2 ATR before exit | HIT before any close below entry | Win rate | Avg trade | Profit factor |
|---|---|---|---|---|---|---|---|
| US | 1 lowest | 1461 | 22% | 14% | 39% | +0.8% | 1.36 |
| US | 2 | 1460 | 28% | 16% | 40% | +0.9% | 1.39 |
| US | 3 | 1461 | 31% | 15% | 40% | +1.7% | 1.57 |
| US | 4 | 1460 | 48% | 18% | 50% | +0.9% | 1.21 |
| US | 5 highest | 1461 | 55% | 19% | 53% | +1.4% | 1.33 |
| EGX | 1 lowest | 404 | 50% | 16% | 50% | +4.9% | 1.98 |
| EGX | 2 | 403 | 60% | 20% | 56% | +5.0% | 2.23 |
| EGX | 3 | 404 | 63% | 20% | 59% | +4.1% | 2.02 |
| EGX | 4 | 403 | 62% | 20% | 59% | +5.4% | 2.29 |
| EGX | 5 highest | 404 | 66% | 25% | 63% | +7.3% | 3.10 |
| Crypto | 1 lowest | 110 | 52% | 25% | 51% | +1.6% | 1.17 |
| Crypto | 2 | 109 | 58% | 25% | 56% | +9.5% | 2.26 |
| Crypto | 3 | 110 | 54% | 22% | 47% | +0.0% | 1.00 |
| Crypto | 4 | 109 | 58% | 21% | 50% | +4.3% | 1.70 |
| Crypto | 5 highest | 110 | 69% | 30% | 68% | +23.3% | 6.65 |

## 3. Ranking test: fixed slots, new signals fill free slots each day (2021-today)

| Market | Slots | Ordering | Trades | Win rate | Avg trade | CAGR | Sharpe | Max DD | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| US | 10 | ML score | 443 | 46% | +0.8% | 5.0% | 0.39 | -33% | +19% | -16% | +15% | +17% | +7% | -8% |
| US | 10 | Simple: weekly green, then 60-day return | 412 | 44% | +2.0% | 10.4% | 0.67 | -23% | +21% | -12% | +25% | +15% | +31% | -12% |
| US | 10 | Random order (avg of 50) | 446 | 44% | +1.5% | 8.8% | 0.63 | -24% | +25% | -11% | +16% | +17% | +15% | -5% |
| EGX | 8 | ML score | 266 | 58% | +5.5% | 25.0% | 1.42 | -30% | +10% | +22% | +53% | +8% | +37% | +15% |
| EGX | 8 | Simple: weekly green, then 60-day return | 275 | 57% | +5.7% | 26.5% | 1.46 | -27% | +15% | +23% | +51% | +10% | +47% | +8% |
| EGX | 8 | Random order (avg of 50) | 278 | 56% | +4.9% | 22.2% | 1.27 | -31% | +14% | +23% | +42% | +5% | +39% | +8% |
| Crypto | 5 | ML score | 183 | 54% | +10.8% | 28.6% | 0.88 | -59% | +206% | -56% | +72% | +64% | -11% | +28% |
| Crypto | 5 | Simple: weekly green, then 60-day return | 182 | 53% | +10.9% | 28.8% | 0.88 | -56% | +206% | -53% | +73% | +63% | -13% | +25% |
| Crypto | 5 | Random order (avg of 50) | 183 | 53% | +10.8% | 27.8% | 0.85 | -59% | +200% | -57% | +72% | +66% | -10% | +25% |

## 4. Verdict (pre-registered)

| Market | R1 signal quality | R2 beats random | R3 beats simple | Result |
|---|---|---|---|---|
| US | yes | no (better in 1 of 6 years) | no | **FAIL** |
| EGX | yes | no (better in 3 of 6 years) | no | **FAIL** |
| Crypto | yes | no (better in 3 of 6 years) | no | **info only** |

Extra check - new data earns its place (US HIT AUC new > price-only): **no**.

## 5. What the US HIT model looks at most (permutation importance, in-sample, explanation only)

| Feature | New? | AUC drop when shuffled |
|---|---|---|
| is_dashboard |  | 0.1072 |
| dist200 |  | 0.0365 |
| mkt_vol20 |  | 0.0106 |
| mkt_up200 |  | 0.0069 |
| rev_accel | new | 0.0055 |
| sector_ret60 | new | 0.0042 |
| days_since_earn | new | 0.0039 |
| signals_5d | new | 0.0037 |
| ret120 |  | 0.0036 |
| atr_pct |  | 0.0034 |
| mkt_ret20 |  | 0.0032 |
| rev_growth | new | 0.0030 |
| rsi2 |  | 0.0029 |
| rsi14 |  | 0.0024 |
| sector_ret20 | new | 0.0024 |

## 6. Reading the result (plain language)

- The model CAN predict the +2 ATR hit (US AUC 0.67; top fifth hits 55% vs 22% for the bottom fifth) -
  but most of that comes from knowing which rule fired: the user's arrow signals hit +2 ATR far more often
  than 200-day-cross signals. High-hit signals had SMALLER gains, so ranking by it lowered US returns.
- The SIZE model failed (rank correlation about 0): how big a trade will be is not predictable here.
- The new SEC / earnings / sector data did not improve the predictions (US AUC 0.668 vs 0.673 price-only).
- EGX: the score separates good and bad signals (top fifth 63% win, +7.3% avg, PF 3.1 vs 50%, +4.9%, 2.0)
  and beat random order on CAGR and Sharpe, but only in 3 of 6 years and not the simple ordering.
- Not pre-registered, observed only: the simple ordering (weekly green first, then 60-day return) beat
  random order in the US and EGX. It would need its own test before being used.
