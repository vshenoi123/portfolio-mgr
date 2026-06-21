import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    np.random.seed(42)
    price = 150.0 + np.cumsum(np.random.normal(0, 1, 300))
    return pd.DataFrame({
        "timestamp": dates,
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(500000, 2000000, 300),
    })


class TestTrendIndicators:
    def test_compute_ema(self, sample_ohlcv):
        from app.engines.features.service import compute_ema
        ema = compute_ema(sample_ohlcv["close"], period=20)
        assert len(ema) == 300
        assert not ema[:19].isna().all()  # some early values are NaN
        assert not ema[19:].isna().any()  # after warmup, all valid
        assert 100 < ema.iloc[-1] < 200

    def test_compute_ema_short_series(self):
        from app.engines.features.service import compute_ema
        s = pd.Series([100.0, 101.0, 102.0])
        ema = compute_ema(s, period=20)
        assert len(ema) == 3
        assert not ema.isna().any()  # ewm(adjust=False) never produces NaN

    def test_compute_sma(self, sample_ohlcv):
        from app.engines.features.service import compute_sma
        sma = compute_sma(sample_ohlcv["close"], period=50)
        assert len(sma) == 300
        assert not sma[49:].isna().any()

    def test_compute_sma_short_series(self):
        from app.engines.features.service import compute_sma
        s = pd.Series([100.0, 101.0])
        sma = compute_sma(s, period=20)
        assert sma.isna().all()

    def test_compute_trend_indicators(self, sample_ohlcv):
        from app.engines.features.service import compute_trend_indicators
        result = compute_trend_indicators(sample_ohlcv)
        expected_keys = {"ema_20", "ema_50", "ema_200", "sma_50", "sma_200"}
        assert expected_keys.issubset(result.keys())
        for v in result.values():
            assert isinstance(v, float)
