# Signal order, liquidity filter and whale-footprint filter (pre-registered)

Generated 2026-11-02. 15,330 closed trades from 2016 (dashboard rule + the user's rule; half at +2 ATR then stop at entry; costs included). Rules and pass conditions were fixed before the run (see run_order_liquidity.py).

## A. Simple order vs random order (fixed slots)

| Market | Slots | Period | Simple: CAGR / Sharpe / maxDD | Random (avg of 50): CAGR / Sharpe / maxDD | Simple better? |
|---|---|---|---|---|---|
| US | 5 | 2016-2020 | 11.9% / 0.74 / -28% | 15.5% / 0.99 / -21% | no |
| US | 5 | 2021-today | 6.5% / 0.43 / -32% | 7.0% / 0.47 / -28% | no |
| US | 10 (main) | 2016-2020 | 12.5% / 0.87 / -21% | 16.3% / 1.13 / -18% | no |
| US | 10 (main) | 2021-today | 9.4% / 0.61 / -24% | 7.3% / 0.54 / -24% | yes |
| US | 20 | 2016-2020 | 16.7% / 1.24 / -18% | 17.1% / 1.26 / -18% | no |
| US | 20 | 2021-today | 9.8% / 0.74 / -23% | 6.3% / 0.52 / -23% | yes |
| EGX | 5 | 2016-2020 | 17.2% / 1.10 / -31% | 16.2% / 1.06 / -33% | yes |
| EGX | 5 | 2021-today | 21.7% / 1.08 / -31% | 24.7% / 1.24 / -30% | no |
| EGX | 8 (main) | 2016-2020 | 12.1% / 0.92 / -39% | 13.8% / 1.05 / -35% | no |
| EGX | 8 (main) | 2021-today | 29.9% / 1.62 / -27% | 24.6% / 1.40 / -30% | yes |
| EGX | 20 | 2016-2020 | 8.0% / 0.85 / -19% | 7.9% / 0.85 / -19% | no |
| EGX | 20 | 2021-today | 27.5% / 1.87 / -18% | 25.3% / 1.76 / -18% | yes |
| Crypto | 5 (main) | 2016-2020 | 30.7% / 1.07 / -41% | 30.6% / 1.07 / -41% | yes |
| Crypto | 5 (main) | 2021-today | 30.9% / 0.92 / -56% | 30.4% / 0.90 / -59% | yes |
| Crypto | 20 | 2016-2020 | 15.1% / 1.28 / -12% | 15.1% / 1.28 / -12% | no |
| Crypto | 20 | 2021-today | 19.6% / 0.94 / -34% | 19.6% / 0.94 / -34% | no |

**A verdict: FAIL** - US fails, EGX fails (crypto, info only: better in both periods).

## B. Liquidity (risk-on) filter: 2 of 3 of weak dollar, credit appetite, calm VIX

| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| US | 2016-2020 | All | 4708 | 50% | +3.0% | 2.27 | 16.1% | 1.03 | -24% |
| US | 2016-2020 | Filter on | 3028 | 50% | +2.7% | 2.16 | 13.8% | 1.13 | -18% |
| US | 2016-2020 | Filter off | 1680 | 51% | +3.7% | 2.44 | 14.0% | 0.93 | -23% |
| US | 2021-today | All | 7303 | 44% | +1.1% | 1.35 | 7.4% | 0.57 | -23% |
| US | 2021-today | Filter on | 4732 | 43% | +1.0% | 1.30 | 5.3% | 0.44 | -27% |
| US | 2021-today | Filter off | 2571 | 47% | +1.4% | 1.47 | 5.8% | 0.47 | -19% |
| EGX | 2016-2020 | All | 607 | 52% | +3.1% | 1.68 | 13.1% | 0.95 | -31% |
| EGX | 2016-2020 | Filter on | 450 | 51% | +2.7% | 1.57 | 8.4% | 0.73 | -28% |
| EGX | 2016-2020 | Filter off | 157 | 54% | +4.4% | 2.05 | 8.5% | 0.94 | -14% |
| EGX | 2021-today | All | 2018 | 58% | +5.3% | 2.29 | 26.9% | 1.47 | -27% |
| EGX | 2021-today | Filter on | 1371 | 57% | +4.7% | 2.14 | 27.1% | 1.56 | -22% |
| EGX | 2021-today | Filter off | 647 | 60% | +6.7% | 2.60 | 20.8% | 1.40 | -26% |
| Crypto | 2016-2020 | All | 146 | 65% | +31.3% | 7.00 | 30.0% | 1.33 | -22% |
| Crypto | 2016-2020 | Filter on | 106 | 62% | +35.5% | 7.90 | 18.1% | 1.14 | -17% |
| Crypto | 2016-2020 | Filter off | 40 | 72% | +20.1% | 4.73 | 11.4% | 0.91 | -15% |
| Crypto | 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| Crypto | 2021-today | Filter on | 389 | 55% | +8.3% | 2.24 | 17.0% | 0.71 | -42% |
| Crypto | 2021-today | Filter off | 159 | 53% | +6.5% | 1.84 | 4.2% | 0.32 | -28% |

**Verdict: FAIL** - passes in: no market.

## C. Whale-footprint filter: Chaikin Money Flow (20) > 0.05

| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| US | 2016-2020 | All | 4708 | 50% | +3.0% | 2.27 | 16.1% | 1.03 | -24% |
| US | 2016-2020 | Filter on | 2133 | 51% | +2.8% | 2.08 | 13.4% | 0.94 | -22% |
| US | 2016-2020 | Filter off | 2575 | 50% | +3.3% | 2.45 | 18.1% | 1.14 | -22% |
| US | 2021-today | All | 7303 | 44% | +1.1% | 1.35 | 7.4% | 0.57 | -23% |
| US | 2021-today | Filter on | 3463 | 46% | +1.2% | 1.35 | 6.1% | 0.48 | -26% |
| US | 2021-today | Filter off | 3840 | 43% | +1.1% | 1.36 | 6.8% | 0.55 | -24% |
| EGX | 2016-2020 | All | 607 | 52% | +3.1% | 1.68 | 13.1% | 0.95 | -31% |
| EGX | 2016-2020 | Filter on | 264 | 56% | +4.3% | 1.95 | 12.7% | 1.15 | -14% |
| EGX | 2016-2020 | Filter off | 343 | 49% | +2.3% | 1.49 | 5.0% | 0.46 | -30% |
| EGX | 2021-today | All | 2018 | 58% | +5.3% | 2.29 | 26.9% | 1.47 | -27% |
| EGX | 2021-today | Filter on | 919 | 57% | +6.0% | 2.43 | 30.2% | 1.65 | -26% |
| EGX | 2021-today | Filter off | 1099 | 58% | +4.8% | 2.17 | 22.1% | 1.32 | -27% |
| Crypto | 2016-2020 | All | 146 | 65% | +31.3% | 7.00 | 30.0% | 1.33 | -22% |
| Crypto | 2016-2020 | Filter on | 112 | 63% | +37.2% | 8.08 | 22.5% | 1.32 | -22% |
| Crypto | 2016-2020 | Filter off | 34 | 71% | +11.9% | 3.35 | 7.8% | 0.83 | -14% |
| Crypto | 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| Crypto | 2021-today | Filter on | 435 | 56% | +9.2% | 2.35 | 22.3% | 0.84 | -43% |
| Crypto | 2021-today | Filter off | 113 | 48% | +2.1% | 1.28 | 1.0% | 0.14 | -18% |

**Verdict: FAIL** - passes in: no market.

Risk-on share of signal days: 68%. Signals with CMF > 0.05: 48%.

## Reading the result (plain language)

- A: the simple order is NOT reliably better than random. It looked good in 2021-today but lost to random
  in the untouched 2016-2020 period in both the US and EGX - the earlier observation was luck.
- B: the liquidity (risk-on) filter removed good trades as often as bad ones; it did not help anywhere.
- C: failed the pre-registered rule, with one note: on EGX, signals with money flow > 0.05 had a higher
  average trade and Sharpe in BOTH periods (2016-2020: 1.15 vs 0.95, max DD -14% vs -31%; 2021-today:
  1.65 vs 1.47) but the win rate did not rise in 2021-today. No untouched data is left to confirm it, so
  it can only be confirmed by tracking it forward from now (paper trading).
