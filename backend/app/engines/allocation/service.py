import duckdb
from datetime import date
from app.database import _init_schema
from app.engines.allocation.schemas import AllocationRequest, AllocationResult, StrategyAllocation

_STRATEGY_ALLOCATIONS: dict[str, list[StrategyAllocation]] = {
    "Bull": [StrategyAllocation(strategy="leaps", allocation_pct=35, max_positions=3,
                rationale="Strong trend supports long-dated calls"),
             StrategyAllocation(strategy="equity", allocation_pct=25, max_positions=5,
                rationale="Direct equity exposure in bullish regime"),
             StrategyAllocation(strategy="swing", allocation_pct=20, max_positions=4,
                rationale="Short-term momentum plays"),
             StrategyAllocation(strategy="csp", allocation_pct=12, max_positions=5,
                rationale="Premium collection with bullish tailwind"),
             StrategyAllocation(strategy="pmcc", allocation_pct=8, max_positions=3,
                rationale="Income on bullish thesis")],
    "Bull High Vol": [StrategyAllocation(strategy="swing", allocation_pct=30, max_positions=4),
                      StrategyAllocation(strategy="csp", allocation_pct=25, max_positions=5),
                      StrategyAllocation(strategy="equity", allocation_pct=20, max_positions=4),
                      StrategyAllocation(strategy="leaps", allocation_pct=15, max_positions=2),
                      StrategyAllocation(strategy="pmcc", allocation_pct=10, max_positions=3)],
    "Bear": [StrategyAllocation(strategy="cash", allocation_pct=40, max_positions=0),
             StrategyAllocation(strategy="csp", allocation_pct=30, max_positions=5),
             StrategyAllocation(strategy="swing", allocation_pct=15, max_positions=3),
             StrategyAllocation(strategy="pmcc", allocation_pct=10, max_positions=2),
             StrategyAllocation(strategy="leaps", allocation_pct=5, max_positions=1)],
    "Bear High Vol": [StrategyAllocation(strategy="cash", allocation_pct=50, max_positions=0),
                      StrategyAllocation(strategy="csp", allocation_pct=25, max_positions=4),
                      StrategyAllocation(strategy="swing", allocation_pct=15, max_positions=3),
                      StrategyAllocation(strategy="pmcc", allocation_pct=10, max_positions=2)],
    "Range": [StrategyAllocation(strategy="csp", allocation_pct=30, max_positions=5),
              StrategyAllocation(strategy="swing", allocation_pct=25, max_positions=4),
              StrategyAllocation(strategy="pmcc", allocation_pct=20, max_positions=3),
              StrategyAllocation(strategy="equity", allocation_pct=15, max_positions=3),
              StrategyAllocation(strategy="leaps", allocation_pct=10, max_positions=2)],
    "Crisis": [StrategyAllocation(strategy="cash", allocation_pct=70, max_positions=0),
               StrategyAllocation(strategy="csp", allocation_pct=15, max_positions=2),
               StrategyAllocation(strategy="swing", allocation_pct=10, max_positions=2),
               StrategyAllocation(strategy="pmcc", allocation_pct=5, max_positions=1)],
}

_DEFAULT_ALLOCATIONS = [
    StrategyAllocation(strategy="cash", allocation_pct=30, max_positions=0),
    StrategyAllocation(strategy="csp", allocation_pct=25, max_positions=4),
    StrategyAllocation(strategy="swing", allocation_pct=20, max_positions=3),
    StrategyAllocation(strategy="equity", allocation_pct=15, max_positions=3),
    StrategyAllocation(strategy="leaps", allocation_pct=10, max_positions=2),
]

