"""Vectorised technical indicators. Inputs are DataFrames (dates x tickers) or Series."""
import numpy as np
import pandas as pd


def sma(x, n):
    return x.rolling(n, min_periods=n).mean()


def ema(x, n):
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder(x, n):
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(close, n=14):
    d = close.diff()
    up = wilder(d.clip(lower=0), n)
    down = wilder((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / down)


def true_range(high, low, close):
    prev = close.shift(1)
    return np.fmax(high - low, np.fmax((high - prev).abs(), (low - prev).abs()))


def atr(high, low, close, n=14):
    return wilder(true_range(high, low, close), n)


def adx(high, low, close, n=14):
    """Average Directional Index - trend strength regardless of direction."""
    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = wilder(true_range(high, low, close), n)
    plus_di = 100 * wilder(plus_dm, n) / tr
    minus_di = 100 * wilder(minus_dm, n) / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return wilder(dx, n)


def bollinger_z(close, n=20):
    """How many standard deviations price is from its n-day mean."""
    return (close - sma(close, n)) / close.rolling(n, min_periods=n).std()


def donchian_high(high, n):
    """Highest high of the previous n days (excludes today, so a close above it is a breakout)."""
    return high.rolling(n, min_periods=n).max().shift(1)


def roc(close, n):
    return close / close.shift(n) - 1


def momentum(close, lookback=252, skip=21):
    """Classic 12-1 momentum: return over `lookback` days, skipping the last `skip` days."""
    return close.shift(skip) / close.shift(lookback) - 1


def obv(close, volume):
    return (np.sign(close.diff()).fillna(0) * volume.fillna(0)).cumsum()


def realized_vol(close, n=60):
    return close.pct_change().rolling(n, min_periods=n).std() * np.sqrt(252)


def cs_rank(df):
    """Cross-sectional percentile rank per day (1.0 = best of the universe)."""
    return df.rank(axis=1, pct=True)
