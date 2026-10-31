"""Python ports of four popular TradingView scripts, plus long-only strategy rules.

Every function takes one stock's daily OHLC as numpy arrays and returns a target
position array `pos` (1 = long, 0 = flat) decided at the CLOSE of each bar. The
engine (`lab/single.py`) trades it at the NEXT bar's open, so nothing here may look
at future bars. Halal constraint: long-only, so every "short" signal means "flat".

1. Lorentzian Classification (jdehorty) - k-nearest-neighbours classifier using
   Lorentzian distance ln(1+|x-y|) on 5 normalised features (RSI14, WaveTrend 10/11,
   CCI20, ADX20, RSI9). Approximate-NN loop over the last 2000 bars, skipping every
   4th bar, keeping 8 neighbours and raising the distance bar to the 75th percentile.
   Filters: volatility (ATR1 > ATR10), regime (Kalman-like slope >= -0.1), kernel
   regression trend (rational quadratic h=8 r=8 x=25). Trades are held 4 bars.
   NOTE: the original labels each bar with the move over the PREVIOUS 4 bars and
   (as published) maps "price rose" to SHORT. `lorentzian(..., fixed=True)` pairs
   features at bar j-4 with the forward move j-4 -> j instead (a proper forecast).
2. Machine Learning Adaptive SuperTrend (AlgoAlpha) - k-means (3 clusters) on the
   last 100 ATR(10) values; the cluster nearest today's ATR sets the SuperTrend ATR
   (factor 3). Long while the SuperTrend is bullish.
3. Squeeze Momentum (LazyBear) - Bollinger Bands inside Keltner Channels = squeeze.
   Momentum = linreg(close - mean(Donchian mid, SMA), 20). (Faithful to the original,
   the BB deviation uses the KC multiplier 1.5.) Long when the squeeze fires with
   positive, rising momentum; exit when momentum turns down.
4. Smart Money Concepts (LuxAlgo-style) - swing pivots, break of structure (BOS) /
   change of character (CHoCH), bullish order blocks (lowest candle between the
   broken swing high and the break), fair value gaps (3-candle imbalances), premium /
   discount zones. Long on a retest of an unmitigated bullish OB or FVG while
   structure is bullish and price is in the discount half; exit on a close below
   the zone or a bearish structure break.
"""
import numpy as np
import pandas as pd
from numba import njit


# ---------------------------------------------------------------- helpers (pine ta.*)
def _s(x):
    return pd.Series(x)


def rma(x, n):
    return _s(x).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy()


def ema(x, n):
    return _s(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x, n):
    return _s(x).rolling(n, min_periods=n).mean().to_numpy()


def tr(h, l, c):
    pc = np.r_[np.nan, c[:-1]]
    return np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))


def atr(h, l, c, n):
    return rma(tr(h, l, c), n)


def rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up, dn = rma(np.clip(d, 0, None), n), rma(np.clip(-d, 0, None), n)
    return 100 - 100 / (1 + up / dn)


def linreg(x, n):
    """ta.linreg(x, n, 0): value of the least-squares line at the latest bar."""
    s = _s(x)
    t = np.arange(n)
    tm, tv = t.mean(), ((t - t.mean()) ** 2).sum()

    def f(w):
        slope = ((t - tm) * (w - w.mean())).sum() / tv
        return w.mean() + slope * (n - 1 - tm)
    return s.rolling(n, min_periods=n).apply(f, raw=True).to_numpy()


def _normalize(x):
    """Pine `normalize`: rescale with the running (expanding) min / max seen so far."""
    s = _s(x)
    lo, hi = s.cummin(), s.cummax()
    return ((s - lo) / (hi - lo).replace(0, np.nan)).to_numpy()


