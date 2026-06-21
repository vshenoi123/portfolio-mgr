import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


pytestmark = pytest.mark.asyncio


class TestDataRouter:
    async def test_get_universe(self, client):
        resp = await client.get("/api/v1/data/universe")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert "SPY" in data["tickers"]
        assert "count" in data

    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @patch("app.engines.data.router.refresh_ticker_data")
    async def test_refresh_ticker(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-123")
        resp = await client.post("/api/v1/data/refresh/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-123"
        assert data["ticker"] == "AAPL"

    async def test_refresh_ticker_no_api_key(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.polygon_api_key", "")
        resp = await client.post("/api/v1/data/refresh/AAPL")
        assert resp.status_code == 400

    @patch("app.engines.data.router.PolygonDataService")
    async def test_get_ohlcv(self, mock_service, client):
        import pandas as pd
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.load_ohlcv.return_value = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "open": [150.0],
            "high": [155.0],
            "low": [149.0],
            "close": [153.0],
            "volume": [1000000],
        })
        resp = await client.get("/api/v1/data/ohlcv/AAPL?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bars"]) == 1
        assert data["bars"][0]["close"] == 153.0

    @patch("app.engines.data.router.PolygonDataService")
    async def test_get_ohlcv_no_data(self, mock_service, client):
        mock_service.return_value.load_ohlcv.return_value = __import__("pandas").DataFrame()
        resp = await client.get("/api/v1/data/ohlcv/UNKNOWN?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bars"]) == 0
