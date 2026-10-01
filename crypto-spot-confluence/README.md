# Spot Confluence Regime (SCR) — crypto spot indicator for TradingView (Pine v6)

Long-only **spot** (no shorts, no leverage). Signals on the **Daily** chart, with a **Weekly** trend filter.

| File | Purpose |
|---|---|
| [`SCR_indicator.pine`](SCR_indicator.pine) | Indicator with signals, visuals, dashboard and alerts |
| [`SCR_strategy.pine`](SCR_strategy.pine) | `strategy()` copy with the same logic, for backtesting (fees + slippage, date window, risk-based sizing) |

> This is a research tool, not financial advice. Nothing here promises profit. The defaults are reasonable starting points, not optimised values. Validate them yourself with the test plan in §7.

---

## 1. Phase 1: Study (the idea space)

### 1.1 Notes by family

**Trend**
- **EMA/SMA (cross or price vs MA).** Strength: simple and robust, and it keeps you in big trends. Weakness: whipsaws in ranges and lags turns. Best in: persistent trends.
- **KAMA / adaptive MAs.** Strength: the speed follows the efficiency ratio, so it is fast in clean trends and nearly flat in chop. Weakness: one extra concept to learn, and it can still be late at V-bottoms. Best in: mixed regimes.
- **Supertrend / ATR trail.** Strength: a clear stop-and-reverse level based on volatility. Weakness: gets whipsawed in chop, and the multiplier is sensitive. Best in: trends with orderly pullbacks.
- **Ichimoku.** Strength: shows trend, momentum and support in one view, and the weekly cloud is a useful filter. Weakness: many parameters, a lot of lag, and the "future" cloud is easy to misuse. Best in: slow, large trends.
- **ADX/DMI.** Strength: measures trend strength regardless of direction, which makes it a good regime input. Weakness: slow, and it peaks after the move. Best in: telling trend apart from range.
- **Donchian breakout.** Strength: the classic turtle edge. Trends in crypto are fat-tailed and breakouts capture them. Weakness: many false breakouts and a low win rate. Best in: volatility expansion.
- **Linear regression channel / slope.** Strength: gives a statistical slope and deviation bands. Weakness: depends on the window and fits the past. Best in: smooth trends.

**Momentum / oscillators**
- **RSI.** Strength: bounded and familiar, and it doubles as a regime tool (it stays at 40–80 in uptrends). Weakness: fixed 30/70 levels fail in trends. Best in: ranges, or trend pullbacks if used with care.
- **Stoch RSI.** Strength: very fast timing. Weakness: extremely noisy, with near-random flips on the daily chart. Best in: tight ranges.
- **MACD.** Strength: combines trend and momentum, and the histogram slope shows acceleration. Weakness: lags, and it is redundant with EMAs (it is built from EMAs). Best in: trending markets.
- **CCI.** Strength: unbounded, so it catches thrusts. Weakness: noisy and needs thresholds tuned per coin. Best in: breakouts.
- **Divergences (RSI/MACD vs price).** Strength: warns early of exhaustion. Weakness: needs a pivot to confirm, so it lags, and divergences can "keep diverging" in strong trends. Best in: range edges and trend ends.
- **ROC / volatility-normalised momentum.** Strength: comparable across coins and a direct measure of the time-series momentum premium. Weakness: needs a volatility denominator to make sense. Best in: trends.

**Volatility**
- **ATR.** Strength: the natural unit for stops and sizing. Weakness: not directional. Best in: every regime, as a ruler.
- **Bollinger Bands.** Strength: adaptive envelope, and %B or bandwidth are useful. Weakness: band "touches" mean opposite things in trends and in ranges. Best in: ranges (mean reversion) and squeezes.
- **Keltner Channels.** Strength: ATR-based, so smoother than BB. Weakness: same directional ambiguity. Best in: trend pullbacks.
- **Squeeze (BB inside KC, or BB-width percentile).** Strength: compression tends to come before expansion. Weakness: it does not tell you the direction. Best in: the transition from range to trend.
- **Volatility regime (ATR% percentile).** Strength: tells you when your other tools stop working, and lets you size down. Weakness: classification lags. Best in: risk control.

