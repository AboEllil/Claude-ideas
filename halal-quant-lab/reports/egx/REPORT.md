# EGX: scanning all halal stocks for the green arrow (ML Adaptive SuperTrend)

Generated 2026-11-01. 137 halal EGX stocks on Yahoo, daily bars, data to 2026-10-29. Costs 0.25% per side, max 10% per stock, liquidity >= EGP 1,000,000/day. Cells: CAGR / Sharpe / max drawdown.

> 15 rule combinations were tested; the best one is partly luck. Look for rules that work in BOTH periods.

| Strategy | EGP 2016-2020 | EGP 2021-today | EGP 2016-today | USD 2016-today | Trades/yr |
|---|---|---|---|---|---|
| **Buy & hold (equal weight, liquid halal EGX)** | 3.4% / 0.26 / -65% | 33.5% / 1.29 / -48% | 18.3% / 0.81 / -65% | -1.9% / 0.12 / -72% |  |
| E0 arrow only | X1 until red | 8.2% / 0.50 / -44% | 32.4% / 1.33 / -36% | 20.4% / 0.97 / -44% | -0.2% / 0.16 / -58% | 203 |
| E0 arrow only | X3 5 days | 8.2% / 0.92 / -22% | 9.9% / 0.67 / -28% | 9.1% / 0.73 / -28% | -9.5% / -0.26 / -74% | 195 |
| E0 arrow only | X4 squeeze turns dark | 19.0% / 1.51 / -19% | 21.0% / 1.08 / -31% | 20.1% / 1.20 / -31% | -0.4% / 0.14 / -57% | 196 |
| E1 arrow + squeeze > 0 | X1 until red | 7.0% / 0.47 / -37% | 39.0% / 1.60 / -33% | 22.9% / 1.12 / -37% | 1.9% / 0.23 / -62% | 130 |
| E1 arrow + squeeze > 0 | X3 5 days | 7.6% / 1.07 / -8% | 9.3% / 0.83 / -25% | 8.5% / 0.89 / -25% | -10.0% / -0.31 / -78% | 125 |
| E1 arrow + squeeze > 0 | X4 squeeze turns dark | 10.6% / 1.17 / -12% | 22.0% / 1.44 / -24% | 16.5% / 1.31 / -24% | -3.4% / 0.00 / -62% | 126 |
| E3 arrow + squeeze > 0 + Lorentzian > 0 | X1 until red | 9.4% / 0.60 / -32% | 40.3% / 1.64 / -31% | 24.7% / 1.20 / -32% | 3.4% / 0.28 / -62% | 124 |
| E3 arrow + squeeze > 0 + Lorentzian > 0 | X3 5 days | 7.2% / 1.06 / -8% | 9.4% / 0.85 / -24% | 8.4% / 0.89 / -24% | -10.1% / -0.32 / -79% | 119 |
| E3 arrow + squeeze > 0 + Lorentzian > 0 | X4 squeeze turns dark | 10.6% / 1.23 / -11% | 21.9% / 1.46 / -23% | 16.4% / 1.34 / -23% | -3.4% / 0.00 / -62% | 120 |
| U1 arrow + BRIGHT green squeeze (your rule) | X1 until red | 7.1% / 0.48 / -37% | 38.1% / 1.58 / -34% | 22.5% / 1.11 / -37% | 1.6% / 0.22 / -62% | 127 |
| U1 arrow + BRIGHT green squeeze (your rule) | X3 5 days | 7.6% / 1.08 / -9% | 8.4% / 0.77 / -26% | 8.1% / 0.86 / -26% | -10.4% / -0.33 / -79% | 123 |
| U1 arrow + BRIGHT green squeeze (your rule) | X4 squeeze turns dark | 10.5% / 1.17 / -13% | 22.0% / 1.45 / -24% | 16.4% / 1.31 / -24% | -3.4% / 0.00 / -62% | 123 |
| U2 arrow + BRIGHT green + Lorentzian arrow (high confidence) | X1 until red | 9.5% / 0.71 / -19% | 35.4% / 1.51 / -35% | 22.5% / 1.19 / -35% | 1.6% / 0.22 / -59% | 70 |
| U2 arrow + BRIGHT green + Lorentzian arrow (high confidence) | X3 5 days | 6.0% / 1.20 / -5% | 9.1% / 1.05 / -19% | 7.6% / 1.07 / -19% | -10.7% / -0.37 / -79% | 68 |
| U2 arrow + BRIGHT green + Lorentzian arrow (high confidence) | X4 squeeze turns dark | 8.1% / 1.27 / -7% | 19.7% / 1.64 / -15% | 14.1% / 1.46 / -15% | -5.3% / -0.10 / -68% | 68 |

USD/EGP went from 7.72 to 55.97 over the period (+625%), so EGP returns overstate real gains.

## Update: the user's exact entry rule
Entry = AlgoAlpha green arrow + Squeeze momentum BRIGHT green (positive and rising); a Lorentzian green arrow
in the last 5 days = high confidence (U2). New exit tested: sell when the squeeze turns dark green (X4).
- "Bright green" vs "any green" makes almost no difference at the arrow (U1 ~ E1).
- Exit choice matters most:
  - hold until red: ~22-25%/yr EGP, Sharpe ~1.1-1.2, drawdown -32% to -37% (most return)
  - sell when the squeeze turns dark: U2 = 14.1%/yr, **Sharpe 1.46, drawdown only -15%** (smoothest);
    arrow-only + this exit = 20.1%/yr, Sharpe 1.20, -31%, strong in both periods (19% and 21%)
  - sell after a fixed 5 days: clearly worst (~8%/yr)
- The scanner now applies this exact rule (`egx_scanner.py`).
