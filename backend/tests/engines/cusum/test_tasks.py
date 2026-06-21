import pytest
from unittest.mock import patch, MagicMock


class TestCUSUMTasks:
    @patch("app.engines.cusum.tasks.PolygonDataService")
    @patch("app.engines.cusum.tasks.cusum_detect")
    def test_compute_cusum_task(self, mock_cusum, mock_ds):
        from app.engines.cusum.tasks import compute_cusum
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame({
            "close": [100.0 + i for i in range(100)],
        })
        mock_cusum.return_value = {
            "detected": True, "direction": "positive",
            "change_probability": 0.85, "days_since_change": 5, "cumulative_deviation": 3.2,
        }
        result = compute_cusum("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["detected"] is True

    @patch("app.engines.cusum.tasks.PolygonDataService")
    def test_compute_cusum_no_data(self, mock_ds):
        from app.engines.cusum.tasks import compute_cusum
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_cusum("UNKNOWN")
        assert result["status"] == "error"

    @patch("app.engines.cusum.tasks.compute_cusum")
    def test_compute_all_cusum_task(self, mock_compute):
        from app.engines.cusum.tasks import compute_all_cusum
        from app.models.universe import DEFAULT_UNIVERSE
        mock_compute.return_value = {"ticker": "TEST", "status": "success", "detected": False}
        results = compute_all_cusum()
        assert len(results) == len(DEFAULT_UNIVERSE)
