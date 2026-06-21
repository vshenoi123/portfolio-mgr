from unittest.mock import MagicMock, patch

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


@pytest.fixture
def mock_router_client():
    """Mock the AlpacaClient used by the router."""
    from app.engines.trading.schemas import TradeResult
    instance = MagicMock()
    instance.enabled = True
    instance.place_order.return_value = TradeResult(
        success=True, message="Order placed", order_id=1, alpaca_order_id="uuid-123",
    )
    instance.cancel_order.return_value = TradeResult(
        success=True, message="Order canceled", alpaca_order_id="uuid-123",
    )
    instance.modify_order.return_value = TradeResult(
        success=True, message="Order modified", order_id=1, alpaca_order_id="uuid-456",
    )
    instance.list_orders.return_value = []
    instance.get_order.return_value = None
    instance.sync_positions.return_value = TradeResult(
        success=True, message="Synced 3 positions",
    )
    with patch("app.engines.trading.router.AlpacaClient", return_value=instance):
        yield instance


class TestTradingRouter:
    async def test_place_order(self, client, mock_router_client):
        resp = await client.post(
            "/api/v1/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "market", "quantity": 100},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["order_id"] == 1

    async def test_place_order_validation_error(self, client):
        resp = await client.post(
            "/api/v1/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "order_type": "limit", "quantity": 100},
        )
        assert resp.status_code == 422

    async def test_cancel_order(self, client, mock_router_client):
        resp = await client.request(
            "DELETE", "/api/v1/trading/orders",
            json={"order_id": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_cancel_order_invalid(self, client):
        resp = await client.request(
            "DELETE", "/api/v1/trading/orders",
            json={},
        )
        assert resp.status_code == 422

    async def test_modify_order(self, client, mock_router_client):
        resp = await client.request(
            "PATCH", "/api/v1/trading/orders",
            json={"order_id": 1, "quantity": 200},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_modify_order_invalid(self, client):
        resp = await client.request(
            "PATCH", "/api/v1/trading/orders",
            json={"order_id": 1},
        )
        assert resp.status_code == 422

    async def test_list_orders(self, client, mock_router_client):
        resp = await client.get("/api/v1/trading/orders?status=open&limit=10")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_order(self, client, mock_router_client):
        resp = await client.get("/api/v1/trading/orders/1")
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_list_positions(self, client, mock_router_client):
        with patch("duckdb.connect") as mock_db:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchall.return_value = [
                ("AAPL", 100, 150.0, 155.0, 15500.0, 15000.0, 500.0, "equity"),
            ]
            mock_db.return_value = mock_conn
            resp = await client.get("/api/v1/trading/positions")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["ticker"] == "AAPL"

    async def test_get_position(self, client, mock_router_client):
        with patch("duckdb.connect") as mock_db:
            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = (
                "AAPL", 100, 150.0, 155.0, 15500.0, 15000.0, 500.0, "equity",
            )
            mock_db.return_value = mock_conn
            resp = await client.get("/api/v1/trading/positions/AAPL")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ticker"] == "AAPL"

    async def test_sync_positions_no_api_key(self, client, mock_router_client):
        with patch("app.config.settings") as mock_settings:
            mock_settings.polygon_api_key = ""
            resp = await client.post("/api/v1/trading/sync")
            assert resp.status_code == 400

    async def test_sync_position(self, client, mock_router_client):
        with patch("app.config.settings") as mock_settings:
            mock_settings.polygon_api_key = "test-key"
            resp = await client.post("/api/v1/trading/sync")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
