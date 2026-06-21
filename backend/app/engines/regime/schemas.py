from pydantic import BaseModel, field_validator

AVAILABLE_REGIMES = ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]


class RegimePrediction(BaseModel):
    regime: str
    probability: float
    confidence: float
    explanation: str = ""

    @field_validator("regime")
    @classmethod
    def validate_regime(cls, v: str) -> str:
        if v not in AVAILABLE_REGIMES:
            raise ValueError(f"Invalid regime: {v}. Must be one of {AVAILABLE_REGIMES}")
        return v

    @field_validator("probability", "confidence")
    @classmethod
    def validate_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        return v


class RegimeRequest(BaseModel):
    ticker: str = "SPY"
    n_states: int = 4
    lookback_days: int = 756

    @field_validator("n_states")
    @classmethod
    def validate_n_states(cls, v: int) -> int:
        if not 2 <= v <= 6:
            raise ValueError("n_states must be between 2 and 6")
        return v


class RegimeResponse(BaseModel):
    ticker: str
    overall_regime: RegimePrediction
    state_probabilities: dict[str, float]
    trained_on_bars: int