# ---------------------------------------------------------------- 1. Lorentzian
def lorentzian_features(o, h, l, c):
    f1 = ema(rsi(c, 14), 1) / 100
    hlc3 = (h + l + c) / 3
    e1 = ema(hlc3, 10)
    e2 = ema(np.abs(hlc3 - e1), 10)
    wt1 = ema((hlc3 - e1) / (0.015 * e2), 11)
    f2 = _normalize(wt1 - sma(wt1, 4))
    tp = hlc3
    md = _s(tp).rolling(20).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True).to_numpy()
    f3 = _normalize(ema((tp - sma(tp, 20)) / (0.015 * md), 1))
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = rma(tr(h, l, c), 20)
    pdi, mdi = 100 * rma(pdm, 20) / trs, 100 * rma(mdm, 20) / trs
    f4 = rma(100 * np.abs(pdi - mdi) / (pdi + mdi), 20) / 100
    f5 = ema(rsi(c, 9), 1) / 100
    return np.column_stack([f1, f2, f3, f4, f5])


@njit(cache=True)
def _ann(F, y, max_back, k, offset):
    """Approximate nearest neighbours as in the published script. For bar t the
    candidates are bars i in [t-max_back, t-1-offset] whose label y[i] is known at t."""
    T = F.shape[0]
    pred = np.zeros(T)
    dist = np.empty(k + 1)
    lab = np.empty(k + 1)
    for t in range(T):
        if np.isnan(F[t]).any():
            continue
        lo = max(0, t - max_back)
        hi = t - offset
        last, n = -1.0, 0
        for i in range(lo, hi):
            if (i - lo) % 4 == 0 or np.isnan(F[i]).any() or np.isnan(y[i]):
                continue
            d = 0.0
            for j in range(F.shape[1]):
                d += np.log(1.0 + abs(F[t, j] - F[i, j]))
            if d >= last:
                last = d
                dist[n] = d
                lab[n] = y[i]
                n += 1
                if n > k:
                    last = dist[int(round(k * 3 / 4))]
                    for m in range(k):
                        dist[m] = dist[m + 1]
                        lab[m] = lab[m + 1]
                    n = k
        s = 0.0
        for m in range(n):
            s += lab[m]
        pred[t] = s
    return pred


def rq_kernel(c, h=8, r=8.0, x=25):
    w = (1 + np.arange(x + 2) ** 2 / (h ** 2 * 2 * r)) ** -r
    out = np.full(len(c), np.nan)
    for t in range(x + 1, len(c)):
        win = c[t - x - 1:t + 1][::-1]
        out[t] = (win * w).sum() / w.sum()
    return out


def regime_filter(o, h, l, c, threshold=-0.1):
    src = (o + h + l + c) / 4
    v1 = v2 = klmf = 0.0
    out = np.zeros(len(c))
    prev_k = np.nan
    slopes = np.zeros(len(c))
    for t in range(1, len(c)):
        v1 = 0.2 * (src[t] - src[t - 1]) + 0.8 * v1
        v2 = 0.1 * (h[t] - l[t]) + 0.8 * v2
        om = abs(v1 / v2) if v2 else 0.0
        a = (-om ** 2 + np.sqrt(om ** 4 + 16 * om ** 2)) / 8
        klmf = a * src[t] + (1 - a) * klmf
        slopes[t] = abs(klmf - prev_k) if not np.isnan(prev_k) else 0.0
        prev_k = klmf
    avg = ema(slopes, 200)
    out = (slopes - avg) / avg >= threshold
    return out


