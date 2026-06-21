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


class TestStrategyRouter:
    async def test_get_strategy_for_ticker(self, client):
        resp = await client.get("/api/v1/opportunities/strategy/AAPL")
        assert resp.status_code == 200
        assert "recommendation" in resp.json()
