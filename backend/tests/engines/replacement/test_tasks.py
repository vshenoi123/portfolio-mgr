import pytest
from unittest.mock import patch, MagicMock


class TestReplacementTasks:
    @patch("app.engines.replacement.tasks._load_opportunities_for_replacement")
    @patch("app.engines.portfolio.service.load_portfolio_state")
    def test_evaluate_replacements(self, mock_load, mock_opps):
        from app.engines.replacement.tasks import evaluate_replacements
        mock_load.return_value = MagicMock(total_value=100000, cash=25000,
            positions=[{"ticker": "AAPL", "unrealized_pl_pct": 5, "sector": "TECHNOLOGY",
                        "market_value": 10000}])
        mock_opps.return_value = [{"ticker": "NVDA", "score": 85, "sector": "TECHNOLOGY"}]
        result = evaluate_replacements()
        assert result["status"] == "success"

    def test_evaluate_replacements_error(self):
        from app.engines.replacement.tasks import evaluate_replacements
        result = evaluate_replacements()
        assert result["status"] == "error"
