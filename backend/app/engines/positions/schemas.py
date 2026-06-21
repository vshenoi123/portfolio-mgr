from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator


class PositionSignal(BaseModel):
    ticker: str
    strategy_type: str
    action: Literal["close", "roll", "exit", "adjust", "hold", "trailing_stop"]
    confidence: float = 0.5
    rationale: str = ""
    details: dict = {}

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class CspEvaluation(PositionSignal):
    current_dte: int = 0
    current_pl_pct: float = 0.0
    current_delta: float = 0.0
    days_to_expiration: int = 0
    strike: float = 0.0
    premium_collected: float = 0.0
    current_premium: float = 0.0
    underlying_price: float = 0.0
    roll_candidate: str = ""


class LeapsEvaluation(PositionSignal):
    entry_price: float = 0.0
    current_price: float = 0.0
    pl_pct: float = 0.0
    trend_status: str = "bullish"
    days_held: int = 0


class SwingEvaluation(PositionSignal):
    entry_price: float = 0.0
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    pl_pct: float = 0.0
    trailing_stop_triggered: bool = False


class PmccEvaluation(PositionSignal):
    short_call_strike: float = 0.0
    short_call_dte: int = 0
    short_call_pl_pct: float = 0.0
    short_call_delta: float = 0.0
    underlying_price: float = 0.0
    roll_candidate_strike: float = 0.0


class ManagementResult(BaseModel):
    ticker: str
    strategy_type: str
    action_taken: str
    success: bool
    message: str = ""
    details: dict = {}


class WatchdogResult(BaseModel):
    timestamp: datetime
    positions_evaluated: int = 0
    actions_taken: list[ManagementResult] = []
    summary: str = ""
