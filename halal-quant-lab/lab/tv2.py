"""Long-only ports of popular TradingView community scripts (daily bars).

Each function takes numpy arrays (o, h, l, c[, v]) and returns pos (1 long / 0 flat) decided at
the close; the engine trades at the next open. Rules follow each script's published signals with
default settings. Where a script only draws signals and has no exit, the exit used is stated.
"Short" signals mean "go flat" (halal: no short selling).
"""
import numpy as np
import pandas as pd

from .tv import _s, atr, ema, rma, rsi, sma, smc_state, supertrend, tr


def _cross_up(a, b):
    return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]


def _cross_dn(a, b):
    return np.r_[False, (a[1:] < b[1:]) & (a[:-1] >= b[:-1])]


def _state(entry, exit_):
    """Long from an entry bar until an exit bar."""
    pos = np.zeros(len(entry))
    for t in range(1, len(entry)):
        pos[t] = 0 if (pos[t - 1] and exit_[t]) else 1 if (pos[t - 1] or entry[t]) else 0
    return pos


def _hold(entry, bars, stop=None, c=None):
    """Long for `bars` bars after each entry (a new entry restarts the clock); optional stop level."""
    pos = np.zeros(len(entry))
    left, lvl = 0, np.nan
    for t in range(len(entry)):
        if left and stop is not None and c[t] < lvl:
            left = 0
        elif left:
            left -= 1
        if entry[t]:
            left = bars
            if stop is not None:
                lvl = stop[t]
        pos[t] = 1 if left else 0
    return pos


def _pivots(x, left, right, high=True):
    """Pivot value confirmed at bar t (the pivot itself is at t-right); NaN elsewhere."""
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(left + right, n):
        p = t - right
        w = x[p - left:t + 1]
        if (x[p] == w.max()) if high else (x[p] == w.min()):
            out[t] = x[p]
    return out


# ------------------------------------------------------------------ trend followers
def supertrend_classic(o, h, l, c):
    """SuperTrend (KivancOzbilgic): ATR 10, multiplier 3, hl2."""
    return (supertrend(h, l, c, atr(h, l, c, 10), 3.0) == 1).astype(float)


def ut_bot(o, h, l, c, key=1.0, n=10):
    """UT Bot Alerts (QuantNomad): ATR trailing stop, buy when close crosses above it."""
    nl = key * atr(h, l, c, n)
    st = np.zeros(len(c))
    for t in range(1, len(c)):
        p = st[t - 1]
        if np.isnan(nl[t]):
            st[t] = c[t]
        elif c[t] > p and c[t - 1] > p:
            st[t] = max(p, c[t] - nl[t])
        elif c[t] < p and c[t - 1] < p:
            st[t] = min(p, c[t] + nl[t])
        else:
            st[t] = c[t] - nl[t] if c[t] > p else c[t] + nl[t]
    return _state(_cross_up(c, st), _cross_dn(c, st))


def adx_di(o, h, l, c, n=14, th=20):
    """ADX and DI (BeikabuOyaji): long while +DI > -DI and ADX > 20."""
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = rma(tr(h, l, c), n)
    pdi, mdi = 100 * rma(pdm, n) / trs, 100 * rma(mdm, n) / trs
    adx = rma(100 * np.abs(pdi - mdi) / (pdi + mdi), n)
    return ((pdi > mdi) & (adx > th)).astype(float)


def ultimate_ma(o, h, l, c, n=20):
    """CM Ultimate MA (ChrisMoody): long while the 20 SMA is rising (its colour is green)."""
    m = sma(c, n)
    return np.r_[0.0, (m[1:] > m[:-1]).astype(float)]


def tma_overlay(o, h, l, c):
    """TMA Overlay (ArtyFXC): long while the smoothed MAs are stacked 21 > 50 > 200."""
    a, b, d = rma(c, 21), rma(c, 50), rma(c, 200)
    return ((a > b) & (b > d)).astype(float)


