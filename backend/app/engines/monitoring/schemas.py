from datetime import datetime
from pydantic import BaseModel, field_validator, computed_field


class PortfolioSnapshot(BaseModel):
    timestamp: datetime
    total_value: float = 0.0
    cash: float = 0.0
    equity_value: float = 0.0
    options_value: float = 0.0
    num_positions: int = 0
    portfolio_beta: float = 0.0
    portfolio_delta_e: float = 0.0


class PositionSnapshot(BaseModel):
    ticker: str
    quantity: float = 0.0
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0
    strategy_type: str = "equity"
    sector: str = "UNKNOWN"


class OrderSnapshot(BaseModel):
    alpaca_order_id: str = ""
    ticker: str = ""
    side: str = ""
    order_type: str = ""
    quantity: float = 0.0
    filled_qty: float = 0.0
    status: str = "pending"
    submitted_at: datetime | None = None


class PortfolioHealthScore(BaseModel):
    score: float
    components: dict = {}

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("Score must be 0-100")
        return v

    @computed_field
    @property
    def level(self) -> str:
        if self.score >= 60:
            return "healthy"
        elif self.score >= 30:
            return "warning"
        return "critical"


class AlertEvent(BaseModel):
    alert_type: str
    severity: str = "info"
    ticker: str = ""
    message: str = ""
    timestamp: datetime
    details: dict = {}


class MonitoringSummary(BaseModel):
    portfolio: PortfolioSnapshot | None = None
    positions: list[PositionSnapshot] = []
    open_orders: list[OrderSnapshot] = []
    health: PortfolioHealthScore | None = None
    alerts: list[AlertEvent] = []
    timestamp: datetime