def lorentzian(o, h, l, c, fixed=False, hold=4, neighbors=8, max_back=2000, use_kernel=True):
    F = lorentzian_features(o, h, l, c)
    T = len(c)
    if fixed:
        # Features at j-4, label = direction of the move j-4 -> j, known at bar j.
        Fl = np.full_like(F, np.nan)
        Fl[4:] = F[:-4]
        y = np.full(T, np.nan)
        y[4:] = np.sign(c[4:] - c[:-4])
        pred = _ann_forward(F, Fl, y, max_back, neighbors)
    else:
        y = np.full(T, np.nan)
        y[4:] = np.sign(c[:-4] - c[4:])          # as published: price up over last 4 bars -> "short"
        pred = _ann(F, y, max_back, neighbors, 0)
    filt = (tr(h, l, c) > atr(h, l, c, 10)) & regime_filter(o, h, l, c)
    sig = np.zeros(T)
    for t in range(1, T):
        sig[t] = 1 if (pred[t] > 0 and filt[t]) else -1 if (pred[t] < 0 and filt[t]) else sig[t - 1]
    k = rq_kernel(c)
    bull = np.r_[False, k[1:] > k[:-1]]
    pos = np.zeros(T)
    held = 0
    for t in range(1, T):
        new_buy = sig[t] == 1 and sig[t - 1] != 1
        if pos[t - 1] == 1:
            held += 1
            exit_ = held >= hold or (sig[t] == -1 and sig[t - 1] != -1)
            pos[t] = 0 if exit_ else 1
        elif new_buy and (bull[t] or not use_kernel):
            pos[t], held = 1, 0
    return pos, pred


@njit(cache=True)
def _ann_forward(F, Fl, y, max_back, k):
    """Same ANN loop, but compares today's features with LAGGED features Fl[i] = F[i-4]
    whose 4-bar-forward outcome y[i] is already known at bar t (i <= t)."""
    T = F.shape[0]
    pred = np.zeros(T)
    dist = np.empty(k + 1)
    lab = np.empty(k + 1)
    for t in range(T):
        if np.isnan(F[t]).any():
            continue
        lo = max(0, t - max_back)
        last, n = -1.0, 0
        for i in range(lo, t + 1):
            if (i - lo) % 4 == 0 or np.isnan(Fl[i]).any() or np.isnan(y[i]):
                continue
            d = 0.0
            for j in range(F.shape[1]):
                d += np.log(1.0 + abs(F[t, j] - Fl[i, j]))
            if d >= last:
                last = d
                dist[n] = d
                lab[n] = y[i]
                n += 1
                if n > k:
                    last = dist[int(round(k * 3 / 4))]
                    for m in range(k):
                        dist[m] = dist[m + 1]
                        lab[m] = lab[m + 1]
                    n = k
        s = 0.0
        for m in range(n):
            s += lab[m]
        pred[t] = s
    return pred


# ---------------------------------------------------------------- 2. Adaptive SuperTrend
@njit(cache=True)
def _kmeans_atr(vol, period, hi_p, mid_p, lo_p):
    T = len(vol)
    out = np.full(T, np.nan)
    for t in range(period - 1, T):
        w = vol[t - period + 1:t + 1]
        if np.isnan(w).any():
            continue
        lo, up = w.min(), w.max()
        c = np.array([lo + (up - lo) * hi_p, lo + (up - lo) * mid_p, lo + (up - lo) * lo_p])
        for _ in range(100):
            s = np.zeros(3)
            n = np.zeros(3)
            for v in w:
                j = np.argmin(np.abs(c - v))
                s[j] += v
                n[j] += 1
            new = c.copy()
            for j in range(3):
                if n[j] > 0:
                    new[j] = s[j] / n[j]
            if np.abs(new - c).max() < 1e-12:
                break
            c = new
        out[t] = c[np.argmin(np.abs(c - vol[t]))]
    return out


@njit(cache=True)
def supertrend(h, l, c, a, factor):
    """Pine ta.supertrend with a custom ATR series. Returns direction: 1 bullish, -1 bearish."""
    T = len(c)
    d = np.zeros(T)
    lb = np.full(T, np.nan)
    ub = np.full(T, np.nan)
    st_is_upper = True
    for t in range(T):
        if np.isnan(a[t]):
            continue
        src = (h[t] + l[t]) / 2
        lo, up = src - factor * a[t], src + factor * a[t]
        if t > 0 and not np.isnan(lb[t - 1]):
            lo = lo if (lo > lb[t - 1] or c[t - 1] < lb[t - 1]) else lb[t - 1]
            up = up if (up < ub[t - 1] or c[t - 1] > ub[t - 1]) else ub[t - 1]
            if st_is_upper:
                d[t] = 1 if c[t] > up else -1
            else:
                d[t] = -1 if c[t] < lo else 1
        else:
            d[t] = -1
        lb[t], ub[t] = lo, up
        st_is_upper = d[t] == -1
    return d


