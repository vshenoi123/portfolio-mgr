from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, field_validator


class ChangePointResult(BaseModel):
    detected: bool
    direction: Literal["positive", "negative", "none"]
    change_probability: float
    days_since_change: int | None = None
    cumulative_deviation: float = 0.0

    @field_validator("change_probability")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("change_probability must be between 0 and 1")
        return v


class CUSUMResponse(BaseModel):
    ticker: str
    cusum_result: ChangePointResult | None = None
    analyzed_bars: int = 0
    generated_at: datetime = datetime.now(timezone.utc)