def macd_cross(o, h, l, c):
    """MacD Custom Indicator (ChrisMoody): MACD 12/26/9, long on signal-line cross up, exit on cross down."""
    m = ema(c, 12) - ema(c, 26)
    s = sma(m, 9)
    return _state(_cross_up(m, s), _cross_dn(m, s))


def macd_sma200(o, h, l, c):
    """MACD + SMA 200 (ChartArt): long when MACD histogram crosses above 0 above the 200 SMA;
    exit on the script's short signal (histogram crosses below 0 below the 200 SMA)."""
    m = ema(c, 12) - ema(c, 26)
    d = m - ema(m, 9)
    s2 = sma(c, 200)
    z = np.zeros(len(c))
    return _state(_cross_up(d, z) & (c > s2), _cross_dn(d, z) & (c < s2))


def market_structure(o, h, l, c, length=5):
    """Market Structure (EmreKb / nephew_sam_ style): long while the last break of structure was bullish."""
    trend = smc_state(h, l, c, length)[0]
    return (trend == 1).astype(float)


def trendline_breaks(o, h, l, c, length=14, mult=1.0):
    """Trendlines with Breaks (LuxAlgo): ATR-sloped lines from pivots; buy the upside break,
    exit on the downside break."""
    slope = atr(h, l, c, length) / length * mult
    ph, pl = _pivots(h, length, length, True), _pivots(l, length, length, False)
    T = len(c)
    up_l = dn_l = np.nan
    sp = sl_ = 0.0
    upos = dnos = 0
    buy, sell = np.zeros(T, bool), np.zeros(T, bool)
    for t in range(T):
        if not np.isnan(ph[t]):
            up_l, sp, upos = ph[t], slope[t], 0
        elif not np.isnan(up_l):
            up_l -= sp
            if c[t] > up_l - sp * length and upos == 0:
                upos, buy[t] = 1, True
        if not np.isnan(pl[t]):
            dn_l, sl_, dnos = pl[t], slope[t], 0
        elif not np.isnan(dn_l):
            dn_l += sl_
            if c[t] < dn_l + sl_ * length and dnos == 0:
                dnos, sell[t] = 1, True
    return _state(buy, sell)


def sr_breaks(o, h, l, c, v, n=15, vol_th=20):
    """Support and Resistance Levels with Breaks (LuxAlgo): buy when close breaks the last pivot
    resistance with volume oscillator > 20; exit when close breaks the last pivot support."""
    res = pd.Series(_pivots(h, n, n, True)).ffill().to_numpy()
    sup = pd.Series(_pivots(l, n, n, False)).ffill().to_numpy()
    osc = 100 * (ema(v, 5) - ema(v, 10)) / ema(v, 10)
    return _state(_cross_up(c, res) & (osc > vol_th), _cross_dn(c, sup))


# ------------------------------------------------------------------ oscillators / mean reversion
def wavetrend(o, h, l, c, n1=10, n2=21, ob=53, os_=-53):
    """WaveTrend (LazyBear): buy wt1/wt2 cross up below -53, sell cross down above +53."""
    ap = (h + l + c) / 3
    esa = ema(ap, n1)
    d = ema(np.abs(ap - esa), n1)
    wt1 = ema((ap - esa) / (0.015 * d), n2)
    wt2 = sma(wt1, 4)
    return _state(_cross_up(wt1, wt2) & (wt1 < os_), _cross_dn(wt1, wt2) & (wt1 > ob))


def williams_vix_fix(o, h, l, c, hold=10):
    """CM Williams Vix Fix (ChrisMoody): buy the fear spike (WVF above its upper Bollinger band or
    85% of its 50-bar high); the script has no exit, so hold 10 bars."""
    hc = _s(c).rolling(22).max().to_numpy()
    wvf = (hc - l) / hc * 100
    ub = sma(wvf, 20) + 2 * _s(wvf).rolling(20).std(ddof=0).to_numpy()
    rh = _s(wvf).rolling(50).max().to_numpy() * 0.85
    return _hold((wvf >= ub) | (wvf >= rh), hold)


