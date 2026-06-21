import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d


def gaussian_channel(close: np.ndarray, sigma: float = 2.0, width: float = 2.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    filtered = gaussian_filter1d(close, sigma=sigma)
    residuals = close - filtered
    std = np.std(residuals)
    upper = filtered + width * std
    lower = filtered - width * std
    return upper, lower, filtered


def detect_gaussian_breakout(close: pd.Series, sigma: float = 2.0, width: float = 2.0) -> dict:
    if len(close) < 20:
        return {"direction": "none", "strength": 0.0, "breakout_type": "gaussian_channel", "confirmed": False}
    values = close.values
    upper, lower, _ = gaussian_channel(values, sigma=sigma, width=width)
    last_price = float(values[-1])
    if last_price > upper[-1]:
        strength = min(1.0, (last_price - upper[-1]) / (upper[-1] * 0.02))
        return {"direction": "bullish", "strength": strength, "breakout_type": "gaussian_channel", "confirmed": True}
    elif last_price < lower[-1]:
        strength = min(1.0, (lower[-1] - last_price) / (lower[-1] * 0.02))
        return {"direction": "bearish", "strength": strength, "breakout_type": "gaussian_channel", "confirmed": True}
    return {"direction": "none", "strength": 0.0, "breakout_type": "gaussian_channel", "confirmed": False}


def detect_vol_compression(close: pd.Series, bb_period: int = 20, kc_period: int = 20) -> dict:
    if len(close) < max(bb_period, kc_period):
        return {"squeeze": False, "strength": 0.0}
    sma = close.rolling(window=bb_period).mean()
    bb_std = close.rolling(window=bb_period).std()
    bb_width = 2.0 * bb_std / sma.replace(0, np.nan)

    tr = pd.concat([
        close - close.shift(),
        close - close.shift(),
        pd.Series(np.zeros(len(close)), index=close.index),
    ], axis=1).max(axis=1)
    kc_atr = tr.rolling(window=kc_period).mean()
    kc_width = 2.0 * kc_atr / sma.replace(0, np.nan)

    squeeze = bb_width.iloc[-1] < kc_width.iloc[-1] if pd.notna(bb_width.iloc[-1]) and pd.notna(kc_width.iloc[-1]) else False
    strength = min(1.0, abs(1.0 - bb_width.iloc[-1] / kc_width.iloc[-1])) if pd.notna(bb_width.iloc[-1]) and pd.notna(kc_width.iloc[-1]) else 0.0
    return {"squeeze": bool(squeeze), "strength": float(strength)}


def detect_market_structure(high: pd.Series, low: pd.Series, lookback: int = 10) -> dict:
    if len(high) < lookback * 2:
        return {"trend": "neutral", "strength": 0.0}
    recent_high = high.iloc[-lookback:].max()
    prev_high = high.iloc[-lookback*2:-lookback].max()
    recent_low = low.iloc[-lookback:].min()
    prev_low = low.iloc[-lookback*2:-lookback].min()

    higher_highs = recent_high > prev_high
    higher_lows = recent_low > prev_low
    lower_highs = recent_high < prev_high
    lower_lows = recent_low < prev_low

    if higher_highs and higher_lows:
        direction = "bullish"
        strength = min(1.0, abs(recent_high - prev_high) / prev_high * 100)
    elif lower_highs and lower_lows:
        direction = "bearish"
        strength = min(1.0, abs(prev_high - recent_high) / prev_high * 100)
    else:
        direction = "neutral"
        strength = 0.0

    return {"trend": direction, "strength": strength}


def detect_volume_confirmation(close: pd.Series, volume: pd.Series, window: int = 21) -> dict:
    if len(volume) < window:
        return {"expanding": False, "strength": 0.0}
    avg_vol = volume.rolling(window=window).mean()
    recent_avg = volume.iloc[-5:].mean() if len(volume) >= 5 else volume.iloc[-1]
    overall_avg = avg_vol.iloc[-1] if pd.notna(avg_vol.iloc[-1]) else volume.mean()
    expanding = recent_avg > overall_avg * 1.5 if overall_avg > 0 else False
    strength = min(1.0, recent_avg / (overall_avg * 2)) if overall_avg > 0 else 0.0
    return {"expanding": bool(expanding), "strength": float(strength)}


def full_breakout_scan(ohlcv: pd.DataFrame) -> list[dict]:
    if ohlcv.empty:
        return []
    signals = []
    gb = detect_gaussian_breakout(ohlcv["close"])
    if gb["direction"] != "none":
        signals.append({"ticker": "UNKNOWN", **gb})

    vc = detect_vol_compression(ohlcv["close"])
    ms = detect_market_structure(ohlcv["high"], ohlcv["low"])
    vol_conf = detect_volume_confirmation(ohlcv["close"], ohlcv["volume"])

    if vc["squeeze"]:
        signals.append({"ticker": "UNKNOWN", "direction": "neutral", "strength": vc["strength"],
                        "breakout_type": "vol_compression", "confirmed": False})
    if ms["trend"] != "neutral":
        signals.append({"ticker": "UNKNOWN", "direction": "bullish" if ms["trend"] == "bullish" else "bearish",
                        "strength": ms["strength"], "breakout_type": "market_structure", "confirmed": True})
    if vol_conf["expanding"]:
        signals.append({"ticker": "UNKNOWN", "direction": "neutral", "strength": vol_conf["strength"],
                        "breakout_type": "volume_confirmation", "confirmed": False})
    return signals
