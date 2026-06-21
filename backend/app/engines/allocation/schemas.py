from pydantic import BaseModel, field_validator


class AllocationRequest(BaseModel):
    ticker: str
    opportunity_score: float
    total_portfolio_value: float = 100000.0
    cash_available: float = 50000.0
    regime: str = "Range"
    strategy: str = "swing"
    existing_position_value: float = 0.0
    win_probability: float = 0.55
    expected_return_pct: float = 10.0
    max_risk_pct: float = 2.0

    @field_validator("win_probability")
    @classmethod
    def validate_win_prob(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Win probability must be between 0 and 1")
        return v

    @field_validator("opportunity_score", "expected_return_pct", "max_risk_pct")
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class AllocationResult(BaseModel):
    ticker: str
    position_size: float
    capital_pct: float
    strategy_allocation_pct: float = 0.0
    allocation_method: str = "kelly"
    regime_at_allocation: str = "Unknown"
    total_portfolio_value: float = 0.0
    cash_reserve: float = 0.0
    details: dict = {}


class StrategyAllocation(BaseModel):
    strategy: str
    allocation_pct: float
    max_positions: int = 5
    rationale: str = ""

    @field_validator("allocation_pct")
    @classmethod
    def validate_allocation_pct(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("Allocation percentage must be between 0 and 100")
        return v
