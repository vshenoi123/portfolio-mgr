from unittest.mock import MagicMock, patch, PropertyMock

import pytest


@pytest.fixture
def mock_trading_client():
    with patch("app.engines.trading.service.TradingClient") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_db():
    """Mock the database layer used by AlpacaClient methods."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_conn.execute.return_value.fetchall.return_value = []
    with patch("app.database.get_connection", return_value=mock_conn) as m:
        yield m, mock_conn


@pytest.fixture
def alpaca_client(mock_trading_client):
    with patch("app.engines.trading.service.logger"):
        from app.engines.trading.service import AlpacaClient
        client = AlpacaClient()
        client._enabled = True
        client._client = mock_trading_client
        return client


class TestPlaceOrder:
    def test_place_market_order(self, alpaca_client, mock_trading_client, mock_db):
        from app.engines.trading.schemas import OrderRequest
        from alpaca.trading.models import Order
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, OrderStatus

        mock_conn_getter, mock_conn = mock_db
        mock_conn.execute.reset_mock()

        mock_order = MagicMock(spec=Order)
        mock_order.id = "uuid-123"
        mock_order.symbol = "AAPL"
        mock_order.side = OrderSide.BUY
        mock_order.type = OrderType.MARKET
        mock_order.time_in_force = TimeInForce.DAY
        mock_order.qty = "100"
        mock_order.filled_qty = "0"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.status = OrderStatus.ACCEPTED
        mock_order.filled_avg_price = None
        mock_order.submitted_at = None
        mock_order.filled_at = None
        mock_trading_client.submit_order.return_value = mock_order

        mock_conn.execute.side_effect = None
        mock_conn.execute.return_value.fetchone.return_value = (42,)
        mock_conn_getter.return_value = mock_conn

        req = OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100)
        result = alpaca_client.place_order(req)

        assert result.success is True
        assert result.alpaca_order_id == "uuid-123"
        assert result.order_id == 42
        mock_trading_client.submit_order.assert_called_once()

    def test_place_limit_order(self, alpaca_client, mock_trading_client, mock_db):
        from app.engines.trading.schemas import OrderRequest
        from alpaca.trading.models import Order
        from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, OrderStatus

        mock_conn_getter, mock_conn = mock_db
        mock_conn.execute.reset_mock()

        mock_order = MagicMock(spec=Order)
        mock_order.id = "uuid-456"
        mock_order.symbol = "AAPL"
        mock_order.side = OrderSide.SELL
        mock_order.type = OrderType.LIMIT
        mock_order.time_in_force = TimeInForce.GTC
        mock_order.qty = "50"
        mock_order.filled_qty = "0"
        mock_order.limit_price = "150.0"
        mock_order.stop_price = None
        mock_order.status = OrderStatus.ACCEPTED
        mock_order.filled_avg_price = None
        mock_order.submitted_at = None
        mock_order.filled_at = None
        mock_trading_client.submit_order.return_value = mock_order

        mock_conn.execute.return_value.fetchone.return_value = (43,)
        mock_conn_getter.return_value = mock_conn

        req = OrderRequest(
            ticker="AAPL", side="sell", order_type="limit",
            quantity=50, price=150.0, time_in_force="gtc",
        )
        result = alpaca_client.place_order(req)

        assert result.success is True
        assert result.alpaca_order_id == "uuid-456"

    def test_place_order_alpaca_error(self, alpaca_client, mock_trading_client):
        from app.engines.trading.schemas import OrderRequest

        mock_trading_client.submit_order.side_effect = Exception("Alpaca API error")

        req = OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100)
        result = alpaca_client.place_order(req)

        assert result.success is False
        assert "Alpaca API error" in result.message


class TestCancelOrder:
    def test_cancel_order_by_id(self, alpaca_client, mock_trading_client):
        from app.engines.trading.schemas import CancelRequest

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("uuid-abc",)

        with patch("app.database.get_connection", return_value=mock_conn):
            req = CancelRequest(order_id=1)
            result = alpaca_client.cancel_order(req)

        assert result.success is True
        mock_trading_client.cancel_order_by_id.assert_called_with("uuid-abc")

    def test_cancel_order_by_alpaca_id(self, alpaca_client, mock_trading_client):
        from app.engines.trading.schemas import CancelRequest

        req = CancelRequest(alpaca_order_id="uuid-direct")
        result = alpaca_client.cancel_order(req)

        assert result.success is True
        mock_trading_client.cancel_order_by_id.assert_called_with("uuid-direct")


class TestModifyOrder:
    def _setup_modify_mocks(self, mock_trading_client, db_row):
        mock_order = MagicMock()
        mock_order.id = "uuid-new"
        mock_order.symbol = "AAPL"
        mock_order.side = MagicMock()
        mock_order.side.value = "buy"
        mock_order.type = MagicMock()
        mock_order.type.value = "market"
        mock_order.time_in_force = MagicMock()
        mock_order.time_in_force.value = "day"
        mock_order.qty = "200"
        mock_order.filled_qty = "0"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.status = MagicMock()
        mock_order.status.value = "accepted"
        mock_order.filled_avg_price = None
        mock_order.submitted_at = None
        mock_order.filled_at = None
        mock_trading_client.submit_order.return_value = mock_order

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.side_effect = [
            db_row,
            (42,),
        ]
        return mock_conn

    def test_modify_order_quantity(self, alpaca_client, mock_trading_client):
        from app.engines.trading.schemas import ModifyRequest

        mock_conn = self._setup_modify_mocks(
            mock_trading_client,
            ("uuid-abc", "AAPL", "buy", "market", 100, None, None, "day", "equity", ""),
        )

        with patch("app.database.get_connection", return_value=mock_conn):
            req = ModifyRequest(order_id=1, quantity=200)
            result = alpaca_client.modify_order(req)

        assert result.success is True
        mock_trading_client.cancel_order_by_id.assert_called_with("uuid-abc")
        mock_trading_client.submit_order.assert_called_once()

    def test_modify_order_price(self, alpaca_client, mock_trading_client):
        from app.engines.trading.schemas import ModifyRequest

        mock_conn = self._setup_modify_mocks(
            mock_trading_client,
            ("uuid-abc", "AAPL", "buy", "limit", 100, 150.0, None, "day", "equity", ""),
        )

        with patch("app.database.get_connection", return_value=mock_conn):
            req = ModifyRequest(order_id=1, price=155.0)
            result = alpaca_client.modify_order(req)

        assert result.success is True
        mock_trading_client.cancel_order_by_id.assert_called_with("uuid-abc")


class TestListOrders:
    def test_list_orders(self, alpaca_client):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            (1, "uuid-1", "AAPL", "buy", "market", 100, 0, None, None, "open",
             "equity", None, None, "2024-01-01", None, ""),
            (2, "uuid-2", "MSFT", "sell", "limit", 50, 0, 400.0, None,
             "open", "equity", None, None, "2024-01-02", None, ""),
        ]

        with patch("app.database.get_connection", return_value=mock_conn):
            orders = alpaca_client.list_orders(status="open", limit=50)

        assert len(orders) == 2
        assert orders[0].ticker == "AAPL"
        assert orders[1].ticker == "MSFT"


class TestSyncPositions:
    def test_sync_positions(self, alpaca_client, mock_trading_client):
        from alpaca.trading.models import Position

        mock_pos1 = MagicMock(spec=Position)
        mock_pos1.symbol = "AAPL"
        mock_pos1.qty = "100"
        mock_pos1.side = "long"
        mock_pos1.avg_entry_price = "150.0"
        mock_pos1.current_price = "155.0"
        mock_pos1.market_value = "15500.0"
        mock_pos1.cost_basis = "15000.0"
        mock_pos1.unrealized_pl = "500.0"
        mock_pos1.unrealized_plpc = "0.0333"

        mock_pos2 = MagicMock(spec=Position)
        mock_pos2.symbol = "MSFT"
        mock_pos2.qty = "50"
        mock_pos2.side = "long"
        mock_pos2.avg_entry_price = "380.0"
        mock_pos2.current_price = "390.0"
        mock_pos2.market_value = "19500.0"
        mock_pos2.cost_basis = "19000.0"
        mock_pos2.unrealized_pl = "500.0"
        mock_pos2.unrealized_plpc = "0.0263"

        mock_trading_client.get_all_positions.return_value = [mock_pos1, mock_pos2]
        mock_conn = MagicMock()

        with patch("app.database.get_connection", return_value=mock_conn):
            result = alpaca_client.sync_positions()

        assert result.success is True
        assert "Synced 2 positions" in result.message
        mock_conn.execute.assert_any_call("DELETE FROM positions")


class TestInitialization:
    def test_initialization_with_empty_key(self):
        from app.engines.trading.service import AlpacaClient

        with patch("app.config.settings") as mock_settings:
            mock_settings.alpaca_api_key = ""
            mock_settings.alpaca_secret_key = ""
            mock_settings.database_path = "/tmp/test.db"
            client = AlpacaClient()

        assert client.enabled is False
        from app.engines.trading.schemas import OrderRequest
        result = client.place_order(OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100))
        assert result.success is False
        assert "not configured" in result.message
