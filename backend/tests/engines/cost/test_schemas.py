import pytest
from pydantic import ValidationError


class TestCostSchemas:
    def test_opportunity_cost_item_valid(self):
        from app.engines.cost.schemas import OpportunityCostItem
        item = OpportunityCostItem(candidate="AAPL", score=85.0, cost_type="new_position",
            rationale="Strong setup", estimated_return_pct=15.0, risk_score=5.0, capital_required=10000)
        assert item.candidate == "AAPL"

    def test_opportunity_cost_item_score_out_of_range(self):
        from app.engines.cost.schemas import OpportunityCostItem
        with pytest.raises(ValidationError):
            OpportunityCostItem(candidate="AAPL", score=150.0, cost_type="test", rationale="")

    def test_opportunity_cost_ranking_valid(self):
        from app.engines.cost.schemas import OpportunityCostRanking
        ranking = OpportunityCostRanking(candidates=[{"candidate": "AAPL", "final_score": 85.0}],
            cash_available=50000.0, total_portfolio_value=250000.0, recommendation="Buy AAPL")
        assert len(ranking.candidates) == 1
