import pytest
from pydantic import ValidationError


class TestAllocationSchemas:
    def test_allocation_request_valid(self):
        from app.engines.allocation.schemas import AllocationRequest
        req = AllocationRequest(ticker="AAPL", opportunity_score=75.0,
                                total_portfolio_value=250000.0, cash_available=75000.0)
        assert req.ticker == "AAPL"
        assert req.opportunity_score == 75.0

    def test_allocation_request_defaults(self):
        from app.engines.allocation.schemas import AllocationRequest
        req = AllocationRequest(ticker="AAPL", opportunity_score=75.0)
        assert req.total_portfolio_value == 100000.0
        assert req.win_probability == 0.55

    def test_allocation_result_valid(self):
        from app.engines.allocation.schemas import AllocationResult
        res = AllocationResult(ticker="AAPL", position_size=15000.0,
                               capital_pct=15.0, strategy_allocation_pct=25.0)
        assert res.position_size == 15000.0

    def test_allocation_result_defaults(self):
        from app.engines.allocation.schemas import AllocationResult
        res = AllocationResult(ticker="AAPL", position_size=0.0, capital_pct=0.0)
        assert res.allocation_method == "kelly"

    def test_strategy_allocation_valid(self):
        from app.engines.allocation.schemas import StrategyAllocation
        sa = StrategyAllocation(strategy="leaps", allocation_pct=35.0)
        assert sa.allocation_pct == 35.0

    def test_strategy_allocation_out_of_range(self):
        from app.engines.allocation.schemas import StrategyAllocation
        with pytest.raises(ValidationError):
            StrategyAllocation(strategy="leaps", allocation_pct=150.0)
