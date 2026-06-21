from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, field_validator


class DataRefreshRequest(BaseModel):
    ticker: str
    days: int = 365

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("days")
    @classmethod
    def days_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class DataRefreshResponse(BaseModel):
    ticker: str
    status: str
    bars_fetched: int = 0
    message: str = ""


class DataQuery(BaseModel):
    ticker: str
    start_date: datetime
    end_date: datetime = datetime.now(timezone.utc)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class DataHealthResponse(BaseModel):
    tickers_in_universe: int
    total_ohlcv_bars: int = 0
    last_refresh: datetime | None = None
    status: str = "healthy"
