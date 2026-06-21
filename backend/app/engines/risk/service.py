import duckdb
import json
from app.engines.risk.schemas import RiskAssessment, TradeRiskCheck
from app.engines.portfolio.service import load_portfolio_state, compute_concentration


def calculate_portfolio_health(
    max_drawdown: float = 0, concentration_pct: float = 0,
    portfolio_beta: float = 0, total_exposure_pct: float = 0,
    cash_pct: float = 0, num_violations: int = 0,
    unrealized_volatility: float = 0,
) -> float:
    score = 100.0

    drawdown_penalty = min(60, max_drawdown * 1.5)
    score -= drawdown_penalty

    if concentration_pct > 40:
        conc_penalty = min(20, (concentration_pct - 40) * 0.8)
        score -= conc_penalty

    if portfolio_beta > 1.5:
        beta_penalty = min(15, (portfolio_beta - 1.5) * 20)
        score -= beta_penalty

    if total_exposure_pct > 80:
        exposure_penalty = min(15, (total_exposure_pct - 80) * 0.5)
        score -= exposure_penalty

    cash_bonus = min(10, cash_pct * 0.3)
    score += cash_bonus

    violation_penalty = min(20, num_violations * 5)
    score -= violation_penalty

    if unrealized_volatility > 0.35:
        vol_penalty = min(10, (unrealized_volatility - 0.35) * 30)
        score -= vol_penalty

    return round(float(max(0, min(100, score))), 2)


def check_position_size_limit(
    ticker: str, requested_size: float,
    total_portfolio_value: float, max_position_pct: float = 15.0,
) -> dict:
    limit = total_portfolio_value * (max_position_pct / 100)
    passed = requested_size <= limit
    return {"check": "position_size", "passed": passed,
            "current": requested_size, "limit": round(limit, 2),
            "message": "OK" if passed else f"Position ${requested_size:.0f} exceeds {max_position_pct}% limit of ${limit:.0f}"}


def check_sector_exposure(
    sector: str, new_size: float,
    sector_exposures: dict, total_value: float,
    max_sector_pct: float = 30.0,
) -> dict:
    if sector == "UNKNOWN":
        return {"check": "sector_exposure", "passed": True,
                "message": f"Sector {sector}: unknown, allowing"}
    current_pct = sector_exposures.get(sector, 0)
    new_pct = ((current_pct / 100 * total_value) + new_size) / total_value * 100 if total_value > 0 else 0
    passed = new_pct <= max_sector_pct
    return {"check": "sector_exposure", "passed": passed,
            "current": round(new_pct, 2), "limit": max_sector_pct,
            "message": "OK" if passed else f"Sector {sector} would exceed {max_sector_pct}% limit"}


def check_portfolio_delta(new_delta: float, current_delta: float, max_delta: float = 500.0) -> dict:
    total = current_delta + new_delta
    passed = abs(total) <= max_delta
    return {"check": "portfolio_delta", "passed": passed,
            "current": round(total, 2), "limit": max_delta,
            "message": "OK" if passed else f"Portfolio delta {total:.0f} exceeds limit {max_delta}"}


def check_cash_available(
    requested_size: float, cash_available: float,
    min_cash_reserve_pct: float = 10.0, total_value: float = 0,
) -> dict:
    reserve = total_value * (min_cash_reserve_pct / 100)
    usable = cash_available - reserve
    passed = requested_size <= usable
    return {"check": "cash_available", "passed": passed,
            "current": requested_size, "available": round(usable, 2),
            "message": "OK" if passed else f"Insufficient cash: need ${requested_size:.0f}, have ${usable:.0f}"}


def validate_trade(
    ticker: str, requested_size: float,
    total_portfolio_value: float, cash_available: float,
    sector: str, sector_exposures: dict,
    current_delta: float = 0.0,
) -> TradeRiskCheck:
    checks = [
        check_position_size_limit(ticker, requested_size, total_portfolio_value),
        check_sector_exposure(sector, requested_size, sector_exposures, total_portfolio_value),
        check_portfolio_delta(0, current_delta),
        check_cash_available(requested_size, cash_available, total_value=total_portfolio_value),
    ]
    passed = sum(1 for c in checks if c["passed"])
    failed = len(checks) - passed
    return TradeRiskCheck(
        ticker=ticker, requested_size=requested_size,
        is_allowed=failed == 0, checks_passed=passed,
        checks_failed=failed, details=checks,
    )


def assess_portfolio_risk(
    db_path: str, max_drawdown: float = 0,
    total_value: float = 0, cash: float = 0,
) -> RiskAssessment:
    state = load_portfolio_state(db_path)

    tv = total_value or state.total_value
    cash_amt = cash or state.cash

    total_exposure = state.equity_value + state.options_value
    exposure_pct = (total_exposure / tv * 100) if tv > 0 else 0
    cash_pct = (cash_amt / tv * 100) if tv > 0 else 0

    positions_obj = []
    for p in state.positions:
        if isinstance(p, dict):
            pos = type('obj', (object,), p)()
        else:
            pos = p
        positions_obj.append(pos)

    concentration = compute_concentration(
        positions_obj, tv
    ) if hasattr(state, 'positions') and state.positions else 0

    violations = []
    if concentration > 40:
        violations.append({"type": "concentration", "value": concentration, "limit": 40})

    health = calculate_portfolio_health(
        max_drawdown=max_drawdown, concentration_pct=concentration,
        portfolio_beta=state.portfolio_beta,
        total_exposure_pct=exposure_pct, cash_pct=cash_pct,
        num_violations=len(violations),
    )

    return RiskAssessment(
        portfolio_health_score=health,
        max_drawdown=max_drawdown,
        current_exposure=round(total_exposure, 2),
        total_value=round(tv, 2),
        concentration_pct=round(concentration, 2),
        violations=violations,
        is_safe=health >= 50 and len(violations) == 0,
        details={"exposure_pct": round(exposure_pct, 2), "cash_pct": round(cash_pct, 2)},
    )
