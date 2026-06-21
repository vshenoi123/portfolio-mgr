import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    np.random.seed(42)
    price = 150.0 + np.cumsum(np.random.normal(0, 1, 300))
    return pd.DataFrame({
        "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
        "low": price * 0.98, "close": price, "volume": np.random.randint(500000, 2000000, 300),
    })


@pytest.fixture
def trending_up_ohlcv():
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    price = 100.0 + np.arange(200) * 0.5
    return pd.DataFrame({
        "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
        "low": price * 0.98, "close": price, "volume": np.full(200, 1000000),
    })


class TestGaussianChannel:
    def test_gaussian_channel_returns_bands(self, sample_ohlcv):
        from app.engines.breakout.service import gaussian_channel
        close = sample_ohlcv["close"].values
        upper, lower, filtered = gaussian_channel(close, sigma=2.0)
        assert len(upper) == len(close)
        assert len(lower) == len(close)
        assert np.all(upper >= lower)

    def test_gaussian_breakout_detection_bullish(self, trending_up_ohlcv):
        from app.engines.breakout.service import detect_gaussian_breakout
        result = detect_gaussian_breakout(trending_up_ohlcv["close"])
        assert "direction" in result
        assert "strength" in result

    def test_gaussian_breakout_detection_short_data(self):
        from app.engines.breakout.service import detect_gaussian_breakout
        short = pd.Series([100.0, 101.0, 102.0])
        result = detect_gaussian_breakout(short)
        assert result["direction"] == "none"


class TestVolatilityCompression:
    def test_vol_compression_detects_squeeze(self, sample_ohlcv):
        from app.engines.breakout.service import detect_vol_compression
        result = detect_vol_compression(sample_ohlcv["close"])
        assert "squeeze" in result
        assert "strength" in result

    def test_vol_compression_ratio_range(self, sample_ohlcv):
        from app.engines.breakout.service import detect_vol_compression
        result = detect_vol_compression(sample_ohlcv["close"])
        assert 0 <= result["strength"] <= 1


class TestMarketStructure:
    def test_market_structure_detection(self, trending_up_ohlcv):
        from app.engines.breakout.service import detect_market_structure
        result = detect_market_structure(trending_up_ohlcv["high"], trending_up_ohlcv["low"])
        assert "trend" in result
        assert "strength" in result

    def test_market_structure_uptrend(self, trending_up_ohlcv):
        from app.engines.breakout.service import detect_market_structure
        result = detect_market_structure(trending_up_ohlcv["high"], trending_up_ohlcv["low"])
        assert result["trend"] == "uptrend" or result["strength"] > 0


class TestVolumeConfirmation:
    def test_volume_confirmation(self, sample_ohlcv):
        from app.engines.breakout.service import detect_volume_confirmation
        result = detect_volume_confirmation(sample_ohlcv["close"], sample_ohlcv["volume"])
        assert "expanding" in result
        assert "strength" in result

    def test_volume_high_volume_day(self, sample_ohlcv):
        from app.engines.breakout.service import detect_volume_confirmation
        high_vol = sample_ohlcv.copy()
        high_vol.loc[high_vol.index[-1], "volume"] = 10_000_000
        result = detect_volume_confirmation(high_vol["close"], high_vol["volume"])
        assert result["expanding"] is True


class TestFullBreakoutScan:
    def test_full_breakout_scan(self, sample_ohlcv):
        from app.engines.breakout.service import full_breakout_scan
        result = full_breakout_scan(sample_ohlcv)
        assert isinstance(result, list)
        if result:
            assert "ticker" in result[0]
            assert "direction" in result[0]

    def test_full_breakout_scan_empty(self):
        from app.engines.breakout.service import full_breakout_scan
        empty = pd.DataFrame()
        result = full_breakout_scan(empty)
        assert result == []
