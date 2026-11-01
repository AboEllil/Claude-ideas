# 24 TradingView community indicators tested on halal stocks

Generated 2026-11-01. Daily bars 2010-today, default settings, signals at the close, orders at the next open, 5 bps per side, long-only. Cells: **CAGR / Sharpe / max drawdown**. Sorted by Sharpe of the rotation portfolio on ranks 21-100 (the fairer universe).

| # | Indicator | Type | Ranks 21-100 rotation | Ranks 21-100 sleeves | Top 20 rotation | In market | Trades/stock/yr | Win rate | Beats B&H Sharpe (of 80 stocks) |
|---|---|---|---|---|---|---|---|---|---|
|  | **Buy & hold** | benchmark | 21.1% / 1.08 / -36% | 22.0% / 1.12 / -37% | 33.2% / 1.17 / -38% | 99% |  |  |  |
| 1 | Market Structure (EmreKb / nephew_sam_) | structure | 19.3% / 1.10 / -28% | 9.4% / 0.95 / -14% | 23.2% / 1.07 / -41% | 58% | 3.0 | 46% | 1 |
| 2 | Trendlines with Breaks (LuxAlgo) | breakout | 19.6% / 1.08 / -34% | 11.0% / 1.11 / -13% | 27.2% / 1.21 / -38% | 60% | 2.6 | 44% | 12 |
| 3 | MACD + SMA 200 (ChartArt) | trend | 20.2% / 1.07 / -35% | 12.9% / 1.04 / -24% | 27.9% / 1.13 / -36% | 68% | 0.8 | 45% | 9 |
| 4 | Nadaraya-Watson Envelope (LuxAlgo) | mean reversion | 22.1% / 1.07 / -39% | 11.1% / 0.90 / -32% | 22.0% / 0.96 / -32% | 43% | 1.0 | 78% | 10 |
| 5 | ML Adaptive SuperTrend (AlgoAlpha) | trend | 18.7% / 1.07 / -27% | 10.3% / 1.06 / -12% | 22.9% / 1.09 / -39% | 57% | 3.5 | 46% | 10 |
| 6 | SuperTrend (KivancOzbilgic) | trend | 18.4% / 1.07 / -26% | 10.0% / 1.04 / -13% | 23.6% / 1.12 / -37% | 57% | 3.5 | 46% | 8 |
| 7 | TMA Overlay (ArtyFXC) | trend | 19.3% / 1.06 / -30% | 10.7% / 1.01 / -16% | 26.7% / 1.13 / -35% | 62% | 1.0 | 45% | 4 |
| 8 | Bollinger + RSI (ChartArt) | mean reversion | 22.3% / 1.05 / -50% | 7.4% / 1.02 / -13% | 13.7% / 0.98 / -27% | 26% | 0.2 | 91% | 10 |
| 9 | Divergence RSI (LonesomeTheBlue) | mean reversion | 14.9% / 1.03 / -21% | 2.7% / 0.89 / -4% | 5.2% / 0.62 / -15% | 9% | 1.3 | 51% | 2 |
| 10 | WaveTrend (LazyBear) | oscillator | 21.4% / 1.01 / -47% | 9.1% / 0.96 / -16% | 12.8% / 0.72 / -34% | 30% | 0.7 | 82% | 10 |
| 11 | Order Blocks (LuxAlgo / wugamlo) | smart money | 17.7% / 1.01 / -27% | 3.5% / 0.89 / -6% | 8.3% / 0.73 / -20% | 21% | 5.0 | 36% | 4 |
| 12 | Liquidity Swings / Sweeps (LuxAlgo) | smart money | 17.2% / 1.00 / -26% | 3.4% / 0.94 / -9% | 6.8% / 0.68 / -31% | 14% | 3.0 | 36% | 6 |
| 13 | FVG (nephew_sam_) | smart money | 17.0% / 0.99 / -28% | 7.0% / 0.91 / -10% | 18.2% / 0.95 / -34% | 42% | 10.2 | 35% | 4 |
| 14 | Smart Money Concepts (LuxAlgo) | smart money | 16.9% / 0.97 / -30% | 5.3% / 0.99 / -8% | 15.3% / 0.93 / -27% | 29% | 1.5 | 31% | 5 |
| 15 | Williams Vix Fix (ChrisMoody) | mean reversion | 18.5% / 0.95 / -37% | 10.5% / 0.82 / -34% | 26.3% / 1.12 / -33% | 46% | 5.9 | 65% | 7 |
| 16 | Candlestick Patterns (repo32) | pattern | 16.6% / 0.88 / -41% | 3.6% / 0.67 / -15% | 7.8% / 0.66 / -32% | 15% | 3.1 | 57% | 2 |
| 17 | S/R Levels with Breaks (LuxAlgo) | breakout | 15.3% / 0.86 / -28% | 3.3% / 0.81 / -7% | 13.3% / 1.09 / -17% | 21% | 0.4 | 49% | 0 |
| 18 | CM Ultimate MA (ChrisMoody) | trend | 13.7% / 0.84 / -26% | 9.0% / 0.91 / -16% | 23.5% / 1.10 / -36% | 58% | 11.6 | 39% | 2 |
| 19 | MacD Custom (ChrisMoody) | trend | 13.9% / 0.82 / -25% | 9.0% / 0.90 / -15% | 18.0% / 0.90 / -34% | 50% | 10.2 | 42% | 3 |
| 20 | UT Bot Alerts (QuantNomad) | trend | 14.0% / 0.81 / -25% | 6.5% / 0.65 / -19% | 19.5% / 0.93 / -34% | 56% | 16.0 | 40% | 0 |
| 21 | ADX and DI (BeikabuOyaji) | trend | 12.4% / 0.79 / -31% | 4.7% / 0.79 / -10% | 16.7% / 0.99 / -23% | 35% | 6.2 | 40% | 2 |
| 22 | Fibonacci Bollinger (Rashad) | mean reversion | 10.2% / 0.75 / -27% | 2.7% / 0.70 / -6% | 2.1% / 0.50 / -10% | 4% | 0.1 | 91% | 3 |
| 23 | Squeeze Momentum (LazyBear) | breakout | 3.9% / 0.37 / -24% | 0.7% / 0.29 / -6% | 3.3% / 0.45 / -22% | 11% | 4.4 | 43% | 1 |
| 24 | Lorentzian Classification (jdehorty) | machine learning | 3.4% / 0.34 / -36% | 1.0% / 0.48 / -5% | 2.4% / 0.42 / -14% | 7% | 4.5 | 53% | 4 |

