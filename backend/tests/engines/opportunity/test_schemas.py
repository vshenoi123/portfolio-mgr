import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestOpportunitySchemas:
    def test_opportunity_score_valid(self):
        from app.engines.opportunity.schemas import OpportunityScore
        score = OpportunityScore(
            ticker="AAPL", total_score=75.5, regime_score=80.0,
            breakout_score=70.0, relative_strength_score=85.0,
            cusum_score=60.0, volume_score=65.0, trend_score=90.0,
            refined_score=78.0, strategy_type="swing", rank=1,
        )
        assert score.ticker == "AAPL"
        assert 0 <= score.total_score <= 100
        assert score.strategy_type == "swing"

    def test_opportunity_score_defaults(self):
        from app.engines.opportunity.schemas import OpportunityScore
        score = OpportunityScore(ticker="AAPL", total_score=50.0)
        assert score.regime_score == 0.0
        assert score.refined_score is None
        assert score.rank == 0

    def test_opportunity_score_rejects_out_of_range(self):
        from app.engines.opportunity.schemas import OpportunityScore
        with pytest.raises(ValidationError):
            OpportunityScore(ticker="AAPL", total_score=150.0)
        with pytest.raises(ValidationError):
            OpportunityScore(ticker="AAPL", total_score=-10.0)

    def test_opportunity_request_valid(self):
        from app.engines.opportunity.schemas import OpportunityRequest
        req = OpportunityRequest(strategy_type="swing", top_n=10)
        assert req.strategy_type == "swing"
        assert req.top_n == 10

    def test_opportunity_request_rejects_invalid_strategy(self):
        from app.engines.opportunity.schemas import OpportunityRequest
        with pytest.raises(ValidationError):
            OpportunityRequest(strategy_type="invalid", top_n=5)

    def test_opportunity_response_valid(self):
        from app.engines.opportunity.schemas import OpportunityResponse, OpportunityScore
        resp = OpportunityResponse(
            date=datetime.now(timezone.utc).date().isoformat(),
            opportunities=[
                OpportunityScore(ticker="AAPL", total_score=75.0),
                OpportunityScore(ticker="NVDA", total_score=72.0),
            ], total_analyzed=50,
        )
        assert len(resp.opportunities) == 2
        assert resp.total_analyzed == 50

    def test_available_strategies(self):
        from app.engines.opportunity.schemas import VALID_STRATEGIES
        assert "swing" in VALID_STRATEGIES
        assert "csp" in VALID_STRATEGIES
        assert "leaps" in VALID_STRATEGIES
        assert "pmcc" in VALID_STRATEGIES
        assert len(VALID_STRATEGIES) == 4
