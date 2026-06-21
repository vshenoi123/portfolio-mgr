from typing import Literal
from pydantic import BaseModel, field_validator

AVAILABLE_RECOMMENDATIONS = [
    "buy_stock", "buy_leaps", "sell_csp", "pmcc",
    "covered_call", "close", "roll", "hold", "avoid",
]

RecommendationType = Literal[
    "buy_stock", "buy_leaps", "sell_csp", "pmcc",
    "covered_call", "close", "roll", "hold", "avoid",
]


class StrategyOutput(BaseModel):
    ticker: str
    recommendation: RecommendationType
    confidence: float
    reasoning: str
    risk_assessment: str
    details: dict = {}

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class StrategyRequest(BaseModel):
    ticker: str


class StrategyResponse(BaseModel):
    ticker: str
    recommendation: str
    confidence: float
    reasoning: str
    risk_assessment: str
