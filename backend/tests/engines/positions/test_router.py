import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


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


class TestPositionsRouter:
    async def test_get_evaluate_csp(self, client):
        resp = await client.get("/api/v1/positions/evaluate/AAPL?strategy=csp")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["strategy_type"] == "csp"

    async def test_get_evaluate_unknown_strategy(self, client):
        resp = await client.get("/api/v1/positions/evaluate/AAPL?strategy=unknown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["strategy_type"] == "unknown"

    async def test_post_evaluate(self, client):
        resp = await client.post("/api/v1/positions/evaluate",
            json={"ticker": "AAPL", "strategy_type": "csp", "action": "hold"})
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"

    async def test_post_evaluate_invalid(self, client):
        resp = await client.post("/api/v1/positions/evaluate",
            json={"ticker": "AAPL", "strategy_type": "csp", "action": "invalid"})
        assert resp.status_code == 422

    async def test_post_watchdog(self, client):
        resp = await client.post("/api/v1/positions/watchdog")
        assert resp.status_code == 200
        data = resp.json()
        assert "positions_evaluated" in data
        assert "summary" in data

    async def test_get_csp_endpoint(self, client):
        resp = await client.get("/api/v1/positions/csp/AAPL?current_dte=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "roll"
        assert data["current_dte"] == 10

    async def test_get_swing_endpoint(self, client):
        resp = await client.get("/api/v1/positions/swing/AAPL?entry_price=100&current_price=130&highest_price=130")
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategy_type"] == "swing"
