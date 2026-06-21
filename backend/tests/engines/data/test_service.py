import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestPolygonService:
    @pytest.fixture
    def mock_polygon(self):
        with patch("app.engines.data.service.polygon_client") as mock:
            yield mock

    def test_fetch_ohlcv_returns_bars(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)

        mock_bar = MagicMock()
        mock_bar.t = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_bar.vw = 152.0
        mock_bar.n = 5000

        mock_polygon.get_aggs.return_value = [mock_bar]

        bars = service.fetch_ohlcv("AAPL", days=30)
        assert len(bars) == 1
        assert bars[0]["ticker"] == "AAPL"
        assert bars[0]["close"] == 153.0
        assert bars[0]["volume"] == 1000000

    def test_fetch_ohlcv_empty_response(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)
        mock_polygon.get_aggs.return_value = []
        bars = service.fetch_ohlcv("UNKNOWN", days=30)
        assert bars == []

    def test_fetch_ohlcv_handles_api_error(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService, PolygonAPIError
        service = PolygonDataService(data_dir=test_data_dir)
        mock_polygon.get_aggs.side_effect = Exception("API timeout")
        with pytest.raises(PolygonAPIError):
            service.fetch_ohlcv("AAPL", days=30)

    def test_save_ohlcv_creates_parquet(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)

        bars = []
        for i in range(5):
            bars.append({
                "ticker": "AAPL",
                "timestamp": datetime.now(timezone.utc),
                "open": 150.0 + i,
                "high": 155.0 + i,
                "low": 149.0 + i,
                "close": 153.0 + i,
                "volume": 1000000 + i * 100,
            })

        path = service.save_ohlcv(bars)
        assert path.endswith(".parquet")
        import os
        assert os.path.exists(path)

    def test_save_and_load_roundtrip(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)

        bars = [{
            "ticker": "AAPL",
            "timestamp": datetime.now(timezone.utc),
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
            "volume": 1000000,
        }]
        service.save_ohlcv(bars)

        loaded = service.load_ohlcv("AAPL", days=30)
        assert len(loaded) >= 1
        assert float(loaded["close"].iloc[0]) == 153.0
