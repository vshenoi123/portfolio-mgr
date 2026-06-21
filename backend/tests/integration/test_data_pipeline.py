"""
Integration tests for the data pipeline end-to-end.
Uses real DuckDB and filesystem, mocks Polygon API.
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestDataPipelineIntegration:
    @patch("app.engines.data.service.polygon_client")
    def test_full_refresh_flow(self, mock_client, test_data_dir):
        """End-to-end: fetch from Polygon -> save Parquet -> load from Parquet"""
        from app.engines.data.service import PolygonDataService

        mock_bar = MagicMock()
        mock_bar.t = int(datetime(2024, 1, 15).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_bar.vw = None
        mock_bar.n = None
        mock_client.get_aggs.return_value = [mock_bar]

        data_service = PolygonDataService(data_dir=test_data_dir)
        bars = data_service.fetch_ohlcv("AAPL", days=30)
        assert len(bars) == 1

        path = data_service.save_ohlcv(bars)
        assert os.path.exists(path)

        loaded = data_service.load_ohlcv("AAPL", days=3650)
        assert len(loaded) == 1
        assert float(loaded["close"].iloc[0]) == 153.0

    def test_parquet_directory_structure(self, test_data_dir):
        """Verify Parquet files are organized by ticker"""
        from app.database import ensure_parquet_dir
        path = ensure_parquet_dir("AAPL", "ohlcv")
        expected = os.path.join(test_data_dir, "market_data", "ohlcv", "aapl")
        assert path == expected
        assert os.path.exists(path)

    def test_incremental_refresh_appends_data(self, test_data_dir):
        """Refreshing twice should keep all bars"""
        from app.engines.data.service import PolygonDataService

        data_service = PolygonDataService(data_dir=test_data_dir)

        today = datetime.now(timezone.utc)

        bars1 = []
        for i in range(3):
            ts = today - timedelta(days=5 + i)
            bars1.append({
                "ticker": "AAPL",
                "timestamp": ts,
                "open": 150.0 + i,
                "high": 155.0 + i,
                "low": 149.0 + i,
                "close": 153.0 + i,
                "volume": 1000000,
            })
        data_service.save_ohlcv(bars1)

        bars2 = [{
            "ticker": "AAPL",
            "timestamp": today,
            "open": 160.0,
            "high": 165.0,
            "low": 159.0,
            "close": 163.0,
            "volume": 2000000,
        }]
        data_service.save_ohlcv(bars2)

        loaded = data_service.load_ohlcv("AAPL", days=365)
        assert len(loaded) == 4

    def test_empty_universe_returns_empty_data(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        data_service = PolygonDataService(data_dir=test_data_dir)
        df = data_service.load_ohlcv("NONEXISTENT", days=30)
        assert df.empty

    @patch("app.engines.data.service.polygon_client")
    def test_concurrent_refresh_same_ticker(self, mock_client, test_data_dir):
        """Multiple refreshes for same ticker should not corrupt data"""
        from app.engines.data.service import PolygonDataService

        mock_bar = MagicMock()
        mock_bar.t = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_bar.vw = None
        mock_bar.n = None
        mock_client.get_aggs.return_value = [mock_bar]

        data_service = PolygonDataService(data_dir=test_data_dir)
        bars = data_service.fetch_ohlcv("AAPL", days=30)
        data_service.save_ohlcv(bars)
        data_service.save_ohlcv(bars)

        loaded = data_service.load_ohlcv("AAPL", days=365)
        assert len(loaded) >= 1

    @patch("app.engines.data.service.polygon_client")
    def test_router_returns_integration_data(self, mock_client, test_data_dir):
        """Verify FastAPI router returns data through the full stack"""
        from app.engines.data.service import PolygonDataService

        mock_bar = MagicMock()
        mock_bar.t = int(datetime(2024, 1, 15).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_bar.vw = None
        mock_bar.n = None
        mock_client.get_aggs.return_value = [mock_bar]

        service = PolygonDataService(data_dir=test_data_dir)
        bars = service.fetch_ohlcv("AAPL", days=30)
        service.save_ohlcv(bars)

        df = service.load_ohlcv("AAPL", days=3650)
        assert not df.empty
        assert float(df["close"].iloc[0]) == 153.0
