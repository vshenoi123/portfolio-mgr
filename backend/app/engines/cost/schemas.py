from pydantic import BaseModel, field_validator


class OpportunityCostItem(BaseModel):
    candidate: str
    score: float
    cost_type: str
    rationale: str
    estimated_return_pct: float = 0.0
    risk_score: float = 0.0
    capital_required: float = 0.0

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    @field_validator("risk_score")
    @classmethod
    def validate_risk(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Risk score must be non-negative")
        return v


class OpportunityCostRanking(BaseModel):
    candidates: list[dict] = []
    cash_available: float = 0.0
    total_portfolio_value: float = 0.0
    recommendation: str = ""
    details: dict = {}
