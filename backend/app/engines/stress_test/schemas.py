from pydantic import BaseModel, Field, field_validator


class ScenarioDefinition(BaseModel):
    name: str
    equity_shock: float = Field(..., lt=0, description="Expected equity return shock (e.g., -0.50 for -50%)")
    bond_yield_shift: float = 0.0
    vol_shock: float = 0.0
    dollar_shock: float = 0.0
    credit_spread_widen: float = 0.0

    @field_validator("equity_shock")
    @classmethod
    def equity_shock_negative(cls, v: float) -> float:
        if v >= 0:
            raise ValueError("equity_shock must be negative")
        return v


PREDEFINED_SCENARIOS: dict[str, ScenarioDefinition] = {
    "2008 Crash": ScenarioDefinition(
        name="2008 Crash", equity_shock=-0.50, vol_shock=0.80, credit_spread_widen=0.05,
    ),
    "COVID Crash": ScenarioDefinition(
        name="COVID Crash", equity_shock=-0.35, vol_shock=0.60, bond_yield_shift=-0.01,
    ),
    "Dot-com Bust": ScenarioDefinition(
        name="Dot-com Bust", equity_shock=-0.49, vol_shock=0.50,
    ),
    "2022 Bear Market": ScenarioDefinition(
        name="2022 Bear Market", equity_shock=-0.25, vol_shock=0.30, bond_yield_shift=0.02,
    ),
    "1987 Black Monday": ScenarioDefinition(
        name="1987 Black Monday", equity_shock=-0.23, vol_shock=1.0,
    ),
}


class PortfolioPosition(BaseModel):
    ticker: str
    beta: float = 1.0
    market_value: float
    sector: str = "Unknown"

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class StressTestRequest(BaseModel):
    positions: list[PortfolioPosition]
    scenarios: list[str] = list(PREDEFINED_SCENARIOS.keys())
    custom_scenarios: list[ScenarioDefinition] = []


class StressTestResult(BaseModel):
    scenario_name: str
    total_portfolio_impact: float
    total_portfolio_impact_pct: float
    position_impacts: list[dict]
    top_vulnerable: list[str]