def bb_rsi(o, h, l, c):
    """Bollinger + RSI Double Strategy (ChartArt): RSI(6) crosses above 50 AND close crosses above
    the lower BB(200, 2); exit on the opposite signal."""
    r = rsi(c, 6)
    b = sma(c, 200)
    d = 2 * _s(c).rolling(200).std(ddof=0).to_numpy()
    f = np.full(len(c), 50.0)
    return _state(_cross_up(r, f) & _cross_up(c, b - d), _cross_dn(r, f) & _cross_dn(c, b + d))


def fib_bollinger(o, h, l, c, v):
    """Fibonacci Bollinger Bands (Rashad): VWMA(200) +/- 3 stdev; buy when price climbs back above
    the lowest band, exit at the middle (VWMA). Exit rule is ours - the script only draws bands."""
    vw = _s(c * v).rolling(200).sum().to_numpy() / _s(v).rolling(200).sum().to_numpy()
    lo = vw - 3 * _s(c).rolling(200).std(ddof=0).to_numpy()
    return _state(_cross_up(c, lo), _cross_up(c, vw))


def nadaraya_watson(o, h, l, c, bw=8.0, mult=3.0, window=500):
    """Nadaraya-Watson Envelope (LuxAlgo), NON-repainting endpoint version: Gaussian kernel h=8,
    envelope = 3 x mean absolute error. Buy on a cross below the lower band, sell on a cross above
    the upper band. (The default chart mode REPAINTS - past signals are redrawn with future data.)"""
    w = np.exp(-np.arange(window) ** 2 / (2 * bw ** 2))
    num = np.convolve(c, w)[:len(c)]
    den = np.convolve(np.ones(len(c)), w)[:len(c)]
    yhat = num / den
    yhat[:window] = np.nan
    mae = sma(np.abs(c - yhat), window - 1) * mult
    return _state(_cross_dn(c, yhat - mae), _cross_up(c, yhat + mae))


def divergence(o, h, l, c, n=5, hold=20):
    """Divergence for Many Indicators (LonesomeTheBlue), RSI(14): price makes a lower pivot low while
    RSI makes a higher low -> buy; hold 20 bars, stop below the pivot low."""
    r = rsi(c, 14)
    pl = _pivots(l, n, n, False)
    entry = np.zeros(len(c), bool)
    stop = np.full(len(c), np.nan)
    last_p = last_r = np.nan
    for t in range(len(c)):
        if not np.isnan(pl[t]):
            rr = r[t - n]
            if not np.isnan(last_p) and pl[t] < last_p and rr > last_r:
                entry[t], stop[t] = True, pl[t]
            last_p, last_r = pl[t], rr
    return _hold(entry, hold, stop, c)


def candle_patterns(o, h, l, c, hold=10):
    """Candlestick Patterns (repo32): bullish engulfing or hammer in a downtrend (close < SMA50);
    hold 10 bars (the script has no exit)."""
    body = np.abs(c - o)
    down = c < sma(c, 50)
    po, pc = np.r_[np.nan, o[:-1]], np.r_[np.nan, c[:-1]]
    engulf = (pc < po) & (c > o) & (c >= po) & (o <= pc)
    lower = np.minimum(o, c) - l
    upper = h - np.maximum(o, c)
    hammer = (lower >= 2 * body) & (upper <= 0.3 * body + 1e-12) & (body > 0)
    return _hold(down & (engulf | hammer), hold)


# ------------------------------------------------------------------ smart-money / liquidity
def order_blocks(o, h, l, c, v, length=5, max_hold=20):
    """Order Block Detector (LuxAlgo) / Order Block (wugamlo) style: a bullish OB forms at a volume
    pivot while the market state is 'down' (top = hl2, bottom = low of that bar). Buy the first
    retest; exit on a close below the OB (mitigation) or after 20 bars."""
    up = _s(h).rolling(length).max().to_numpy()
    dn = _s(l).rolling(length).min().to_numpy()
    phv = _pivots(np.nan_to_num(v), length, length, True)
    T = len(c)
    os_ = 0
    top = btm = np.nan
    pos = np.zeros(T)
    held = 0
    for t in range(length, T):
        if h[t - length] > up[t]:
            os_ = 0
        elif l[t - length] < dn[t]:
            os_ = 1
        if not np.isnan(phv[t]) and os_ == 1:
            top, btm = (h[t - length] + l[t - length]) / 2, l[t - length]
        if pos[t - 1]:
            held += 1
            pos[t] = 0 if (c[t] < btm or held >= max_hold) else 1
            if pos[t] == 0:
                top = btm = np.nan
        elif not np.isnan(top) and l[t] <= top and c[t] >= btm:
            pos[t], held = 1, 0
        elif not np.isnan(btm) and c[t] < btm:
            top = btm = np.nan
    return pos


