# Insider buying (SEC Form 4) as an add-on to the halal strategy

Generated 2026-10-31. Source: SEC Insider Transactions Data Sets (free), open-market purchases (code P) >= $25,000 by officers, directors or 10% owners, filed 2006-01 to 2026-03.

**2738 qualifying purchases in 90 of the 100 stocks.** Large caps rarely see insider buying.

## E1 - event study: excess return after insider buying (vs equal-weight halal universe)

| Group | Horizon (days) | Events | Mean excess | Median excess | Beat universe | t-stat |
|---|---|---|---|---|---|---|
| All events | 20 | 909 | -0.52% | -0.81% | 45% | -2.06 |
| All events | 60 | 909 | +0.10% | -1.21% | 47% | 0.19 |
| All events | 120 | 908 | +0.12% | -1.82% | 46% | 0.14 |
| Cluster buys (2+ insiders in 30 days) | 20 | 207 | +0.18% | -0.63% | 47% | 0.28 |
| Cluster buys (2+ insiders in 30 days) | 60 | 207 | +1.45% | +0.49% | 51% | 1.03 |
| Cluster buys (2+ insiders in 30 days) | 120 | 207 | +2.09% | +0.89% | 53% | 1.07 |
| Since 2019 | 20 | 289 | -0.53% | -0.80% | 44% | -1.18 |
| Since 2019 | 60 | 289 | -0.24% | -2.20% | 42% | -0.24 |
| Since 2019 | 120 | 288 | -1.14% | -3.81% | 43% | -0.68 |

**E1 verdict: FAIL** (rule: 60-day mean excess > 0 and t > 2)

## Top 20

Share of stock-days with insider buying in the prior 365 days: 19.8%

| Strategy | 2010-2018 | 2019-today | 2010-today | Avg invested | Trades |
|---|---|---|---|---|---|
| A  baseline (1% risk) | 10.7% / 0.88 / -21% | 28.9% / 1.38 / -26% | 18.8% / 1.14 / -26% | 61% | 774 |
| E2 2% risk if insider bought (180d) | 11.4% / 0.89 / -23% | 29.1% / 1.38 / -28% | 19.3% / 1.14 / -28% | 63% | 744 |
| E3 entries only after insider buying (365d) | 3.2% / 0.71 / -5% | 6.4% / 0.91 / -12% | 4.7% / 0.80 / -12% | 19% | 208 |

## Ranks 21-100

Share of stock-days with insider buying in the prior 365 days: 28.6%

| Strategy | 2010-2018 | 2019-today | 2010-today | Avg invested | Trades |
|---|---|---|---|---|---|
| A  baseline (1% risk) | 14.8% / 1.02 / -16% | 19.4% / 1.12 / -19% | 16.9% / 1.07 / -19% | 89% | 1145 |
| E2 2% risk if insider bought (180d) | 14.3% / 0.95 / -20% | 23.5% / 1.25 / -18% | 18.5% / 1.10 / -20% | 90% | 1070 |
| E3 entries only after insider buying (365d) | 9.3% / 0.73 / -22% | 17.2% / 1.16 / -14% | 12.9% / 0.94 / -22% | 72% | 841 |

## Verdicts (ranks 21-100, both halves)

- **E2: FAIL** - 2010-2018: Sharpe 1.02 -> 0.95, drawdown -15.9% -> -20.5%; 2019-today: Sharpe 1.12 -> 1.25, drawdown -19.2% -> -18.2%
- **E3: FAIL** - 2010-2018: Sharpe 1.02 -> 0.73, drawdown -15.9% -> -21.6%; 2019-today: Sharpe 1.12 -> 1.16, drawdown -19.2% -> -13.7%

## Conclusion
Insider open-market buying does **not** add a reliable edge for these large-cap halal stocks:
- After a typical insider purchase the stock did no better than the other halal stocks (60 days: +0.10%, t = 0.19),
  and since 2019 slightly worse. This matches the literature: the effect is concentrated in small companies.
- Cluster buys (2+ insiders within 30 days) look better (+1.45% over 60 days, +2.09% over 120) but are not
  statistically significant (t ~ 1.0, 207 events) - not enough to trade on.
- Doubling risk on insider-bought names helped after 2019 but hurt in 2010-2018; using insider buying as a filter
  removed too many good trades. Both fail the pre-registered rule.
Not added to the monitor. Insider data is still useful as a manual check (Quiver's free site or SEC EDGAR).
Note: the SEC publishes each quarter's file with a delay (latest available here: 2026 Q1).
