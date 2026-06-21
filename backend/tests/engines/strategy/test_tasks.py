from unittest.mock import patch


class TestStrategyTasks:
    @patch("app.engines.strategy.tasks.select_strategy")
    def test_compute_strategy_task(self, mock_select):
        from app.engines.strategy.tasks import compute_strategy
        from app.engines.strategy.schemas import StrategyOutput
        mock_select.return_value = StrategyOutput(ticker="AAPL",
            recommendation="buy_leaps", confidence=0.85,
            reasoning="Bullish", risk_assessment="Moderate")
        result = compute_strategy("AAPL", {"regime": "Bull", "regime_score": 80.0})
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["recommendation"] == "buy_leaps"

    @patch("app.engines.strategy.tasks.select_strategy")
    def test_compute_strategy_error(self, mock_select):
        from app.engines.strategy.tasks import compute_strategy
        mock_select.side_effect = Exception("fail")
        result = compute_strategy("AAPL", {})
        assert result["status"] == "error"

    @patch("app.engines.strategy.tasks.compute_strategy")
    def test_compute_all_strategies(self, mock_compute):
        from app.engines.strategy.tasks import compute_all_strategies
        mock_compute.return_value = {"status": "success", "recommendation": "hold"}
        results = compute_all_strategies()
        assert len(results) > 0
