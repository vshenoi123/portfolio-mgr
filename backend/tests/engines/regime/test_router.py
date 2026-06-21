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


class TestRegimeRouter:
    async def test_get_global_regime(self, client):
        resp = await client.get("/api/v1/analysis/regime")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_regime" in data
        assert "ticker" in data

    async def test_get_regime_for_ticker(self, client):
        resp = await client.get("/api/v1/analysis/regime/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "overall_regime" in data

    @patch("app.engines.regime.router.compute_regime_task")
    async def test_post_compute_regime(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-789")
        resp = await client.post("/api/v1/analysis/regime/compute", json={"ticker": "SPY", "n_states": 4})
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-789"
