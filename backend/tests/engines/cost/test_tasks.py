import pytest
from unittest.mock import patch, MagicMock


class TestCostTasks:
    @patch("app.engines.cost.tasks._load_opportunity_candidates")
    @patch("app.engines.portfolio.service.load_portfolio_state")
    def test_evaluate_opportunity_cost(self, mock_load, mock_candidates):
        from app.engines.cost.tasks import evaluate_opportunity_cost
        from app.engines.portfolio.schemas import PortfolioState
        mock_load.return_value = PortfolioState(total_value=100000, cash=25000)
        mock_candidates.return_value = [{"candidate": "AAPL", "score": 85}]
        result = evaluate_opportunity_cost()
        assert result["status"] == "success"

    @patch("app.engines.cost.tasks._load_opportunity_candidates")
    def test_evaluate_opportunity_cost_error(self, mock_candidates):
        from app.engines.cost.tasks import evaluate_opportunity_cost
        mock_candidates.side_effect = Exception("fail")
        result = evaluate_opportunity_cost()
        assert result["status"] == "error"
