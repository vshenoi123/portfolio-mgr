import pytest
from unittest.mock import patch, MagicMock, ANY


class TestPortfolioTasks:
    @patch("app.engines.portfolio.tasks.duckdb")
    @patch("app.engines.risk.service.assess_portfolio_risk")
    @patch("app.engines.portfolio.service.load_portfolio_state")
    def test_compute_portfolio_snapshot(self, mock_load, mock_risk, mock_duckdb):
        from app.engines.portfolio.tasks import compute_portfolio_snapshot
        from app.engines.portfolio.schemas import PortfolioState
        mock_load.return_value = PortfolioState(total_value=100000, cash=25000,
            equity_value=70000, options_value=5000,
            portfolio_beta=1.1, portfolio_delta_e=200)
        mock_risk.return_value = MagicMock(portfolio_health_score=85.0, concentration_pct=25.0)
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        result = compute_portfolio_snapshot()
        assert result["status"] == "success"
        assert result["health_score"] == 85.0

    @patch("app.engines.risk.service.assess_portfolio_risk")
    def test_compute_portfolio_snapshot_error(self, mock_risk):
        from app.engines.portfolio.tasks import compute_portfolio_snapshot
        mock_risk.side_effect = Exception("fail")
        result = compute_portfolio_snapshot()
        assert result["status"] == "error"
