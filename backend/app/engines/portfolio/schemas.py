from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class PortfolioPosition(BaseModel):
    ticker: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float = 0.0
    cost_basis: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0
    weight_pct: float = 0.0
    beta: float = 1.0
    delta: float = 1.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    sector: str = "UNKNOWN"
    strategy_type: str = "equity"

    def __init__(self, **data):
        super().__init__(**data)
        if self.market_value == 0.0:
            self.market_value = round(self.quantity * self.current_price, 2)
        if self.cost_basis == 0.0:
            self.cost_basis = round(self.quantity * self.avg_price, 2)
        if self.unrealized_pl == 0.0:
            self.unrealized_pl = round(self.market_value - self.cost_basis, 2)
        if self.unrealized_pl_pct == 0.0 and self.cost_basis > 0:
            self.unrealized_pl_pct = round((self.unrealized_pl / self.cost_basis) * 100, 2)


class PortfolioState(BaseModel):
    total_value: float = 0.0
    cash: float = 0.0
    equity_value: float = 0.0
    options_value: float = 0.0
    num_positions: int = 0
    num_options: int = 0
    positions: list[dict] = []
    options_positions: list[dict] = []
    sector_exposures: dict = {}
    portfolio_beta: float = 0.0
    portfolio_delta_e: float = 0.0

    @property
    def cash_pct(self) -> float:
        if self.total_value > 0:
            return round((self.cash / self.total_value) * 100, 2)
        return 0.0


class PortfolioImpactScore(BaseModel):
    ticker: str
    raw_opportunity_score: float
    adjusted_score: float = 0.0
    impact_factors: list[dict] = []

    def __init__(self, **data):
        super().__init__(**data)
        if self.adjusted_score == 0.0 and "raw_opportunity_score" in data:
            self.adjusted_score = data["raw_opportunity_score"]


class CorrelationPair(BaseModel):
    ticker_a: str
    ticker_b: str
    correlation: float

    @field_validator("correlation")
    @classmethod
    def validate_correlation(cls, v: float) -> float:
        if not -1 <= v <= 1:
            raise ValueError("Correlation must be between -1 and 1")
        return v


class HoldingDetail(BaseModel):
    ticker: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0
    weight_pct: float = 0.0
    sector: str = "UNKNOWN"
    beta: float = 1.0
    days_held: int = 0
    strategy_type: str = "equity"
    active_risk_score: float = 0.0
    details: dict = {}


class PortfolioSummaryResponse(BaseModel):
    total_value: float
    cash: float
    equity_value: float
    options_value: float
    num_positions: int
    num_options: int
    portfolio_beta: float
    portfolio_delta_e: float
    portfolio_health_score: float = 100.0
    top_holdings: list[HoldingDetail] = []
    details: dict = {}
