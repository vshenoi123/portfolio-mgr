import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.asyncio


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestFeaturesRouter:
    async def test_get_indicators(self, client):
        resp = await client.get("/api/v1/analysis/indicators/AAPL?days=365")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticker" in data
        assert data["ticker"] == "AAPL"

    async def test_get_indicators_no_data(self, client):
        resp = await client.get("/api/v1/analysis/indicators/UNKNOWN?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bars_analyzed"] == 0

    @patch("app.engines.features.router.compute_features_task")
    async def test_post_compute_features(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-456")
        resp = await client.post("/api/v1/analysis/indicators/compute/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-456"

    async def test_features_health(self, client):
        resp = await client.get("/api/v1/analysis/features/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine"] == "features"
