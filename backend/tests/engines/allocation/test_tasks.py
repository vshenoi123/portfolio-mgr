import pytest
from unittest.mock import patch, MagicMock


class TestAllocationTasks:
    @patch("app.engines.portfolio.service.load_portfolio_state")
    def test_run_daily_allocation(self, mock_load):
        from app.engines.allocation.tasks import run_daily_allocation
        from app.engines.portfolio.schemas import PortfolioState
        mock_load.return_value = PortfolioState(total_value=100000, cash=25000)
        result = run_daily_allocation(regime="Bull")
        assert result["status"] == "success"
        assert result["regime"] == "Bull"

    def test_run_daily_allocation_error(self):
        from app.engines.allocation.tasks import run_daily_allocation
        result = run_daily_allocation(regime="Invalid")
        assert result["status"] == "error"
