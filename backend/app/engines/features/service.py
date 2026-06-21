import pandas as pd
import numpy as np


def compute_ema(series: pd.Series, period: int = 20) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def compute_sma(series: pd.Series, period: int = 50) -> pd.Series:
    return series.rolling(window=period).mean()


def compute_trend_indicators(df: pd.DataFrame) -> dict[str, float]:
    close = df["close"]
    return {
        "ema_20": float(compute_ema(close, 20).iloc[-1]),
        "ema_50": float(compute_ema(close, 50).iloc[-1]),
        "ema_200": float(compute_ema(close, 200).iloc[-1]),
        "sma_50": float(compute_sma(close, 50).iloc[-1]),
        "sma_200": float(compute_sma(close, 200).iloc[-1]),
    }
