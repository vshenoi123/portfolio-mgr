from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, field_validator


class BreakoutSignal(BaseModel):
    ticker: str
    direction: Literal["bullish", "bearish"]
    strength: float
    breakout_type: str
    confirmed: bool = False

    @field_validator("strength")
    @classmethod
    def validate_strength(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("strength must be between 0 and 1")
        return v


class BreakoutResponse(BaseModel):
    ticker: str
    signals: list[BreakoutSignal] = []
    total_signals: int = 0
    max_strength: float = 0.0
    generated_at: datetime = datetime.now(timezone.utc)
