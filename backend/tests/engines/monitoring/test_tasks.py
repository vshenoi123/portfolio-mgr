import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestMonitoringTasks:
    @patch("app.engines.monitoring.tasks.get_connection")
    @patch("app.engines.monitoring.tasks.close_connection")
    @patch("app.engines.monitoring.service.collect_monitoring_summary")
    def test_collect_monitoring_data_success(self, mock_summary, mock_close, mock_get_conn):
        from app.engines.monitoring.schemas import (
            MonitoringSummary, PortfolioSnapshot, PositionSnapshot,
            PortfolioHealthScore,
        )
        from app.engines.monitoring.tasks import collect_monitoring_data
        now = datetime.now(timezone.utc)
        mock_summary.return_value = MonitoringSummary(
            portfolio=PortfolioSnapshot(
                timestamp=now, total_value=100000.0, cash=25000.0,
                equity_value=70000.0, options_value=5000.0,
                num_positions=2, portfolio_beta=1.2, portfolio_delta_e=500.0,
            ),
            positions=[
                PositionSnapshot(ticker="AAPL", quantity=100, market_value=16500),
                PositionSnapshot(ticker="NVDA", quantity=50, market_value=4750),
            ],
            health=PortfolioHealthScore(score=85.0),
            timestamp=now,
        )
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        result = collect_monitoring_data()
        assert result["status"] == "success"
        assert result["health_score"] == 85.0
        assert result["num_positions"] == 2
        assert result["num_alerts"] == 0

    @patch("app.engines.monitoring.service.collect_monitoring_summary")
    def test_collect_monitoring_data_error(self, mock_summary):
        from app.engines.monitoring.tasks import collect_monitoring_data
        mock_summary.side_effect = Exception("DB failure")
        result = collect_monitoring_data()
        assert result["status"] == "error"
        assert "DB failure" in result["message"]
