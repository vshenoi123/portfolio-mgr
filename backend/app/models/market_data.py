from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator


class OHLCVBar(BaseModel):
    ticker: str
    timestamp: datetime
    open: float
    low: float
    high: float
    close: float
    volume: int
    vwap: float | None = None
    trades: int | None = None

    @field_validator("high")
    @classmethod
    def high_must_be_above_low(cls, v: float, info) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price cannot be negative")
        return v

    @field_validator("volume")
    @classmethod
    def volume_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("volume cannot be negative")
        return v


class OptionsContract(BaseModel):
    ticker: str
    expiration: datetime
    strike: float
    option_type: Literal["call", "put"]
    bid: float
    ask: float
    implied_vol: float
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    volume: int = 0
    open_interest: int = 0

    @field_validator("option_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("call", "put"):
            raise ValueError("option_type must be 'call' or 'put'")
        return v

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2