**Volume / flow**
- **OBV.** Strength: cumulative flow, and OBV divergences can be useful. Weakness: on its own scale it is unbounded and arbitrary. Best in: confirming breakouts.
- **VWAP / anchored VWAP.** Strength: shows the average cost of participants since an anchor. Weakness: session VWAP means little on daily crypto, and the anchor choice is subjective. Best in: intraday trading, or anchored to swing points.
- **CVD (cumulative volume delta).** Strength: shows aggressor flow. Weakness: needs tick or intrabar data, differs by exchange, and gets expensive in Pine on the daily chart. Best in: intraday trading.
- **Relative volume (RVOL).** Strength: separates real breakouts from drift. Weakness: noisy around exchange listings and wash trading. Best in: breakouts and capitulation.
- **Up/down volume ratio.** Strength: a simple way to read accumulation vs distribution. Weakness: says nothing about price level. Best in: trends.
- **Volume profile.** Strength: shows support and resistance where volume traded. Weakness: heavy computation, a subjective range, and it is approximated on TradingView. Best in: range trading.

**Market structure / Smart Money Concepts**
- **BOS (break of structure).** Strength: an objective trend continuation trigger once pivots are confirmed. Weakness: the pivot confirmation delay. Best in: trends.
- **CHoCH (change of character).** Strength: catches early reversals. Weakness: a high false-positive rate. Best in: trend ends.
- **Order blocks.** Strength: zones you can act on. Weakness: the definitions are subjective, they tend to be overfit, and they produce too many zones. Best in: ranges and retests.
- **Liquidity sweeps (stop runs).** Strength: a wick below an obvious low that closes back inside is a well-understood failure-of-breakdown pattern. Weakness: in a real breakdown the price never closes back. Best in: range lows and pullbacks in uptrends.
- **Fair value gaps.** Strength: mark imbalances. Weakness: on 24/7 crypto daily charts they are frequent and mostly noise. Best in: lower timeframes.

**Statistical / ML-style**
- **Lorentzian / kNN classification.** Strength: finds non-linear patterns. Weakness: high overfitting risk, opaque, and many public versions repaint or leak. Best in: research only.
- **Z-score of price / returns.** Strength: gives a statistical extreme in comparable units. Weakness: assumes stationarity, which crypto violates. Best in: ranges.
- **Hurst exponent.** Strength: in theory tells trending from mean-reverting. Weakness: very noisy on short windows. Best in: regime detection (the efficiency ratio is a cheaper proxy).
- **Regime detection (HMM, volatility clusters, ADX + ER).** Strength: lets the tool switch its logic. Weakness: the classification lags. Best in: all regimes, as a meta layer.

**Cycle / seasonality / market-wide**
- **Halving cycle / seasonality.** Strength: has historical narrative support. Weakness: tiny sample (3 or 4 cycles) and not tradable daily. Best in: macro context only.
- **BTC trend filter for alts.** Strength: alts have high beta to BTC, and most alt drawdowns happen while BTC trends down. Weakness: drops alt-specific rallies. Best in: alts.
- **BTC dominance / TOTAL / TOTAL3.** Strength: shows rotation (alt season). Weakness: data symbols vary, and it is noisy and slow. Best in: choosing which assets to trade.

### 1.2 Summary table

