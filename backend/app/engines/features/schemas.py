from datetime import datetime, timezone
from pydantic import BaseModel, field_validator


class IndicatorRequest(BaseModel):
    ticker: str
    days: int = 365

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("ticker cannot be empty")
        return stripped.upper()


class IndicatorResponse(BaseModel):
    ticker: str
    indicators: dict[str, float]
    bars_analyzed: int
    generated_at: datetime = datetime.now(timezone.utc)
    engine_version: str = "0.1.0"


class EngineHealthResponse(BaseModel):
    engine: str
    status: str = "healthy"
    uptime_hours: float = 0.0