def adaptive_supertrend(o, h, l, c, atr_len=10, factor=3.0, period=100):
    vol = atr(h, l, c, atr_len)
    a = _kmeans_atr(vol, period, 0.75, 0.5, 0.25)
    d = supertrend(h, l, c, a, factor)
    return (d == 1).astype(float), d


# ---------------------------------------------------------------- 3. Squeeze Momentum
def squeeze(o, h, l, c, length=20, mult_kc=1.5):
    basis = sma(c, length)
    dev = mult_kc * _s(c).rolling(length).std(ddof=0).to_numpy()   # LazyBear uses multKC here
    ubb, lbb = basis + dev, basis - dev
    rng = sma(tr(h, l, c), length)
    ukc, lkc = basis + rng * mult_kc, basis - rng * mult_kc
    sqz_on = (lbb > lkc) & (ubb < ukc)
    hh = _s(h).rolling(length).max().to_numpy()
    ll = _s(l).rolling(length).min().to_numpy()
    val = linreg(c - ((hh + ll) / 2 + basis) / 2, length)
    return sqz_on, val


def squeeze_strategy(o, h, l, c):
    on, val = squeeze(o, h, l, c)
    T = len(c)
    pos = np.zeros(T)
    for t in range(2, T):
        fired = on[t - 1] and not on[t]
        if pos[t - 1] == 1:
            pos[t] = 0 if val[t] < val[t - 1] else 1
        elif fired and val[t] > 0 and val[t] > val[t - 1]:
            pos[t] = 1
    return pos, on, val


# ---------------------------------------------------------------- 4. Smart Money Concepts
@njit(cache=True)
def smc_state(h, l, c, length):
    """Structure, order blocks and FVGs, all confirmed without look-ahead.
    Returns per bar: trend (+1/-1), last swing high/low, active bullish zone (bottom, top),
    zone type (1 = OB, 2 = FVG), bullish break flag, bearish break flag."""
    T = len(c)
    trend = np.zeros(T)
    sh = np.full(T, np.nan)
    sl = np.full(T, np.nan)
    zb = np.full(T, np.nan)
    zt = np.full(T, np.nan)
    bull_brk = np.zeros(T)
    bear_brk = np.zeros(T)
    sh_p, sh_i, sh_x = np.nan, -1, True
    sl_p, sl_i, sl_x = np.nan, -1, True
    tr_ = 0.0
    zb_, zt_ = np.nan, np.nan
    # FVG size threshold: running mean of |bar % change| * 2 (LuxAlgo "auto" threshold)
    cum, cnt = 0.0, 0
    for t in range(T):
        # Confirm a pivot at p = t - length (needs `length` bars on each side).
        p = t - length
        if p - length >= 0:
            if h[p] == h[p - length:t + 1].max():
                sh_p, sh_i, sh_x = h[p], p, False
            if l[p] == l[p - length:t + 1].min():
                sl_p, sl_i, sl_x = l[p], p, False
        # Bullish break of structure / CHoCH.
        if not sh_x and not np.isnan(sh_p) and c[t] > sh_p:
            sh_x = True
            bull_brk[t] = 2 if tr_ == -1 else 1          # 2 = CHoCH, 1 = BOS
            tr_ = 1.0
            # Order block: candle with the lowest low between the broken swing high and now.
            j = sh_i + int(np.argmin(l[sh_i:t + 1]))
            zb_, zt_ = l[j], h[j]
        if not sl_x and not np.isnan(sl_p) and c[t] < sl_p:
            sl_x = True
            bear_brk[t] = 2 if tr_ == 1 else 1
            tr_ = -1.0
            zb_, zt_ = np.nan, np.nan
        # Bullish fair value gap in a bullish structure becomes the active zone.
        if t >= 2 and c[t - 1] > 0:
            cum += abs(c[t] / c[t - 1] - 1)
            cnt += 1
            if tr_ == 1 and l[t] > h[t - 2] and c[t - 1] > h[t - 2] and (l[t] - h[t - 2]) / h[t - 2] > 2 * cum / cnt:
                zb_, zt_ = h[t - 2], l[t]
        # Mitigation: a close below the zone removes it.
        if not np.isnan(zb_) and c[t] < zb_:
            zb_, zt_ = np.nan, np.nan
        trend[t], sh[t], sl[t], zb[t], zt[t] = tr_, sh_p, sl_p, zb_, zt_
    return trend, sh, sl, zb, zt, bull_brk, bear_brk


