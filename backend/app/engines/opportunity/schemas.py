from pydantic import BaseModel, field_validator

VALID_STRATEGIES = ["swing", "csp", "leaps", "pmcc"]


class OpportunityScore(BaseModel):
    ticker: str
    total_score: float
    regime_score: float = 0.0
    breakout_score: float = 0.0
    relative_strength_score: float = 0.0
    cusum_score: float = 0.0
    volume_score: float = 0.0
    trend_score: float = 0.0
    refined_score: float | None = None
    strategy_type: str = "swing"
    rank: int = 0
    details: dict = {}

    @field_validator("total_score", "regime_score", "breakout_score",
                     "relative_strength_score", "cusum_score", "volume_score",
                     "trend_score", "refined_score")
    @classmethod
    def validate_score_range(cls, v: float | None) -> float | None:
        if v is not None and not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v


class OpportunityRequest(BaseModel):
    strategy_type: str = "all"
    top_n: int = 20
    min_score: float = 0.0
    include_refined: bool = True

    @field_validator("strategy_type")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v != "all" and v not in VALID_STRATEGIES:
            raise ValueError(f"Invalid strategy: {v}")
        return v


class OpportunityResponse(BaseModel):
    date: str
    opportunities: list[OpportunityScore] = []
    total_analyzed: int = 0
    engine_version: str = "0.1.0"
