from typing import Literal
from pydantic import BaseModel, field_validator

ActionType = Literal["keep", "reduce", "exit", "replace"]


class PositionEvaluation(BaseModel):
    ticker: str
    score: float
    action: ActionType
    rationale: str
    details: dict = {}

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v


class TradeReplacement(BaseModel):
    current_ticker: str
    current_score: float
    replacement_ticker: str
    replacement_score: float
    rationale: str = ""
    estimated_upside_pct: float = 0.0
    confidence: float = 0.0


class ReplacementResponse(BaseModel):
    evaluations: list[PositionEvaluation] = []
    replacements: list[TradeReplacement] = []
    total_positions_evaluated: int = 0
    details: dict = {}
