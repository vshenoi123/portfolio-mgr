from unittest.mock import patch


class TestPositionTasks:
    def test_run_watchdog_success(self):
        from app.engines.positions.tasks import run_position_watchdog
        with patch("app.engines.positions.tasks._load_positions") as mock_load:
            mock_load.return_value = [
                {"ticker": "AAPL", "strategy_type": "csp"},
                {"ticker": "MSFT", "strategy_type": "leaps"},
            ]
            result = run_position_watchdog()
            assert result["status"] == "success"
            assert result["positions_evaluated"] == 2

    def test_run_watchdog_empty(self):
        from app.engines.positions.tasks import run_position_watchdog
        with patch("app.engines.positions.tasks._load_positions") as mock_load:
            mock_load.return_value = []
            result = run_position_watchdog()
            assert result["status"] == "success"
            assert result["positions_evaluated"] == 0

    def test_run_watchdog_error(self):
        from app.engines.positions.tasks import run_position_watchdog
        with patch("app.engines.positions.tasks._load_positions") as mock_load:
            mock_load.side_effect = Exception("DB error")
            result = run_position_watchdog()
            assert result["status"] == "error"

    def test_load_positions_returns_list(self):
        from app.engines.positions.tasks import _load_positions
        result = _load_positions()
        assert isinstance(result, list)
