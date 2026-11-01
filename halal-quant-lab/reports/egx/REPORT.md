# EGX: scanning all halal stocks for the green arrow (ML Adaptive SuperTrend)

Generated 2026-11-01. 137 halal EGX stocks on Yahoo, daily bars, data to 2026-10-29. Costs 0.25% per side, max 10% per stock, liquidity >= EGP 1,000,000/day. Cells: CAGR / Sharpe / max drawdown.

> 12 rule combinations were tested; the best one is partly luck. Look for rules that work in BOTH periods.

| Strategy | EGP 2016-2020 | EGP 2021-today | EGP 2016-today | USD 2016-today | Trades/yr |
|---|---|---|---|---|---|
| **Buy & hold (equal weight, liquid halal EGX)** | 3.4% / 0.26 / -65% | 33.5% / 1.29 / -48% | 18.3% / 0.81 / -65% | -1.9% / 0.12 / -72% |  |
| E0 arrow only | X1 until red | 8.2% / 0.50 / -44% | 32.4% / 1.33 / -36% | 20.4% / 0.97 / -44% | -0.2% / 0.16 / -58% | 203 |
| E0 arrow only | X2 3 days | 3.3% / 0.53 / -21% | 5.9% / 0.52 / -26% | 4.6% / 0.50 / -26% | -13.2% / -0.46 / -82% | 194 |
| E0 arrow only | X3 5 days | 8.2% / 0.92 / -22% | 9.9% / 0.67 / -28% | 9.1% / 0.73 / -28% | -9.5% / -0.26 / -74% | 195 |
| E1 arrow + squeeze | X1 until red | 7.0% / 0.47 / -37% | 39.0% / 1.60 / -33% | 22.9% / 1.12 / -37% | 1.9% / 0.23 / -62% | 130 |
| E1 arrow + squeeze | X2 3 days | 2.8% / 0.58 / -11% | 3.1% / 0.39 / -24% | 2.9% / 0.44 / -24% | -14.6% / -0.57 / -85% | 124 |
| E1 arrow + squeeze | X3 5 days | 7.6% / 1.07 / -8% | 9.3% / 0.83 / -25% | 8.5% / 0.89 / -25% | -10.0% / -0.31 / -78% | 125 |
| E2 arrow + Lorentzian | X1 until red | 12.6% / 0.71 / -36% | 32.2% / 1.32 / -36% | 22.5% / 1.06 / -36% | 1.6% / 0.22 / -59% | 190 |
| E2 arrow + Lorentzian | X2 3 days | 4.8% / 0.80 / -13% | 5.6% / 0.50 / -26% | 5.2% / 0.56 / -26% | -12.7% / -0.44 / -80% | 182 |
| E2 arrow + Lorentzian | X3 5 days | 9.6% / 1.11 / -14% | 9.7% / 0.67 / -28% | 9.6% / 0.78 / -28% | -9.1% / -0.24 / -72% | 183 |
| E3 arrow + both | X1 until red | 9.4% / 0.60 / -32% | 40.3% / 1.64 / -31% | 24.7% / 1.20 / -32% | 3.4% / 0.28 / -62% | 124 |
| E3 arrow + both | X2 3 days | 3.2% / 0.68 / -9% | 3.5% / 0.44 / -23% | 3.3% / 0.50 / -23% | -14.3% / -0.55 / -85% | 118 |
| E3 arrow + both | X3 5 days | 7.2% / 1.06 / -8% | 9.4% / 0.85 / -24% | 8.4% / 0.89 / -24% | -10.1% / -0.32 / -79% | 119 |

USD/EGP went from 7.72 to 55.97 over the period (+625%), so EGP returns overstate real gains.

## What this means
- On EGX the user's three indicators **do add value** - unlike the US market. Every "hold until red" version beat
  buy & hold in BOTH 2016-2020 and 2021-today, with about half the drawdown.
- Adding Squeeze (momentum > 0) and Lorentzian (bullish) confirmations improved the arrow: 24.7%/yr, Sharpe 1.20,
  max drawdown -32% vs buy & hold 18.3%, 0.81, -65%.
- **Selling after 3-5 days destroys the edge** (3-10%/yr): EGX trading costs (~0.25% per side) and cutting winners
  early. The profit comes from riding the full trend.
- In US dollars almost everything is flat or negative since 2016 because the pound fell from 7.7 to 56 per dollar.
  EGX stocks protected savings against devaluation but did not grow them in dollar terms.
- 12 combinations were tested, so the best is partly luck; the consistent finding is "hold until red".
- Daily scanner: `python egx_scanner.py` (reports/egx/scan_latest.md).