def smc_strategy(o, h, l, c, length=10, discount=True):
    trend, sh, sl, zb, zt, bb, sb = smc_state(h, l, c, length)
    T = len(c)
    pos = np.zeros(T)
    stop = np.nan
    for t in range(1, T):
        if pos[t - 1] == 1:
            out = c[t] < stop or sb[t] > 0
            pos[t] = 0 if out else 1
            continue
        if trend[t] != 1 or np.isnan(zb[t]):
            continue
        tapped = l[t] <= zt[t] and c[t] >= zb[t]
        eq = (sh[t] + sl[t]) / 2 if not (np.isnan(sh[t]) or np.isnan(sl[t])) else np.inf
        in_discount = c[t] <= max(eq, zt[t]) if discount else True
        if tapped and in_discount:
            pos[t], stop = 1, zb[t]
    return pos, (trend, sh, sl, zb, zt, bb, sb)


# ---------------------------------------------------------------- 5. Confluence (our design)
def confluence(o, h, l, c, mkt_ok=None, use_ml=True, use_squeeze=True, use_smc=True,
               use_market=True, smc_len=10):
    """Trend-following core with 'smart' entries, designed from what each tool does best.

    Stay in trends (the only long-only edge that survived our earlier research) and use
    the other tools for timing:
      regime  : ML Adaptive SuperTrend is bullish (k-means volatility-adaptive trend).
      entries : any of - SuperTrend flips bullish
                       - squeeze fires with positive, rising momentum
                       - retest of an unmitigated bullish order block / FVG in bullish structure
      ML veto : no entry when the (fixed, forward-labelled) Lorentzian kNN predicts down.
      market  : no NEW entries when the market is in a slow bear trend (SPY below its
                10-month average AND down over 12 months) - from the v3 research.
      exits   : SuperTrend flips bearish, or a bearish CHoCH (structure turns down).
    Trades are held for the whole trend instead of 4 bars, cutting turnover.
    """
    T = len(c)
    st, _ = adaptive_supertrend(o, h, l, c)
    on, val = squeeze(o, h, l, c)
    trend, sh, sl, zb, zt, bb, sb = smc_state(h, l, c, smc_len)
    pred = lorentzian(o, h, l, c, fixed=True)[1] if use_ml else np.zeros(T)
    mkt = np.ones(T, bool) if (mkt_ok is None or not use_market) else (mkt_ok > 0.5)
    pos = np.zeros(T)
    for t in range(2, T):
        if pos[t - 1] == 1:
            out = st[t] == 0 or (use_smc and sb[t] == 2)
            pos[t] = 0 if out else 1
            continue
        if st[t] != 1 or not mkt[t] or pred[t] < 0:
            continue
        flip = st[t - 1] == 0
        fire = use_squeeze and on[t - 1] and not on[t] and val[t] > 0 and val[t] > val[t - 1]
        tap = use_smc and trend[t] == 1 and not np.isnan(zb[t]) and l[t] <= zt[t] and c[t] >= zb[t]
        if flip or fire or tap:
            pos[t] = 1
    return pos, pred
