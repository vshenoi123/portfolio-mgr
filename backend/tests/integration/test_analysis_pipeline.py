"""Integration tests for the full analysis pipeline end-to-end."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


class TestAnalysisPipeline:
    @pytest.fixture
    def sample_data(self, test_data_dir):
        """Create test data accessible to all analysis engines."""
        dates = pd.date_range("2024-01-01", periods=300, freq="B")
        np.random.seed(42)
        price = 150.0 + np.cumsum(np.random.normal(0, 1, 300))
        df = pd.DataFrame({
            "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
            "low": price * 0.98, "close": price, "volume": np.random.randint(500000, 2000000, 300),
        })

        from app.engines.data.service import PolygonDataService
        bars = []
        for _, row in df.iterrows():
            bars.append({
                "ticker": "SPY", "timestamp": row["timestamp"].to_pydatetime(),
                "open": float(row["open"]), "high": float(row["high"]),
                "low": float(row["low"]), "close": float(row["close"]),
                "volume": int(row["volume"]),
            })
        service = PolygonDataService(data_dir=test_data_dir)
        service.save_ohlcv(bars)
        return df, test_data_dir

    def test_features_pipeline(self, sample_data):
        """Feature engineering compute_all_indicators works end-to-end."""
        df, _ = sample_data
        from app.engines.features.service import compute_all_indicators
        result = compute_all_indicators(df)
        assert len(result) >= 4  # trend, momentum, volatility, market_relative, ...
        assert "trend" in result
        assert "ema_20" in result["trend"]
        assert "momentum" in result

    def test_regime_pipeline(self, sample_data):
        """Market regime analysis works with real data structure."""
        df, _ = sample_data
        returns = df["close"].pct_change().dropna()
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(returns, n_states=4)
        assert result["overall_regime"].regime in ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]

    def test_cusum_pipeline(self, sample_data):
        """CUSUM detection works with real data structure."""
        df, _ = sample_data
        returns = df["close"].pct_change().dropna()
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(returns)
        assert "detected" in result
        assert "direction" in result

    def test_breakout_pipeline(self, sample_data):
        """Breakout detection works with real data structure."""
        df, _ = sample_data
        from app.engines.breakout.service import full_breakout_scan
        signals = full_breakout_scan(df)
        assert isinstance(signals, list)

    def test_all_engines_independent(self, sample_data):
        """Each engine can run without depending on other engines' output."""
        df, _ = sample_data
        from app.engines.features.service import compute_all_indicators
        from app.engines.regime.service import full_regime_analysis
        from app.engines.cusum.service import cusum_detect

        features = compute_all_indicators(df)
        assert len(features) > 0

        returns = df["close"].pct_change().dropna()
        regime = full_regime_analysis(returns)
        assert regime["trained_on_bars"] > 0

        cusum = cusum_detect(returns)
        assert "detected" in cusum