Not testable as buy/sell rules (drawing or session tools): ICT Killzones, Sessions (LuxAlgo), Swing High/Low (Patternsmart), Support/Resistance (ChartPrime, LonesomeTheBlue channels), Breakout Probability (Zeiierman), RelativeValue. Paid/locked (code not public): LuxAlgo Signals & Overlays, LuxAlgo Price Action Concepts. Covered by another test: Smart Money Concepts (AlgoAlpha), ICT Concepts (LuxAlgo), Buyside & Sellside Liquidity (LuxAlgo), CM_Ultimate_MA_MTF, Order Block Detector.

## Verdict
- **None of the 24 beat simply holding the stocks.** The best had about the same Sharpe as buy & hold (1.07-1.10 vs
  1.08) with smaller drawdowns, and each beat buy & hold's Sharpe on at most 12 of 80 individual stocks.
- **Trend/structure tools are the useful group:** Market Structure, Trendlines with Breaks, MACD + SMA 200, both
  SuperTrends and TMA. They roughly halve single-stock drawdowns (sleeves: -12% to -24% vs -37%).
- **High win rate does not mean good:** Bollinger + RSI (91% wins), WaveTrend (82%) and Nadaraya-Watson (78%) win often
  but rarely trade, and when capital is concentrated in their few signals the drawdowns reach -39% to -50%.
- **Nadaraya-Watson repaints** in its default chart mode (it redraws past signals with future data); that is why it
  looks perfect on a chart. The non-repainting version tested here is ordinary.
- **Fast-flipping tools lose to costs and whipsaws:** UT Bot (16 trades/stock/yr), CM Ultimate MA, MacD Custom, ADX/DI.
- **Smart-money tools (OB, FVG, liquidity sweeps, SMC)** are low-exposure and below buy & hold on every measure.
- **Squeeze Momentum and Lorentzian Classification are the weakest** (Sharpe ~0.35 in rotation).
