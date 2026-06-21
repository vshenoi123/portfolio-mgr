from pydantic import BaseModel, field_validator, model_validator
from typing import Literal
import numpy as np


class MonteCarloRequest(BaseModel):
    ticker: str
    days: int = 252
    simulations: int = 10000
    method: Literal["historical", "parametric"] = "historical"

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("simulations")
    @classmethod
    def simulations_must_be_at_least_1000(cls, v: int) -> int:
        if v < 1000:
            raise ValueError("simulations must be >= 1000")
        return v

    @field_validator("days")
    @classmethod
    def days_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class MonteCarloResult(BaseModel):
    ticker: str
    simulations: int
    days: int
    method: str
    final_prices: np.ndarray
    returns: np.ndarray
    var_95: float
    var_99: float
    cvar_95: float
    max_drawdowns: np.ndarray
    median_final: float
    mean_final: float
    std_final: float

    @model_validator(mode="after")
    def var_99_more_negative_than_var_95(self):
        if self.var_99 > self.var_95:
            raise ValueError("var_99 must be <= var_95 (more negative for tail risk)")
        return self

    class Config:
        arbitrary_types_allowed = True


class PortfolioMonteCarloRequest(BaseModel):
    positions: list[dict]
    days: int = 252
    simulations: int = 10000

    @field_validator("simulations")
    @classmethod
    def simulations_must_be_at_least_1000(cls, v: int) -> int:
        if v < 1000:
            raise ValueError("simulations must be >= 1000")
        return v

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        total = sum(p["weight"] for p in self.positions)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"position weights must sum to 1.0, got {total}")
        return self