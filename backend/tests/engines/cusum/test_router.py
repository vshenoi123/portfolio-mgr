import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
import pytest_asyncio


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


class TestCUSUMRouter:
    async def test_get_cusum(self, client):
        resp = await client.get("/api/v1/analysis/cusum/AAPL?days=365")
        assert resp.status_code == 200
        data = resp.json()
        assert "cusum_result" in data or "ticker" in data

    async def test_get_cusum_no_data(self, client):
        resp = await client.get("/api/v1/analysis/cusum/UNKNOWN?days=30")
        assert resp.status_code == 200

    @patch("app.engines.cusum.router.compute_cusum_task")
    async def test_post_compute_cusum(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-111")
        resp = await client.post("/api/v1/analysis/cusum/compute/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-111"