def fvg_retest(o, h, l, c, max_hold=20):
    """FVG (nephew_sam_): buy the first retest of the latest bullish fair value gap; exit on a close
    below the gap or after 20 bars."""
    T = len(c)
    top = btm = np.nan
    pos = np.zeros(T)
    held = 0
    stop = np.nan
    for t in range(2, T):
        if pos[t - 1]:
            held += 1
            pos[t] = 0 if (c[t] < stop or held >= max_hold) else 1
        elif not np.isnan(top) and l[t] <= top and c[t] >= btm:
            pos[t], held, stop = 1, 0, btm
            top = btm = np.nan                      # a gap is traded once
        elif not np.isnan(btm) and c[t] < btm:
            top = btm = np.nan
        if l[t] > h[t - 2]:                         # newest bullish gap becomes the active zone
            top, btm = l[t], h[t - 2]
    return pos


def liquidity_sweep(o, h, l, c, n=14, max_hold=20):
    """Liquidity Swings / Buyside & Sellside Liquidity (LuxAlgo): price wicks below the last swing
    low (sell-side liquidity grab) and closes back above it -> buy; stop at the sweep low,
    exit after 20 bars."""
    lvl = pd.Series(_pivots(l, n, n, False)).ffill().to_numpy()
    sweep = (l < lvl) & (c > lvl)
    return _hold(sweep, max_hold, stop=l, c=c)


STRATEGIES = {
    # name: (function, needs_volume, family)
    "SuperTrend (KivancOzbilgic)": (supertrend_classic, False, "trend"),
    "UT Bot Alerts (QuantNomad)": (ut_bot, False, "trend"),
    "ADX and DI (BeikabuOyaji)": (adx_di, False, "trend"),
    "CM Ultimate MA (ChrisMoody)": (ultimate_ma, False, "trend"),
    "TMA Overlay (ArtyFXC)": (tma_overlay, False, "trend"),
    "MacD Custom (ChrisMoody)": (macd_cross, False, "trend"),
    "MACD + SMA 200 (ChartArt)": (macd_sma200, False, "trend"),
    "Market Structure (EmreKb / nephew_sam_)": (market_structure, False, "structure"),
    "Trendlines with Breaks (LuxAlgo)": (trendline_breaks, False, "breakout"),
    "S/R Levels with Breaks (LuxAlgo)": (sr_breaks, True, "breakout"),
    "WaveTrend (LazyBear)": (wavetrend, False, "oscillator"),
    "Williams Vix Fix (ChrisMoody)": (williams_vix_fix, False, "mean reversion"),
    "Bollinger + RSI (ChartArt)": (bb_rsi, False, "mean reversion"),
    "Fibonacci Bollinger (Rashad)": (fib_bollinger, True, "mean reversion"),
    "Nadaraya-Watson Envelope (LuxAlgo)": (nadaraya_watson, False, "mean reversion"),
    "Divergence RSI (LonesomeTheBlue)": (divergence, False, "mean reversion"),
    "Candlestick Patterns (repo32)": (candle_patterns, False, "pattern"),
    "Order Blocks (LuxAlgo / wugamlo)": (order_blocks, True, "smart money"),
    "FVG (nephew_sam_)": (fvg_retest, False, "smart money"),
    "Liquidity Swings / Sweeps (LuxAlgo)": (liquidity_sweep, False, "smart money"),
}
