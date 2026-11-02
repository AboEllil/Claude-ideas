# Real liquidity and whale data - Fed liquidity, stablecoins, Bitcoin on-chain (pre-registered)

Generated 2026-11-02. 15,330 closed trades from 2016. Regimes and pass rules were fixed before the run (see run_liquidity2.py). Share of days ON since 2016: FED 48%, STABLE 72%, CHAIN 54%.

## Filter: Fed net liquidity above its 13-week average

| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| US | 2016-2020 | All | 4708 | 50% | +3.0% | 2.27 | 16.1% | 1.03 | -24% |
| US | 2016-2020 | Regime ON | 2167 | 52% | +4.3% | 2.87 | 15.1% | 1.03 | -22% |
| US | 2016-2020 | Regime OFF | 2541 | 48% | +1.9% | 1.79 | 10.9% | 0.94 | -19% |
| US | 2021-today | All | 7303 | 44% | +1.1% | 1.35 | 7.4% | 0.57 | -23% |
| US | 2021-today | Regime ON | 3461 | 46% | +1.3% | 1.43 | 8.3% | 0.67 | -17% |
| US | 2021-today | Regime OFF | 3842 | 43% | +1.0% | 1.29 | 5.5% | 0.45 | -24% |
| Crypto | 2016-2020 | All | 146 | 65% | +31.3% | 7.00 | 30.0% | 1.33 | -22% |
| Crypto | 2016-2020 | Regime ON | 85 | 73% | +46.3% | 13.62 | 23.4% | 1.32 | -16% |
| Crypto | 2016-2020 | Regime OFF | 61 | 54% | +10.4% | 2.41 | 6.6% | 0.59 | -21% |
| Crypto | 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| Crypto | 2021-today | Regime ON | 265 | 63% | +13.5% | 3.46 | 27.1% | 1.11 | -29% |
| Crypto | 2021-today | Regime OFF | 283 | 46% | +2.4% | 1.28 | -0.4% | 0.09 | -54% |
| EGX | 2016-2020 | All | 607 | 52% | +3.1% | 1.68 | 13.1% | 0.95 | -31% |
| EGX | 2016-2020 | Regime ON | 340 | 53% | +3.6% | 1.78 | 10.9% | 0.96 | -20% |
| EGX | 2016-2020 | Regime OFF | 267 | 51% | +2.5% | 1.55 | 3.8% | 0.40 | -24% |
| EGX | 2021-today | All | 2018 | 58% | +5.3% | 2.29 | 26.9% | 1.47 | -27% |
| EGX | 2021-today | Regime ON | 1113 | 58% | +4.9% | 2.18 | 20.4% | 1.25 | -23% |
| EGX | 2021-today | Regime OFF | 905 | 57% | +5.9% | 2.43 | 27.1% | 1.73 | -24% |

**Verdict: FAIL** (judged on US, Crypto; EGX shown for information).

## Filter: Stablecoin supply up over 30 days

| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| Crypto | 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| Crypto | 2021-today | Regime ON | 410 | 56% | +9.4% | 2.38 | 20.3% | 0.80 | -39% |
| Crypto | 2021-today | Regime OFF | 138 | 51% | +2.9% | 1.38 | 2.4% | 0.22 | -30% |
| Crypto | 2020 (info) | All | 70 | 77% | +47.3% | 18.11 | 144.8% | 2.64 | -15% |
| Crypto | 2020 (info) | Regime ON | 70 | 77% | +47.3% | 18.11 | 144.8% | 2.64 | -15% |
| Crypto | 2020 (info) | Regime OFF | 0 | nan% | +nan% | nan | 0.0% | 0.00 | 0% |

**Verdict: FAIL** (judged on Crypto; ).

## Filter: Bitcoin on-chain volume: 30-day avg above 90-day avg