| Idea | What it measures | Lag | False-signal risk | Best regime |
|---|---|---|---|---|
| EMA/SMA | Average price trend | High | High in ranges | Trend |
| KAMA (adaptive MA) | Noise-adjusted trend | Medium (adaptive) | Medium | Mixed |
| Supertrend / ATR trail | Volatility-band trend flip | Medium | High in chop | Trend |
| Ichimoku | Trend + equilibrium + S/R | High | Medium | Slow trend |
| ADX/DMI | Trend strength (no direction) | High | Low as a filter | Regime detection |
| Donchian breakout | New N-bar extremes | Low | High (low win rate) | Expansion |
| Regression channel | Statistical slope/deviation | Medium | Medium | Smooth trend |
| RSI | Momentum, bounded | Low | High in trends | Range |
| Stoch RSI | Fast RSI oscillation | Very low | Very high | Tight range |
| MACD | EMA spread + acceleration | Medium-high | Medium | Trend |
| CCI | Deviation from mean | Low | High | Breakout |
| Divergence | Momentum vs price disagreement | High (pivots) | High | Exhaustion |
| Vol-normalised momentum | Return ÷ noise (t-stat) | Medium | Low-medium | Trend |
| ATR | Volatility unit | Low | n/a (ruler) | All |
| Bollinger | Price vs σ envelope | Low | Medium | Range / squeeze |
| Keltner | Price vs ATR envelope | Low | Medium | Trend pullbacks |
| Squeeze | Volatility compression | Low | Medium (no direction) | Range → trend |
| Vol regime (ATR% rank) | Volatility state | Medium | Low (as a filter) | Risk control |
| OBV | Cumulative signed volume | Medium | Medium | Trend confirm |
| VWAP / anchored VWAP | Volume-weighted cost basis | Low | Medium | Intraday / swing anchors |
| CVD | Aggressor buy-sell delta | Low | Medium (data quality) | Intraday |
| Relative volume | Participation vs normal | None | Medium | Breakout / capitulation |
| Up/down volume ratio | Accumulation vs distribution | Medium | Medium | Trend |
| Volume profile | Volume by price | n/a | Medium | Range |
| BOS | Break of confirmed swing high | Medium (pivot) | Medium | Trend |
| CHoCH | First counter-structure break | Medium | High | Reversal |
| Order blocks | Last opposing candle before impulse | Medium | High (subjective) | Range / retest |
| Liquidity sweep + reclaim | Failed breakdown below swing low | Low | Medium | Range low / pullback |
| Fair value gap | 3-candle imbalance | Low | High on daily crypto | Lower TFs |
| Lorentzian / kNN | Similarity to past patterns | Low | Very high (overfit) | Research only |
| Z-score | Distance from mean in σ | Low | High (non-stationary) | Range |
| Hurst exponent | Persistence vs mean reversion | High | High (estimation noise) | Regime |
| Efficiency ratio | Net move ÷ path length | Medium | Low-medium | Regime |
| Halving / seasonality | Calendar effects | Very high | Very high (tiny sample) | Macro context |
| BTC trend filter | Market beta direction | Medium | Low (as a filter) | Alts |
| Dominance / TOTAL3 | Capital rotation | High | Medium | Asset selection |

---

## 2. Phase 2: Create (new / hybrid ideas)

| # | Idea | Logic | Why it should work | How to test |
|---|---|---|---|---|
| 1 | **Volatility-normalised momentum (t-stat)** | `ln(C/C[N]) / (σ_daily·√N)` gives a trend z-score, mapped to 0–1. | Raw ROC means different things on BTC and on a meme coin. Dividing by noise makes it comparable and filters out drift. This is the time-series-momentum premium with a sensible denominator. | Compare against raw ROC and RSI>50 as the momentum component on the same coins. Measure forward 10/20-day returns by t-stat bucket (monotonic?). |
| 2 | **Regime-switching rule set** | ADX + efficiency ratio → Trend. ATR% percentile ≥ 85 → High-vol. Anything else → Range. Each regime has its own BUY threshold, and Range only allows sweep-and-reclaim setups. | One rule set cannot fit both trends and chop. Asking more of the signal in poor regimes cuts false signals where they cluster. | Ablation: one threshold for all regimes vs per-regime thresholds. Compare profit factor (PF) and expectancy by regime. |
| 3 | **Agreement gate across uncorrelated families** | Count the components that score ≥ 0.6. Require at least 3 of 5 on top of the weighted score. | A high weighted score can come from one maxed-out component. Requiring breadth makes the system lean on independent evidence. | Compare minAgree = 1…5. Check trade count vs expectancy. Look for a plateau, not a spike. |
| 4 | **Sweep + volume-exhaustion reclaim** | Low pierces the last confirmed swing low, the bar closes back above it, and relative volume is ≥ 1.2. | Stops below obvious lows provide liquidity. A high-volume failed breakdown is often seller capitulation. | Event study: forward returns after the event vs after random bars and vs after plain swing-low touches. |
| 5 | **Directional squeeze release** | BB-width percentile ≤ 20 within the last 10 bars, then width expands and the close is above the BB basis. | Compression comes before expansion, and the basis filter picks the direction. | Event study plus ablation of the volatility component. |
| 6 | **Stretch-aware momentum** | The momentum score is halved when the close is more than 3 ATR above the trend line. | Buying blow-off extensions gives poor reward/risk and wide stops. | Compare entry efficiency (MAE in R) with and without the penalty. |
| 7 | **Demand thrust** | 60% from the up-volume share over 20 bars, 40% from the strongest up-bar RVOL in the last 3 bars. | Separates accumulation-driven moves from low-volume drift. | Ablation, plus a check of the flow score on exchanges with and without wash trading. |
| 8 | **Structure-anchored adaptive stop** | Stop = the higher of (swing low − 0.25 ATR) and (close − 2.5 ATR), never closer than 1 ATR. The trail only starts after +1R. | The stop sits where the thesis is wrong, not at an arbitrary distance, and an early trail does not choke the trade. | Compare against a fixed-ATR stop. Measure average R, win rate and MAE distribution. |
| 9 | **Divergence quality score** | Score a bullish RSI divergence by depth (Δprice ÷ ATR), span (bars), RSI gap, and declining volume into the second low. | Most divergences fail. The quality ones (deep, with declining volume) should not. | Event study by quality quintile. **Not included in v1** (see §3). |
| 10 | **Volatility-adaptive threshold** | `buyTh = base + k·(1 − ER)`, a continuous version of idea 2. | Smoother than discrete regimes. | Compare against idea 2. Rejected for v1: one more fitted parameter (`k`) and harder to read. |
| 11 | **Alt relative-strength gate** | Only buy alts when ALT/BTC is above its 50-day EMA. | Avoids alts that rise less than BTC with more risk. | Compare alt results with and without it. Optional extension. |

