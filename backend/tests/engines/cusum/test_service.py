import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def stable_returns():
    np.random.seed(42)
    return pd.Series(np.random.normal(0, 0.01, 300))


@pytest.fixture
def shift_up_returns():
    np.random.seed(42)
    before = np.random.normal(0, 0.01, 200)
    after = np.random.normal(0.02, 0.01, 100)
    return pd.Series(np.concatenate([before, after]))


@pytest.fixture
def shift_down_returns():
    np.random.seed(42)
    before = np.random.normal(0, 0.01, 200)
    after = np.random.normal(-0.02, 0.01, 100)
    return pd.Series(np.concatenate([before, after]))


class TestCUSUMService:
    def test_cusum_no_drift_stable(self, stable_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(stable_returns, threshold=3.0, drift=0.005)
        assert result["detected"] is False
        assert result["direction"] == "none"

    def test_cusum_detects_positive_shift(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold=1.0, drift=0.005)
        assert result["detected"] is True
        assert result["direction"] == "positive"
        assert result["change_probability"] > 0.5

    def test_cusum_detects_negative_shift(self, shift_down_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_down_returns, threshold=1.0, drift=0.005)
        assert result["detected"] is True
        assert result["direction"] == "negative"
        assert result["change_probability"] > 0.5

    def test_cusum_calculates_days_since_change(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold=1.0, drift=0.005)
        assert result["days_since_change"] is not None
        assert result["days_since_change"] >= 0

    def test_cusum_higher_threshold_less_detection(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        low_thresh = cusum_detect(shift_up_returns, threshold=1.0, drift=0.005)
        high_thresh = cusum_detect(shift_up_returns, threshold=3.0, drift=0.005)
        assert low_thresh["detected"] is True
        assert high_thresh["detected"] is False

    def test_cusum_insufficient_data(self):
        from app.engines.cusum.service import cusum_detect
        short = pd.Series([0.01, -0.02, 0.01])
        result = cusum_detect(short, threshold=3.0, drift=0.005)
        assert result["detected"] is False

    def test_cusum_dynamic_threshold(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold="dynamic", drift=0.005)
        assert "detected" in result
        assert "change_probability" in result

    def test_cusum_all_numpy_no_pandas_dependency(self):
        from app.engines.cusum.service import _cusum_algorithm
        arr = np.random.randn(300)
        arr[200:] += 0.03
        result = _cusum_algorithm(arr, threshold=3.0, drift=0.005)
        assert result["detected"] is True
