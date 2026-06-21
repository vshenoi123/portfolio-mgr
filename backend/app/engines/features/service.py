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


def _safe_last(series: pd.Series) -> float:
    if series.empty or series.isna().all():
        return 0.0
    last = series.iloc[-1]
    return float(last) if not pd.isna(last) else 0.0


def compute_all_trend(close: pd.Series) -> dict[str, float]:
    return {
        "ema_20": _safe_last(compute_ema(close, 20)),
        "ema_50": _safe_last(compute_ema(close, 50)),
        "ema_200": _safe_last(compute_ema(close, 200)),
        "sma_50": _safe_last(compute_sma(close, 50)),
        "sma_200": _safe_last(compute_sma(close, 200)),
    }


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    zero_loss = avg_loss == 0
    zero_gain = avg_gain == 0
    rsi = rsi.where(~zero_loss, 100.0)
    rsi = rsi.where(~(zero_loss & zero_gain), 50.0)
    return rsi


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd = ema_fast - ema_slow
    signal = compute_ema(macd, signal_period)
    hist = macd - signal
    return macd, signal, hist


def compute_roc(close: pd.Series, period: int = 10) -> pd.Series:
    return close.pct_change(periods=period) * 100.0


def compute_ppo(close: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    return ((ema_fast - ema_slow) / ema_slow) * 100.0


def compute_stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series,
    k_period: int = 14, d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    k = 100.0 * ((close - low_min) / (high_max - low_min).replace(0, np.nan))
    d = k.rolling(window=d_period).mean()
    return k, d


def compute_all_momentum(high: pd.Series, low: pd.Series, close: pd.Series) -> dict[str, float]:
    macd, macd_signal, macd_hist = compute_macd(close)
    stoch_k, stoch_d = compute_stochastic(high, low, close)
    return {
        "rsi_14": _safe_last(compute_rsi(close, 14)),
        "macd": _safe_last(macd),
        "macd_signal": _safe_last(macd_signal),
        "macd_hist": _safe_last(macd_hist),
        "roc_10": _safe_last(compute_roc(close, 10)),
        "ppo": _safe_last(compute_ppo(close)),
        "stoch_k": _safe_last(stoch_k),
        "stoch_d": _safe_last(stoch_d),
    }


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def compute_historical_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    log_returns = np.log(close / close.shift())
    return log_returns.rolling(window=window).std() * np.sqrt(252)


def compute_realized_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    returns = close.pct_change()
    return returns.rolling(window=window).std() * np.sqrt(252)


def compute_bollinger_width(close: pd.Series, period: int = 20) -> pd.Series:
    sma = compute_sma(close, period)
    std = close.rolling(window=period).std()
    return 2.0 * std / sma.replace(0, np.nan)


def compute_all_volatility(high: pd.Series, low: pd.Series, close: pd.Series) -> dict[str, float]:
    return {
        "atr_14": _safe_last(compute_atr(high, low, close, 14)),
        "historical_vol_21": _safe_last(compute_historical_volatility(close, 21)),
        "realized_vol_21": _safe_last(compute_realized_volatility(close, 21)),
        "bollinger_width": _safe_last(compute_bollinger_width(close, 20)),
    }


def compute_relative_volume(volume: pd.Series, window: int = 21) -> pd.Series:
    avg_volume = volume.rolling(window=window).mean()
    return volume / avg_volume.replace(0, np.nan)


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()


def compute_accumulation_distribution(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    return (clv * volume).cumsum()


def compute_all_volume(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> dict[str, float]:
    return {
        "relative_volume_21": _safe_last(compute_relative_volume(volume, 21)),
        "obv": float(compute_obv(close, volume).iloc[-1]),
        "acc_dist": float(compute_accumulation_distribution(high, low, close, volume).iloc[-1]),
    }


def compute_relative_strength(ticker_close: pd.Series, benchmark_close: pd.Series) -> pd.Series:
    ticker_ret = ticker_close / ticker_close.iloc[0]
    bench_ret = benchmark_close / benchmark_close.iloc[0]
    return ticker_ret / bench_ret.replace(0, np.nan)


def compute_all_indicators(df: pd.DataFrame, spy_close: pd.Series | None = None) -> dict[str, dict]:
    if df.empty:
        return {"trend": {}, "momentum": {}, "volatility": {}, "volume": {}, "market_relative": {}}
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    if spy_close is not None and not spy_close.empty:
        relative_strength = _safe_last(compute_relative_strength(close, spy_close))
    else:
        relative_strength = _safe_last(compute_relative_strength(close, close))

    return {
        "trend": compute_all_trend(close),
        "momentum": compute_all_momentum(high, low, close),
        "volatility": compute_all_volatility(high, low, close),
        "volume": compute_all_volume(high, low, close, volume),
        "market_relative": {
            "relative_strength": relative_strength,
        },
    }
