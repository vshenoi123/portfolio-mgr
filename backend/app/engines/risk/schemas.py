from pydantic import BaseModel, field_validator


class RiskLimit(BaseModel):
    name: str
    value: float
    unit: str = ""
    description: str = ""
    enabled: bool = True


class RiskAssessment(BaseModel):
    portfolio_health_score: float
    max_drawdown: float = 0.0
    current_exposure: float = 0.0
    total_value: float = 0.0
    concentration_pct: float = 0.0
    violations: list[dict] = []
    is_safe: bool = True
    details: dict = {}

    @property
    def exposure_pct(self) -> float:
        if self.total_value > 0:
            return round((self.current_exposure / self.total_value) * 100, 2)
        return 0.0


class TradeRiskCheck(BaseModel):
    ticker: str
    requested_size: float
    is_allowed: bool = True
    checks_passed: int = 0
    checks_failed: int = 0
    details: list[dict] = []
