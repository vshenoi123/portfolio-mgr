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


class TestOpportunityRouter:
    async def test_get_opportunities(self, client):
        resp = await client.get("/api/v1/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert "opportunities" in data

    async def test_get_opportunities_by_strategy(self, client):
        resp = await client.get("/api/v1/opportunities/swing")
        assert resp.status_code == 200
        for opp in resp.json()["opportunities"]:
            assert opp["strategy_type"] == "swing"

    @patch("app.engines.opportunity.router.compute_opp_task")
    async def test_post_compute_opportunities(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-301")
        resp = await client.post("/api/v1/opportunities/compute")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "task-301"
