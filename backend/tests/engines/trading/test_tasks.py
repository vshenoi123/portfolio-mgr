from unittest.mock import MagicMock, patch


class TestSyncPositionsTask:
    @patch("app.engines.trading.service.AlpacaClient")
    def test_sync_positions_success(self, mock_client_cls):
        from app.engines.trading.tasks import sync_positions

        mock_instance = MagicMock()
        mock_instance.enabled = True
        mock_instance.sync_positions.return_value = MagicMock(
            success=True, message="Synced 3 positions",
        )
        mock_client_cls.return_value = mock_instance

        result = sync_positions()
        assert result["status"] == "success"
        assert "Synced 3" in result["message"]

    @patch("app.engines.trading.service.AlpacaClient")
    def test_sync_positions_disabled(self, mock_client_cls):
        from app.engines.trading.tasks import sync_positions

        mock_instance = MagicMock()
        mock_instance.enabled = False
        mock_client_cls.return_value = mock_instance

        result = sync_positions()
        assert result["status"] == "skipped"

    @patch("app.engines.trading.service.AlpacaClient")
    def test_sync_positions_error(self, mock_client_cls):
        from app.engines.trading.tasks import sync_positions

        mock_client_cls.side_effect = Exception("Connection failed")

        result = sync_positions()
        assert result["status"] == "error"
        assert "Connection failed" in result["message"]


class TestPlaceOrderTask:
    @patch("app.engines.trading.service.AlpacaClient")
    def test_place_order_success(self, mock_client_cls):
        from app.engines.trading.tasks import place_order_task

        mock_instance = MagicMock()
        mock_instance.place_order.return_value = MagicMock(
            success=True, message="Order placed",
            order_id=42, alpaca_order_id="uuid-abc",
        )
        mock_client_cls.return_value = mock_instance

        result = place_order_task("AAPL", "buy", "market", 100)
        assert result["status"] == "success"
        assert result["order_id"] == 42

    @patch("app.engines.trading.service.AlpacaClient")
    def test_place_order_error(self, mock_client_cls):
        from app.engines.trading.tasks import place_order_task

        mock_instance = MagicMock()
        mock_instance.place_order.return_value = MagicMock(
            success=False, message="API error",
            order_id=None, alpaca_order_id=None,
        )
        mock_client_cls.return_value = mock_instance

        result = place_order_task("AAPL", "buy", "market", 100)
        assert result["status"] == "error"

    @patch("app.engines.trading.service.AlpacaClient")
    def test_place_order_task_exception(self, mock_client_cls):
        from app.engines.trading.tasks import place_order_task

        mock_client_cls.side_effect = Exception("Broker error")

        result = place_order_task("AAPL", "buy", "market", 100)
        assert result["status"] == "error"
        assert "Broker error" in result["message"]
