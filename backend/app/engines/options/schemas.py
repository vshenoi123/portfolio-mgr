from typing import Literal
from pydantic import BaseModel, field_validator


class CSPOption(BaseModel):
    ticker: str
    strike: float
    expiration: str
    premium: float
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    bid: float
    ask: float
    last_price: float
    open_interest: int
    volume: int
    underlying_price: float
    days_to_expiration: int
    annualized_yield: float
    probability_of_profit: float
    live_data: bool = False
    strategy: Literal["csp"] = "csp"

    @field_validator("delta")
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if not -1 <= v <= 1:
            raise ValueError("delta must be between -1 and 1")
        return v

    @field_validator("annualized_yield")
    @classmethod
    def validate_yield(cls, v: float) -> float:
        if v < 0:
            raise ValueError("annualized_yield must be non-negative")
        return v


class LEAPSOption(BaseModel):
    ticker: str
    strike: float
    expiration: str
    premium: float
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    bid: float
    ask: float
    last_price: float
    open_interest: int
    volume: int
    underlying_price: float
    days_to_expiration: int
    leverage_factor: float
    intrinsic_value: float
    time_value: float
    live_data: bool = False
    strategy: Literal["leaps"] = "leaps"

    @field_validator("delta")
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("delta must be between 0 and 1 for long calls")
        return v

    @field_validator("leverage_factor")
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        if v < 0:
            raise ValueError("leverage_factor must be non-negative")
        return v


class PMMCOption(BaseModel):
    ticker: str
    long_strike: float
    short_strike: float
    long_expiration: str
    short_expiration: str
    long_premium: float
    short_premium: float
    net_debit: float
    max_profit: float
    max_loss: float
    break_even: float
    delta: float
    underlying_price: float
    days_to_long_expiration: int
    days_to_short_expiration: int
    probability_of_profit: float
    annualized_yield: float
    live_data: bool = False
    strategy: Literal["pmcc"] = "pmcc"

    @field_validator("net_debit")
    @classmethod
    def validate_net_debit(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("net_debit must be positive")
        return v


class CoveredCallOption(BaseModel):
    ticker: str
    strike: float
    expiration: str
    premium: float
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    bid: float
    ask: float
    last_price: float
    open_interest: int
    volume: int
    underlying_price: float
    days_to_expiration: int
    annualized_yield: float
    probability_of_profit: float
    live_data: bool = False
    strategy: Literal["covered_call"] = "covered_call"

    @field_validator("delta")
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("delta must be between 0 and 1 for short calls")
        return v

    @field_validator("annualized_yield")
    @classmethod
    def validate_yield(cls, v: float) -> float:
        if v < 0:
            raise ValueError("annualized_yield must be non-negative")
        return v


class OptionsGenerateRequest(BaseModel):
    ticker: str
    underlying_price: float
    implied_volatility: float
    risk_free_rate: float = 0.05
    dividend_yield: float = 0.0
    days_to_expiration: int
    target_delta: float = 0.30
    strategy: Literal["csp", "leaps", "pmcc", "covered_call"]
    max_premium: float | None = None

    @field_validator("underlying_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("underlying_price must be positive")
        return v

    @field_validator("implied_volatility")
    @classmethod
    def validate_iv(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("implied_volatility must be between 0 and 1")
        return v

    @field_validator("target_delta")
    @classmethod
    def validate_target_delta(cls, v: float) -> float:
        if not 0 < v <= 0.5:
            raise ValueError("target_delta must be between 0 and 0.5")
        return v

    @field_validator("days_to_expiration")
    @classmethod
    def validate_dte(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days_to_expiration must be positive")
        return v
