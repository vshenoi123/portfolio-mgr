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


class TestMomentumIndicators:
    def test_compute_rsi(self, sample_ohlcv):
        from app.engines.features.service import compute_rsi
        rsi = compute_rsi(sample_ohlcv["close"], period=14)
        assert len(rsi) == 300
        last = rsi.iloc[-1]
        assert 0 <= last <= 100

    def test_rsi_constant_price(self):
        from app.engines.features.service import compute_rsi
        values = pd.Series([100.0] * 50)
        rsi = compute_rsi(values, period=14)
        assert rsi.iloc[-1] == 50.0

    def test_rsi_uptrend(self):
        from app.engines.features.service import compute_rsi
        values = pd.Series(np.linspace(100, 200, 100))
        rsi = compute_rsi(values, period=14)
        assert rsi.iloc[-1] > 50

    def test_compute_macd(self, sample_ohlcv):
        from app.engines.features.service import compute_macd
        macd, signal, hist = compute_macd(sample_ohlcv["close"])
        assert len(macd) == 300
        assert len(signal) == 300
        assert len(hist) == 300
        assert isinstance(macd.iloc[-1], float)

    def test_compute_roc(self, sample_ohlcv):
        from app.engines.features.service import compute_roc
        roc = compute_roc(sample_ohlcv["close"], period=10)
        assert len(roc) == 300
        assert isinstance(roc.iloc[-1], float)

    def test_compute_ppo(self, sample_ohlcv):
        from app.engines.features.service import compute_ppo
        ppo = compute_ppo(sample_ohlcv["close"])
        assert len(ppo) == 300
        assert isinstance(ppo.iloc[-1], float)

    def test_compute_stochastic(self, sample_ohlcv):
        from app.engines.features.service import compute_stochastic
        k, d = compute_stochastic(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        assert len(k) == 300
        assert len(d) == 300
        assert 0 <= k.iloc[-1] <= 100
        assert 0 <= d.iloc[-1] <= 100

    def test_compute_all_momentum(self, sample_ohlcv):
        from app.engines.features.service import compute_all_momentum
        result = compute_all_momentum(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        expected = {"rsi_14", "macd", "macd_signal", "macd_hist", "roc_10", "ppo", "stoch_k", "stoch_d"}
        assert expected.issubset(result.keys())
        assert all(isinstance(v, float) for v in result.values())


class TestVolatilityIndicators:
    def test_compute_atr(self, sample_ohlcv):
        from app.engines.features.service import compute_atr
        atr = compute_atr(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], period=14)
        assert len(atr) == 300
        assert atr.iloc[-1] > 0

    def test_compute_historical_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_historical_volatility
        hv = compute_historical_volatility(sample_ohlcv["close"], window=21)
        assert len(hv) == 300
        assert hv.iloc[-1] >= 0

    def test_compute_realized_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_realized_volatility
        rv = compute_realized_volatility(sample_ohlcv["close"], window=21)
        assert len(rv) == 300
        assert rv.iloc[-1] >= 0

    def test_compute_bollinger_width(self, sample_ohlcv):
        from app.engines.features.service import compute_bollinger_width
        width = compute_bollinger_width(sample_ohlcv["close"], period=20)
        assert len(width) == 300
        assert width.iloc[-1] >= 0

    def test_compute_all_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_all_volatility
        result = compute_all_volatility(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        assert "atr_14" in result
        assert "historical_vol_21" in result
        assert "realized_vol_21" in result
        assert "bollinger_width" in result
        assert all(isinstance(v, float) for v in result.values())


class TestVolumeIndicators:
    def test_compute_relative_volume(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_volume
        rvol = compute_relative_volume(sample_ohlcv["volume"], window=21)
        assert len(rvol) == 300
        assert rvol.iloc[-1] >= 0

    def test_compute_obv(self, sample_ohlcv):
        from app.engines.features.service import compute_obv
        obv = compute_obv(sample_ohlcv["close"], sample_ohlcv["volume"])
        assert len(obv) == 300
        assert isinstance(obv.iloc[-1], (int, float, np.integer))

    def test_compute_accumulation_distribution(self, sample_ohlcv):
        from app.engines.features.service import compute_accumulation_distribution
        ad = compute_accumulation_distribution(
            sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], sample_ohlcv["volume"]
        )
        assert len(ad) == 300
        assert isinstance(ad.iloc[-1], (int, float))

    def test_compute_all_volume(self, sample_ohlcv):
        from app.engines.features.service import compute_all_volume
        result = compute_all_volume(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], sample_ohlcv["volume"])
        assert "relative_volume_21" in result
        assert "obv" in result
        assert "acc_dist" in result
        assert all(isinstance(v, float) for v in result.values())


class TestMarketRelativeIndicators:
    def test_compute_relative_strength(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        spy = sample_ohlcv["close"] * 1.0
        rs = compute_relative_strength(sample_ohlcv["close"], spy)
        assert len(rs) == 300
        assert isinstance(rs.iloc[-1], float)

    def test_rs_diverging_up(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        n = len(sample_ohlcv)
        ticker = pd.Series(np.linspace(100, 150, n))
        spy = pd.Series(np.linspace(100, 120, n))
        rs = compute_relative_strength(ticker, spy)
        assert rs.iloc[-1] > 1.0

    def test_rs_diverging_down(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        n = len(sample_ohlcv)
        ticker = pd.Series(np.linspace(100, 120, n))
        spy = pd.Series(np.linspace(100, 150, n))
        rs = compute_relative_strength(ticker, spy)
        assert rs.iloc[-1] < 1.0


class TestFullPipeline:
    def test_compute_all_indicators(self, sample_ohlcv):
        from app.engines.features.service import compute_all_indicators
        result = compute_all_indicators(sample_ohlcv)
        expected_categories = {"trend", "momentum", "volatility", "volume", "market_relative"}
        assert expected_categories.issubset(result.keys())
        for cat in expected_categories:
            assert isinstance(result[cat], dict)
            assert len(result[cat]) > 0

    def test_compute_all_indicators_short_data(self):
        from app.engines.features.service import compute_all_indicators
        short = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=10, freq="B"),
            "open": [150.0] * 10,
            "high": [155.0] * 10,
            "low": [149.0] * 10,
            "close": [153.0] * 10,
            "volume": [1000000] * 10,
        })
        result = compute_all_indicators(short)
        assert isinstance(result, dict)

    def test_compute_all_indicators_empty_data(self):
        from app.engines.features.service import compute_all_indicators
        empty = pd.DataFrame()
        result = compute_all_indicators(empty)
        assert isinstance(result, dict)
