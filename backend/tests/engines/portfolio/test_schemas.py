import pytest
from pydantic import ValidationError


class TestPortfolioSchemas:
    def test_portfolio_state_valid(self):
        from app.engines.portfolio.schemas import PortfolioState
        state = PortfolioState(total_value=100000.0, cash=30000.0,
                               equity_value=65000.0, options_value=5000.0)
        assert state.cash_pct == 30.0
        assert state.equity_value == 65000.0

    def test_portfolio_state_defaults(self):
        from app.engines.portfolio.schemas import PortfolioState
        state = PortfolioState()
        assert state.equity_value == 0.0
        assert state.sector_exposures == {}

    def test_portfolio_impact_score_valid(self):
        from app.engines.portfolio.schemas import PortfolioImpactScore
        score = PortfolioImpactScore(ticker="AAPL", raw_opportunity_score=95.0,
            adjusted_score=78.0, impact_factors=[{"name": "sector", "impact": -10}])
        assert score.raw_opportunity_score == 95.0
        assert score.adjusted_score == 78.0
        assert len(score.impact_factors) == 1

    def test_portfolio_impact_score_defaults(self):
        from app.engines.portfolio.schemas import PortfolioImpactScore
        score = PortfolioImpactScore(ticker="AAPL", raw_opportunity_score=80.0)
        assert score.adjusted_score == 80.0
        assert score.impact_factors == []

    def test_portfolio_position_valid(self):
        from app.engines.portfolio.schemas import PortfolioPosition
        pos = PortfolioPosition(ticker="AAPL", quantity=100.0,
                                avg_price=150.0, current_price=165.0)
        assert pos.market_value == 16500.0
        assert pos.unrealized_pl == 1500.0
        assert pos.weight_pct == 0.0  # no total_value for weight calc

    def test_portfolio_summary_response(self):
        from app.engines.portfolio.schemas import PortfolioSummaryResponse
        resp = PortfolioSummaryResponse(total_value=100000.0, cash=20000.0,
            equity_value=75000.0, options_value=5000.0, num_positions=5,
            num_options=2, portfolio_beta=1.2, portfolio_delta_e=250.0)
        assert resp.portfolio_beta == 1.2

    def test_correlation_pair_valid(self):
        from app.engines.portfolio.schemas import CorrelationPair
        cp = CorrelationPair(ticker_a="AAPL", ticker_b="MSFT", correlation=0.75)
        assert cp.correlation == 0.75

    def test_correlation_pair_rejects_out_of_range(self):
        from app.engines.portfolio.schemas import CorrelationPair
        with pytest.raises(ValidationError):
            CorrelationPair(ticker_a="AAPL", ticker_b="MSFT", correlation=1.5)

    def test_holding_extended_schema(self):
        from app.engines.portfolio.schemas import HoldingDetail
        h = HoldingDetail(ticker="AAPL", quantity=100.0, avg_price=150.0,
                          current_price=165.0, days_held=45, active_risk_score=8.5)
        assert h.days_held == 45
        assert h.active_risk_score == 8.5
