import pytest
from unittest.mock import patch, MagicMock


class TestBreakoutTasks:
    @patch("app.engines.breakout.tasks.PolygonDataService")
    @patch("app.engines.breakout.tasks.full_breakout_scan")
    def test_compute_breakouts_task(self, mock_scan, mock_ds):
        from app.engines.breakout.tasks import compute_breakouts
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame({
            "close": [100.0 + i for i in range(100)],
            "high": [102.0 + i for i in range(100)],
            "low": [98.0 + i for i in range(100)],
            "volume": [1000000] * 100,
        })
        mock_scan.return_value = [{"direction": "bullish", "strength": 0.8, "breakout_type": "gaussian_channel", "confirmed": True}]
        result = compute_breakouts("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["signals_count"] == 1

    @patch("app.engines.breakout.tasks.PolygonDataService")
    def test_compute_breakouts_no_data(self, mock_ds):
        from app.engines.breakout.tasks import compute_breakouts
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_breakouts("UNKNOWN")
        assert result["status"] == "error"