| Market | Period | Signals | Trades | Win rate | Avg trade | Profit factor | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| Crypto | 2016-2020 | All | 146 | 65% | +31.3% | 7.00 | 30.0% | 1.33 | -22% |
| Crypto | 2016-2020 | Regime ON | 60 | 70% | +40.5% | 9.60 | 10.2% | 0.88 | -10% |
| Crypto | 2016-2020 | Regime OFF | 86 | 62% | +24.9% | 5.47 | 19.3% | 1.13 | -23% |
| Crypto | 2021-today | All | 548 | 55% | +7.7% | 2.11 | 23.5% | 0.81 | -49% |
| Crypto | 2021-today | Regime ON | 228 | 58% | +14.1% | 3.09 | 16.8% | 0.80 | -24% |
| Crypto | 2021-today | Regime OFF | 320 | 52% | +3.3% | 1.45 | 5.8% | 0.36 | -41% |

**Verdict: FAIL** (judged on Crypto; ).

## Timing: hold the market only when the regime is ON (else cash at 0%)

| Market | Period | Strategy | CAGR | Sharpe | Max DD | Time invested |
|---|---|---|---|---|---|---|
| US | 2016-2020 | Buy & hold | 28.3% | 1.21 | -39% | 100% |
| US | 2016-2020 | 200-day rule | 22.2% | 1.38 | -20% | 87% |
| US | 2016-2020 | FED ON | 16.6% | 0.91 | -32% | 46% |
| US | 2021-today | Buy & hold | 25.7% | 1.19 | -26% | 100% |
| US | 2021-today | 200-day rule | 18.5% | 1.11 | -32% | 84% |
| US | 2021-today | FED ON | 13.0% | 0.92 | -18% | 50% |
| Crypto | 2016-2020 | Buy & hold | 131.9% | 1.50 | -83% | 100% |
| Crypto | 2016-2020 | 200-day rule | 126.6% | 1.62 | -70% | 70% |
| Crypto | 2016-2020 | FED ON | 69.5% | 1.26 | -60% | 47% |
| Crypto | 2021-today | Buy & hold | 18.5% | 0.58 | -77% | 100% |
| Crypto | 2021-today | 200-day rule | 17.6% | 0.60 | -64% | 56% |
| Crypto | 2021-today | FED ON | 24.5% | 0.73 | -58% | 50% |
| Crypto | 2021-today | STABLE ON | 23.5% | 0.68 | -54% | 68% |
| Crypto | 2016-2020 | CHAIN ON | 78.3% | 1.26 | -74% | 55% |
| Crypto | 2021-today | CHAIN ON | 23.7% | 0.71 | -53% | 53% |

## Verdicts (pre-registered)

| Test | Result |
|---|---|
| FED filter | **FAIL** |
| STABLE filter | **FAIL** |
| CHAIN filter | **FAIL** |
| FED timing (US) | **FAIL** |
| FED timing (Crypto) | **FAIL** |
| STABLE timing (Crypto) | **PASS** |
| CHAIN timing (Crypto) | **FAIL** |

Latest readings: Fed net liquidity $5.74 trillion (OFF); stablecoins $298 billion (OFF); Bitcoin on-chain ON.

## Reading the result (plain language)

- By the pre-registered rules everything failed except "hold Bitcoin only while stablecoin supply is
  growing" (judged on 2021-today only, because the stablecoin data is unreliable before 2020 - weak evidence).
- The strongest pattern, though it did not pass: crypto signals taken while Fed net liquidity was rising won
  far more often in BOTH periods (73% vs 54% when falling in 2016-2020; 63% vs 46% in 2021-today) with much
  bigger average trades. The filter failed only because the portfolio Sharpe in 2016-2020 was 1.32 vs 1.33
  (fewer trades = less time invested). The Bitcoin on-chain filter shows the same picture (better trades,
  same or lower Sharpe).
- US: Fed liquidity raised the win rate by only 2 points (needed 3); EGX: no effect.
- No untouched history is left, so these can only be confirmed by tracking them forward from now.