---

## 3. Phase 3: Select and design

### 3.1 What was chosen and why (low correlation)

| Component (weight) | Measures | Ideas used | Why it is not redundant |
|---|---|---|---|
| **Trend** (25) | Direction | KAMA trend line (price above it, slope) + weekly EMA21 | Path-smoothed price level |
| **Momentum** (20) | Speed relative to noise | #1 t-stat + #6 stretch penalty | Uses the return/σ ratio, not price level |
| **Volume** (20) | Participation | #7 demand thrust | Uses volume only, which is independent of price math |
| **Structure** (20) | Swing geometry | Higher lows, BOS, #4 sweep & reclaim | Discrete, event-based |
| **Volatility** (15) | Compression → expansion | #5 squeeze release | Uses the second moment, not direction |
| *Regime layer* | Meta | #2 ADX + ER + ATR% rank | Changes thresholds rather than adding score |
| *Gates* | Market | Weekly trend, BTC > EMA50 (alts) | Hard filters, kept out of the score so they cannot be "averaged away" |
| *Breadth* | Meta | #3 agreement ≥ 3/5 | Stops one component from dominating |

**Rejected:** RSI, Stoch RSI, MACD and CCI (redundant with the t-stat momentum, and noisier). Ichimoku (lag, many parameters). Supertrend (redundant with KAMA plus the ATR trail). VWAP (no natural daily anchor). CVD (data quality on daily spot). Volume profile (heavy and subjective). Order blocks and FVGs (subjective, too many zones). Lorentzian/kNN (overfitting and leak risk). Hurst (estimation noise; the efficiency ratio is a cheaper proxy). Seasonality (sample too small). Dominance/TOTAL3 (symbol availability; better used for picking which assets to trade). Divergence quality (#9) is promising but lags by pivot confirmation and overlaps with the momentum component. It is the first candidate for v2 if ablation shows momentum adds little.

### 3.2 Score

Each component returns a value from 0 to 1:

```
score = 100 · Σ(wᵢ · componentᵢ) / Σwᵢ          (weights editable, auto-normalised)
agree = count(componentᵢ ≥ 0.6)                  (0..5)
```

### 3.3 Regime

| Regime | Rule | Background | BUY threshold | Allowed setups | Risk |
|---|---|---|---|---|---|
| High-vol | ATR% percentile (252) ≥ 85 | orange | 80 | all (toggle) | × 0.5 |
| Trend | not High-vol, ADX ≥ 20 and ER(20) ≥ 0.25 | green | 65 | all | × 1 |
| Range | otherwise | grey | 75 | sweep & reclaim only (toggle) | × 1 |

The trend regime is direction-agnostic: green background means "trending". The dashboard and the trend-line colour show the direction.

### 3.4 BUY rule (evaluated only on a closed daily bar, when flat)

All of the following must be true:
1. `score ≥ regime threshold` and `agree ≥ 3`.
2. A **trigger** happens on this bar: the score crosses up through the threshold, **or** a break of structure, **or** a liquidity sweep & reclaim.
3. Weekly close is above the weekly EMA21 (the previous closed week).
4. BTC is above its daily EMA50 (skipped when the chart is BTC).
5. The regime is allowed (Range additionally needs a recent sweep).
6. At least 3 bars of cooldown since the last EXIT.

The trigger requirement is what keeps signals rare: a high score alone only puts the dashboard in the "Armed" state.

### 3.5 EXIT rules (whichever comes first)

1. **Stop:** initial stop = the higher of (swing low − 0.25 ATR) and (entry − 2.5 ATR), never closer than 1 ATR.
2. **Target:** at entry + 2.5R. The default "Partial 50% + trail" takes half there, moves the stop to breakeven and trails the rest. "Full exit" closes everything at the target.
3. **Trailing stop:** after +1R, the stop becomes highest close − 3 ATR (it only ratchets up).
4. **Thesis break:** close below the trend line **and** score < 35.
5. **HTF flip:** the weekly trend turns bearish (toggle).

### 3.6 Non-repainting design

- Every signal, label, alert and state change sits inside `barstate.isconfirmed`.
- Pivots only become available `pvR` bars after the swing, so they are never redrawn.
- **Weekly data (a stated assumption):** you asked for `lookahead_off`. A plain `lookahead_off` call has no future leak, but in real time it returns the still-forming week, so mid-week values can differ from what history showed. The default mode therefore uses TradingView's documented non-repainting form, `request.security(…, expr[1], lookahead = barmerge.lookahead_on)`. Combined with `[1]` this only ever reads the last closed week, so it behaves the same in history and live. The raw `lookahead_off` mode is still available in the inputs.
- The BTC filter uses the same timeframe with `lookahead_off`, which is final at bar close.

---

## 4. Indicator: [`SCR_indicator.pine`](SCR_indicator.pine)

**Visuals:**
- One BUY or EXIT label per signal, showing the score. The tooltip gives the regime, agreement, entry, stop, target and position size. EXIT labels give the reason, P/L % and R.
- Regime background: green for trend, grey for range, orange for high-vol.
- A single KAMA trend line, coloured by its direction.
- Entry, stop and target lines with risk/reward shading, drawn only while a trade is open.
- A dashboard showing regime, trend, momentum, volume, structure, volatility, score / threshold / agreement, signal state, risk per trade, and filters.
- **Minimal mode** shows only the labels and the trend line.

**Alerts:**
- `alertcondition` "SCR BUY" / "SCR EXIT" send JSON with TradingView placeholders.
- `alert()` ("Any alert() function call") sends richer JSON:

```json
{"symbol":"BINANCE:ETHUSDT","timeframe":"1D","signal":"BUY","score":78,"price":3120.55,"sl":2890.10,"tp":3696.67,"regime":"TREND","agree":4,"reason":"score>=65","time":1727827200000}
```

Signals are `BUY`, `TP1` and `EXIT`. Point the alert webhook at your Telegram relay, for example a small Cloudflare Worker or n8n flow that forwards the body to `sendMessage`.

## 5. Strategy: [`SCR_strategy.pine`](SCR_strategy.pine)

- The BUY/EXIT logic is the same as the indicator. Partial targets use two `strategy.exit` orders.
- **Costs:** `commission_value = 0.2 %` per side, which is 0.1 % commission plus 0.1 % slippage. Pine's `slippage` setting counts ticks, which means something different on every coin, so the slippage is folded into the commission. To test other costs, change it in *Properties*.
- `process_orders_on_close = true`, so entries fill at the signal close, as the indicator assumes.
- Sizing is risk-based: equity × risk % ÷ stop distance, capped at 98 % of equity, since spot means no leverage.
- Start and End date inputs let you run in-sample and out-of-sample splits.

---

## 6. Recommended starting settings (all on 1D)

These are starting points only. Validate them with §7 before trusting any of them.

| Setting | BTC | ETH | Large-cap alts (SOL, BNB, XRP, LINK…) | Small / volatile alts |
|---|---|---|---|---|
| BTC filter | n/a (auto) | On | On | On |
| HTF EMA | 21 | 21 | 21 | 21 |
| BUY threshold T / R / HV | 65 / 75 / 80 | 65 / 75 / 80 | 70 / 80 / 85 | 70 / 80 / 85 |
| Allow Range entries | On | On | On | **Off** |
| Allow High-vol entries | On | On | On | **Off** |
| Min agreement | 3 | 3 | 3 | 4 |
| Initial stop (ATR) | 2.5 | 2.5 | 3.0 | 3.0 |
| Trail (ATR) | 3.0 | 3.0 | 3.5 | 3.5 |
| Target (R) / mode | 2.5 / Partial | 2.5 / Partial | 3.0 / Partial | 2.0 / Full exit |
| Over-stretch (ATR) | 3.0 | 3.0 | 3.5 | 4.0 |
| Sweep RVOL ≥ | 1.2 | 1.2 | 1.5 | 1.8 |
| Risk per trade | 1.0 % | 1.0 % | 0.75 % | 0.5 % |
| Weights T/M/V/S/Vol | 25/20/20/20/15 | 25/20/20/20/15 | 30/20/15/20/15 | 30/20/10/25/15 |

For alts, volume is down-weighted because of wash trading and listing distortions. Use the exchange with the deepest spot book (e.g. Binance/Coinbase USDT or USD pairs) and at least 3 years of daily history so the 252-bar volatility rank is warm.

---

## 7. Honest weaknesses and test plan

### 7.1 Weaknesses
- **Lag by design.** The weekly filter, pivot confirmation (3 bars) and KAMA mean it will miss the first 15–30 % of a new bull leg and will not catch bottoms.
- **Low trade count.** On daily charts, expect roughly 3–10 trades per coin per year. Statistics per coin are weak, so pool across coins.
- **Regime thresholds are discrete.** A bar can flip regimes on a small ADX change, and the BUY threshold jumps with it.
- **Gaps through stops.** Crypto is 24/7 but news wicks are huge. Stops can fill well below the level, and the backtest only partly models this (a fill at the open if it gaps).
- **Volume quality.** Exchange volume on alts can be wash-traded. The flow component can be fooled.
- **Correlated portfolio.** Running it on 10 alts is not 10 independent bets. In a BTC sell-off they all stop out together.
- **Parameter count.** About 40 inputs. Most should stay at their defaults. Tuning many of them on one coin is overfitting.
- **Survivorship.** Backtesting today's top coins ignores the ones that died. Real results will be worse.
- **Weights are judgement, not fitted.** They are a prior to be tested, not proven optimal.
- **Fills at the close.** The strategy fills at the daily close. A live trader acting on the alert gets the next price. Costs are set conservatively to compensate, but that is not a guarantee.

### 7.2 Test plan (anti-overfitting)
1. **Universe:** BTC, ETH, plus 8–12 alts from different sectors (SOL, BNB, XRP, ADA, LINK, AVAX, DOGE, LTC, DOT, MATIC/POL), plus at least 2 dead or collapsed coins (e.g. LUNA, FTT) to see the damage.
2. **History:** at least 4 years, ideally 2018 to now. That covers the 2018 bear, the 2019 chop, the 2020–21 bull, the 2022 crash, and the 2023–25 recovery.
3. **Freeze defaults first.** Run all coins with the default settings before changing anything. This is the honest baseline.
4. **Benchmarks:** buy & hold, and a simple "close above the 50-day EMA and the weekly trend" system. SCR has to beat the simple one on risk-adjusted terms, or it is not worth its complexity.
5. **Walk-forward:** optimise at most 3 parameters (BUY thresholds, stop ATR, trail ATR) on 24 months, test on the next 6 months, roll forward 6 months, and repeat. Report only the stitched out-of-sample results. Use the strategy's Start and End inputs.
6. **Robustness:** vary each key parameter by ±20 %. The results should form a plateau. A sharp peak means overfitting.
7. **Ablation:** set each weight to 0 in turn. Drop any component whose removal does not hurt out-of-sample expectancy.
8. **Cost stress:** rerun with commission at 0.3 % and 0.5 % per side. If the edge disappears, it was never there.
9. **Monte Carlo:** shuffle the trade order 1,000 times and look at the 95th-percentile drawdown, not the backtest drawdown.
10. **Metrics:** expectancy in R, profit factor, maximum drawdown, time in market, number of trades (aim for at least 100 pooled), and return / max drawdown. Do not judge by net profit alone.
11. **Forward test:** paper trade with alerts for at least 3 months before risking capital, and compare live signals with the backtest bar for bar to confirm there is no repainting.
