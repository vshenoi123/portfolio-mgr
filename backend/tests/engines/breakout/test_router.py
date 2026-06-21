import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


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


class TestBreakoutRouter:
    async def test_get_breakouts(self, client):
        resp = await client.get("/api/v1/analysis/breakouts/AAPL?days=365")
        assert resp.status_code == 200

    async def test_get_breakouts_no_data(self, client):
        resp = await client.get("/api/v1/analysis/breakouts/UNKNOWN?days=30")
        assert resp.status_code == 200