_CAPACITY_FACTOR: dict[str, dict[str, float]] = {
    "Bull": {"leaps": 1.0, "equity": 1.0, "swing": 0.8, "csp": 0.5, "pmcc": 0.5},
    "Bear": {"leaps": 0.1, "equity": 0.2, "swing": 0.5, "csp": 0.8, "pmcc": 0.6},
    "Range": {"leaps": 0.4, "equity": 0.5, "swing": 0.8, "csp": 1.0, "pmcc": 1.0},
    "Crisis": {"leaps": 0.05, "equity": 0.1, "swing": 0.4, "csp": 0.5, "pmcc": 0.3},
    "Bull High Vol": {"swing": 0.9, "csp": 0.7, "equity": 0.6, "leaps": 0.4, "pmcc": 0.6},
    "Bear High Vol": {"csp": 0.7, "swing": 0.6, "pmcc": 0.5},
}


def kelly_criterion(win_probability: float, win_loss_ratio: float) -> float:
    if win_probability <= 0 or win_probability >= 1:
        return 0.0
    q = 1 - win_probability
    kelly = (win_probability * win_loss_ratio - q) / win_loss_ratio
    return round(float(max(-1, min(1, kelly))), 4)


def fractional_kelly(win_probability: float, win_loss_ratio: float, fraction: float = 0.25) -> float:
    full = kelly_criterion(win_probability, win_loss_ratio)
    return round(float(max(0, full * fraction)), 4)


def get_strategy_allocation(regime: str) -> list[StrategyAllocation]:
    return _STRATEGY_ALLOCATIONS.get(regime, _DEFAULT_ALLOCATIONS)


def _get_regime_capacity_factor(regime: str, strategy: str) -> float:
    regime_map = _CAPACITY_FACTOR.get(regime, {})
    return regime_map.get(strategy, 0.5)


def calculate_position_size(
    total_portfolio_value: float, cash_available: float,
    kelly_fraction_value: float, opportunity_score: float,
    strategy: str, regime: str,
    existing_position_value: float = 0.0,
) -> AllocationResult:
    cash_reserve = total_portfolio_value * 0.10
    usable_cash = max(0, cash_available - cash_reserve)

    score_factor = opportunity_score / 100.0
    capacity = _get_regime_capacity_factor(regime, strategy)

    strategy_allocs = get_strategy_allocation(regime)
    strategy_pct = 0.0
    for sa in strategy_allocs:
        if sa.strategy == strategy:
            strategy_pct = sa.allocation_pct
            break
    if strategy_pct == 0:
        strategy_pct = 20.0

    strategy_cap = total_portfolio_value * (strategy_pct / 100.0)
    existing_discount = max(0, 1.0 - (existing_position_value / strategy_cap))
    combined_factor = min(1.0, score_factor * capacity * existing_discount)
    base_size = usable_cash * combined_factor

    max_by_score = total_portfolio_value * (opportunity_score / 100.0) * 0.15
    position_size = min(base_size, strategy_cap, max_by_score, usable_cash)

    capital_pct = round((position_size / total_portfolio_value) * 100, 2) if total_portfolio_value > 0 else 0

    return AllocationResult(
        ticker="", position_size=round(position_size, 2),
        capital_pct=capital_pct, strategy_allocation_pct=strategy_pct,
        allocation_method="kelly", regime_at_allocation=regime,
        total_portfolio_value=round(total_portfolio_value, 2),
        cash_reserve=round(cash_reserve, 2),
        details={"score_factor": round(score_factor, 3), "capacity": capacity,
                 "usable_cash": round(usable_cash, 2), "strategy_cap": round(strategy_cap, 2)},
    )


def save_allocation(result: AllocationResult, strategy: str, db_path: str) -> None:
    conn = duckdb.connect(db_path)
    _init_schema(conn)
    try:
        conn.execute("""
            INSERT INTO capital_allocation (date, strategy, ticker, position_size, capital_pct,
                strategy_allocation_pct, allocation_method, regime_at_allocation,
                total_portfolio_value, cash_reserve)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date.today().isoformat(), strategy, result.ticker, result.position_size,
            result.capital_pct, result.strategy_allocation_pct, result.allocation_method,
            result.regime_at_allocation, result.total_portfolio_value, result.cash_reserve,
        ))
    finally:
        conn.close()
