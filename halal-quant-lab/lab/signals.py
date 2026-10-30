"""Concept signals built from indicators, cached so thousands of configs share work.

Concepts (each answers one question about a stock on a given day):
  uptrend     - is price above a rising moving average?
  strong      - is the trend strong (ADX above a threshold)?
  momentum    - cross-sectional rank of 12-1 style momentum
  rel_strength- has it beaten SPY over the last n days?
  pullback    - is short-term RSI oversold inside the trend? (buy the dip)
  bb_dip      - is price stretched below its Bollinger mean? (mean reversion)
  breakout    - did it close above its n-day high? (Donchian / turtle style)
  volume      - is volume surging and on-balance volume rising? (accumulation)
  low_vol     - cross-sectional rank of low realised volatility (quality proxy)
  regime      - is the overall market healthy (SPY trend + VIX level)?
"""
import pandas as pd

from . import indicators as ind


class Features:
    def __init__(self, px, tickers):
        self.O = px["Open"][tickers].ffill()
        self.H = px["High"][tickers].ffill()
        self.L = px["Low"][tickers].ffill()
        self.C = px["Close"][tickers].ffill()
        self.V = px["Volume"][tickers]
        # Valid where the stock actually trades (no ffill before listing).
        self.alive = px["Close"][tickers].notna() & self.C.notna()
        self.spy = px["Close"]["SPY"].ffill()
        self.vix = px["Close"]["^VIX"].ffill()
        self._cache = {}

    def get(self, name, *args):
        key = (name, *args)
        if key not in self._cache:
            self._cache[key] = getattr(self, "_" + name)(*args)
        return self._cache[key]

    # ---- raw indicators -------------------------------------------------
    def _sma(self, n):
        return ind.sma(self.C, n)

    def _atr(self, n):
        return ind.atr(self.H, self.L, self.C, n)

    def _adx(self, n):
        return ind.adx(self.H, self.L, self.C, n)

    def _rsi(self, n):
        return ind.rsi(self.C, n)

    def _roc(self, n):
        return ind.roc(self.C, n)

    def _vol(self, n):
        return ind.realized_vol(self.C, n)

    # ---- concepts -------------------------------------------------------
    def _uptrend(self, n):
        m = self.get("sma", n)
        return (self.C > m) & (m > m.shift(20))

    def _strong(self, th):
        return self.get("adx", 14) > th

    def _momentum(self, lookback):
        return ind.cs_rank(ind.momentum(self.C, lookback, 21).where(self.alive))

    def _rel_strength(self, n):
        return self.get("roc", n).sub(ind.roc(self.spy, n), axis=0) > 0

    def _pullback(self, n, th):
        return self.get("rsi", n) < th

    def _bb_dip(self, n, z):
        return ind.bollinger_z(self.C, n) < -z

    def _breakout(self, n):
        return self.C > ind.donchian_high(self.H, n)

    def _volume(self, mult):
        surge = self.V > mult * ind.sma(self.V, 20)
        o = ind.obv(self.C, self.V)
        return surge & (o > ind.sma(o, 20))

    def _low_vol(self, n):
        return ind.cs_rank(-self.get("vol", n).where(self.alive))

    def _regime(self, n, vix_max):
        return (self.spy > ind.sma(self.spy, n)) & (self.vix < vix_max)


def rotation_score(F: Features, cfg):
    """Multi-factor score for ranking stocks in the rotation family."""
    score = (cfg["w_mom"] * F.get("momentum", cfg["mom_lb"])
             + cfg["w_short"] * ind.cs_rank(F.get("roc", 63).where(F.alive))
             + cfg["w_lowvol"] * F.get("low_vol", 60)
             + cfg["w_strength"] * ind.cs_rank(F.get("adx", 14).where(F.alive))
             + cfg["w_dip"] * ind.cs_rank(-F.get("rsi", 5).where(F.alive)))
    eligible = F.alive & F.get("uptrend", cfg["trend_n"])
    return score.where(eligible)


def swing_signals(F: Features, cfg):
    """Confluence entry: weighted vote of concepts must reach a threshold."""
    votes = {
        "strong": F.get("strong", cfg["adx_th"]),
        "momentum": F.get("momentum", cfg["mom_lb"]) >= cfg["mom_q"],
        "rel_strength": F.get("rel_strength", cfg["rs_n"]),
        "pullback": F.get("pullback", cfg["rsi_n"], cfg["rsi_th"]),
        "bb_dip": F.get("bb_dip", 20, cfg["bb_z"]),
        "breakout": F.get("breakout", cfg["break_n"]),
        "volume": F.get("volume", cfg["vol_mult"]),
    }
    total = sum(cfg["w"][k] for k in votes) or 1
    score = sum(cfg["w"][k] * v.astype(float) for k, v in votes.items() if cfg["w"][k])
    entry = (score >= cfg["threshold"] * total) & F.alive
    if cfg["require_trend"]:
        entry &= F.get("uptrend", cfg["trend_n"])
    if cfg["regime"]:
        entry = entry.mul(F.get("regime", cfg["regime_n"], cfg["vix_max"]), axis=0).astype(bool)
    exit_ = F.C < F.get("sma", cfg["exit_n"])
    rank = F.get("momentum", cfg["mom_lb"]).fillna(0) + 0.01 * score
    return entry.fillna(False), exit_, rank
