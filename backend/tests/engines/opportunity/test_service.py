import pytest


class TestScoringFormula:
    def test_compute_opportunity_score_full(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=80.0, breakout_score=70.0,
            relative_strength_score=90.0, cusum_score=60.0,
            volume_score=50.0, trend_score=85.0,
        )
        assert result == pytest.approx(74.5, rel=0.01)

    def test_compute_opportunity_score_min(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=0, breakout_score=0,
            relative_strength_score=0, cusum_score=0,
            volume_score=0, trend_score=0,
        )
        assert result == 0.0

    def test_compute_opportunity_score_max(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=100, breakout_score=100,
            relative_strength_score=100, cusum_score=100,
            volume_score=100, trend_score=100,
        )
        assert result == 100.0

    def test_compute_opportunity_score_missing_score_defaults_zero(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=100.0, breakout_score=100.0,
            relative_strength_score=None, cusum_score=None,
            volume_score=None, trend_score=None,
        )
        assert result == pytest.approx(45.0, rel=0.01)

    def test_compute_opportunity_score_all_none(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=None, breakout_score=None,
            relative_strength_score=None, cusum_score=None,
            volume_score=None, trend_score=None,
        )
        assert result == 0.0

    def test_score_weights_sum_to_one(self):
        from app.engines.opportunity.service import SCORE_WEIGHTS
        total = sum(SCORE_WEIGHTS.values())
        assert total == pytest.approx(1.0, rel=0.01)


class TestOpportunityRanking:
    def test_rank_opportunities_sorts_by_score_desc(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="MSFT", total_score=90.0),
            OpportunityScore(ticker="NVDA", total_score=60.0),
        ]
        ranked = rank_opportunities(scores)
        assert ranked[0].ticker == "MSFT"
        assert ranked[1].ticker == "AAPL"
        assert ranked[2].ticker == "NVDA"
        assert ranked[0].rank == 1

    def test_rank_opportunities_top_n(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [OpportunityScore(ticker=f"T{i}", total_score=float(100 - i))
                  for i in range(20)]
        ranked = rank_opportunities(scores, top_n=5)
        assert len(ranked) == 5
        assert ranked[0].ticker == "T0"
        assert ranked[-1].ticker == "T4"

    def test_rank_opportunities_empty(self):
        from app.engines.opportunity.service import rank_opportunities
        assert rank_opportunities([]) == []

    def test_rank_opportunities_min_score_filter(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="MSFT", total_score=50.0),
        ]
        ranked = rank_opportunities(scores, min_score=60.0)
        assert len(ranked) == 1
        assert ranked[0].ticker == "AAPL"

    def test_filter_by_strategy_swing(self):
        from app.engines.opportunity.service import filter_by_strategy
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0, strategy_type="swing"),
            OpportunityScore(ticker="MSFT", total_score=80.0, strategy_type="csp"),
        ]
        filtered = filter_by_strategy(scores, "swing")
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"

    def test_filter_by_strategy_all(self):
        from app.engines.opportunity.service import filter_by_strategy
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0, strategy_type="swing"),
            OpportunityScore(ticker="MSFT", total_score=80.0, strategy_type="csp"),
        ]
        assert len(filter_by_strategy(scores, "all")) == 2

    def test_strategy_assignment_leaps(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=90.0, breakout_score=85.0,
            relative_strength_score=95.0, total_score=88.0,
        )
        assert result == "leaps"

    def test_strategy_assignment_swing(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=55.0, breakout_score=50.0,
            relative_strength_score=60.0, total_score=52.0,
        )
        assert result == "swing"

    def test_strategy_assignment_csp(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=65.0, breakout_score=60.0,
            relative_strength_score=55.0, total_score=66.0,
        )
        assert result == "csp"
