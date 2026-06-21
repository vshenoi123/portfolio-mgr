import pytest
from pydantic import ValidationError


class TestStrategySchemas:
    def test_strategy_output_valid(self):
        from app.engines.strategy.schemas import StrategyOutput
        out = StrategyOutput(
            ticker="SPY",
            recommendation="buy_stock",
            confidence=0.85,
            reasoning="Strong bullish trend with increasing volume",
            risk_assessment="Moderate risk, market at all-time highs",
        )
        assert out.ticker == "SPY"
        assert out.recommendation == "buy_stock"
        assert 0 <= out.confidence <= 1
        assert isinstance(out.details, dict)

    def test_strategy_output_rejects_invalid_recommendation(self):
        from app.engines.strategy.schemas import StrategyOutput
        with pytest.raises(ValidationError):
            StrategyOutput(
                ticker="SPY",
                recommendation="invalid_trade",
                confidence=0.85,
                reasoning="test",
                risk_assessment="test",
            )

    def test_strategy_output_rejects_confidence_out_of_range(self):
        from app.engines.strategy.schemas import StrategyOutput
        with pytest.raises(ValidationError):
            StrategyOutput(
                ticker="SPY",
                recommendation="hold",
                confidence=1.5,
                reasoning="test",
                risk_assessment="test",
            )
        with pytest.raises(ValidationError):
            StrategyOutput(
                ticker="SPY",
                recommendation="hold",
                confidence=-0.5,
                reasoning="test",
                risk_assessment="test",
            )

    def test_strategy_output_with_details(self):
        from app.engines.strategy.schemas import StrategyOutput
        out = StrategyOutput(
            ticker="AAPL",
            recommendation="sell_csp",
            confidence=0.72,
            reasoning="High IV percentile makes premium selling attractive",
            risk_assessment="Below delta threshold, defined risk",
            details={"strike": 180, "expiry": "2025-03-21", "iv_percentile": 0.65},
        )
        assert out.details["strike"] == 180
        assert out.details["iv_percentile"] == 0.65

    def test_strategy_request_valid(self):
        from app.engines.strategy.schemas import StrategyRequest
        req = StrategyRequest(ticker="SPY")
        assert req.ticker == "SPY"

    def test_strategy_response_valid(self):
        from app.engines.strategy.schemas import StrategyResponse
        resp = StrategyResponse(
            ticker="SPY",
            recommendation="buy_stock",
            confidence=0.85,
            reasoning="Strong trend",
            risk_assessment="Moderate",
        )
        assert resp.ticker == "SPY"

    def test_available_recommendations_list(self):
        from app.engines.strategy.schemas import AVAILABLE_RECOMMENDATIONS
        assert len(AVAILABLE_RECOMMENDATIONS) == 9
        assert "buy_stock" in AVAILABLE_RECOMMENDATIONS
        assert "buy_leaps" in AVAILABLE_RECOMMENDATIONS
        assert "sell_csp" in AVAILABLE_RECOMMENDATIONS
        assert "pmcc" in AVAILABLE_RECOMMENDATIONS
        assert "covered_call" in AVAILABLE_RECOMMENDATIONS
        assert "close" in AVAILABLE_RECOMMENDATIONS
        assert "roll" in AVAILABLE_RECOMMENDATIONS
        assert "hold" in AVAILABLE_RECOMMENDATIONS
        assert "avoid" in AVAILABLE_RECOMMENDATIONS
