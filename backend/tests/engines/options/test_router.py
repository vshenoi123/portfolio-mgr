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


class TestOptionsRouter:
    async def test_generate_options_csp(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "underlying_price": 150.0, "implied_volatility": 0.30,
                  "risk_free_rate": 0.05, "strategy": "csp", "days_to_expiration": 30})
        assert resp.status_code == 200
        assert resp.json()["strategy"] == "csp"

    async def test_generate_options_leaps(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "underlying_price": 150.0, "implied_volatility": 0.35,
                  "risk_free_rate": 0.05, "strategy": "leaps", "days_to_expiration": 365})
        assert resp.status_code == 200
        assert resp.json()["strategy"] == "leaps"

    async def test_generate_options_invalid_strategy(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "underlying_price": 150.0, "implied_volatility": 0.30,
                  "days_to_expiration": 30, "strategy": "invalid"})
        assert resp.status_code == 422
