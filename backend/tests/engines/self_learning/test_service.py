from unittest.mock import patch, MagicMock
from datetime import datetime


class MockRow:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, idx):
        return self._values[idx]

    def __iter__(self):
        return iter(self._values)


class TestLogTrade:
    def test_log_trade_success(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            from app.engines.self_learning.service import log_trade
            result = log_trade("AAPL", "buy", "momentum", 150.0, 100)
            assert result["status"] == "success"
            assert result["ticker"] == "AAPL"
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    def test_log_trade_with_date_and_regime(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            from app.engines.self_learning.service import log_trade
            dt = datetime(2024, 1, 15, 12, 0, 0)
            result = log_trade("NVDA", "sell", "swing", 800.0, 50,
                               entry_date=dt, regime="Bull")
            assert result["status"] == "success"


class TestCloseTrade:
    def test_close_trade_success(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = MockRow((100.0, 10, datetime(2024, 1, 1, 12, 0, 0)))
            from app.engines.self_learning.service import close_trade
            result = close_trade(1, 110.0, exit_reason="target_hit", regime="Bull")
            assert result["status"] == "success"
            assert result["gross_pl"] == 100.0
            mock_conn.close.assert_called_once()

    def test_close_trade_not_found(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = None
            from app.engines.self_learning.service import close_trade
            result = close_trade(999, 110.0)
            assert result["status"] == "error"
            assert "not found" in result["message"]


class TestComputeSignalEfficacy:
    def test_empty_trades(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = MockRow((0, 0, 0, 0))
            mock_conn.execute.return_value.fetchall.return_value = []
            from app.engines.self_learning.service import compute_signal_efficacy
            result = compute_signal_efficacy(db_path=":memory:")
            assert result.total_trades == 0
            assert result.win_rate == 0.0
            assert result.strategy_breakdown == {}

    def test_with_trades(self):
        with patch("duckdb.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = MockRow((10, 200, -100, 0.6))
            mock_conn.execute.return_value.fetchall.return_value = [
                MockRow(("momentum", 6, 150.0)),
                MockRow(("swing", 4, 80.0)),
            ]
            from app.engines.self_learning.service import compute_signal_efficacy
            result = compute_signal_efficacy(db_path=":memory:")
            assert result.total_trades == 10
            assert result.win_rate == 60.0
            assert result.avg_win == 200.0
            assert result.avg_loss == 100.0
            assert "momentum" in result.strategy_breakdown
            assert result.strategy_breakdown["momentum"]["count"] == 6

    def test_db_path_fallback(self):
        with (
            patch("duckdb.connect") as mock_connect,
            patch("app.config.settings") as mock_settings,
        ):
            mock_settings.database_path = "/tmp/test.db"
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchone.return_value = MockRow((0, 0, 0, 0))
            mock_conn.execute.return_value.fetchall.return_value = []
            from app.engines.self_learning.service import compute_signal_efficacy
            result = compute_signal_efficacy()
            assert result.total_trades == 0
