import logging

from app.config import settings
from app.engines.positions.schemas import (
    CspEvaluation,
    LeapsEvaluation,
    ManagementResult,
    PmccEvaluation,
    SwingEvaluation,
    WatchdogResult,
)

logger = logging.getLogger(__name__)


def evaluate_csp(
    ticker: str,
    current_dte: int = 0,
    current_pl_pct: float = 0.0,
    current_delta: float = 0.0,
    days_to_expiration: int = 0,
    strike: float = 0.0,
    premium_collected: float = 0.0,
    current_premium: float = 0.0,
    underlying_price: float = 0.0,
) -> CspEvaluation:
    action = "hold"
    confidence = 0.5
    rationale = ""
    roll_candidate = ""
    dte = current_dte or days_to_expiration

    if dte <= settings.csp_roll_dte_threshold:
        action = "roll"
        confidence = 0.8
        rationale = f"Only {dte} DTE remaining (threshold: {settings.csp_roll_dte_threshold})"
        roll_candidate = f"{ticker} {settings.csp_roll_dte_threshold + 30}d put"
    elif current_pl_pct >= settings.csp_close_profit_max_pct:
        action = "close"
        confidence = 0.9
        rationale = f"Profit target reached: {current_pl_pct:.1f}% (max: {settings.csp_close_profit_max_pct}%)"
    elif current_pl_pct >= settings.csp_close_profit_min_pct:
        action = "close"
        confidence = 0.7
        rationale = f"Profit target range: {current_pl_pct:.1f}% (min: {settings.csp_close_profit_min_pct}%)"
    elif abs(current_delta) > 0.30:
        action = "roll"
        confidence = 0.6
        rationale = f"Delta {current_delta:.2f} approaching ATM, consider rolling"
        roll_candidate = f"{ticker} {int(dte * 1.5)}d put lower strike"
    else:
        rationale = f"CSP healthy: {dte} DTE, P&L {current_pl_pct:.1f}%, delta {current_delta:.2f}"

    return CspEvaluation(
        ticker=ticker,
        strategy_type="csp",
        action=action,
        confidence=round(confidence, 2),
        rationale=rationale,
        current_dte=dte,
        current_pl_pct=current_pl_pct,
        current_delta=current_delta,
        days_to_expiration=days_to_expiration,
        strike=strike,
        premium_collected=premium_collected,
        current_premium=current_premium,
        underlying_price=underlying_price,
        roll_candidate=roll_candidate,
        details={"roll_dte_threshold": settings.csp_roll_dte_threshold},
    )


def evaluate_leaps(
    ticker: str,
    entry_price: float = 0.0,
    current_price: float = 0.0,
    trend_status: str = "bullish",
    days_held: int = 0,
) -> LeapsEvaluation:
    pl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
    action = "hold"
    confidence = 0.5
    rationale = ""

    if pl_pct >= settings.leaps_exit_profit_target_pct:
        action = "exit"
        confidence = 0.85
        rationale = f"Profit target {pl_pct:.0f}% >= {settings.leaps_exit_profit_target_pct}%"
    elif trend_status == settings.leaps_trend_failure_threshold:
        action = "exit"
        confidence = 0.75
        rationale = f"Trend reversed to {trend_status}"
    elif pl_pct < -50:
        action = "exit"
        confidence = 0.7
        rationale = f"Loss {pl_pct:.0f}% exceeds 50% threshold"
    else:
        rationale = f"LEAPS held {days_held}d, P&L {pl_pct:.1f}%, trend {trend_status}"

    return LeapsEvaluation(
        ticker=ticker,
        strategy_type="leaps",
        action=action,
        confidence=round(confidence, 2),
        rationale=rationale,
        entry_price=entry_price,
        current_price=current_price,
        pl_pct=round(pl_pct, 2),
        trend_status=trend_status,
        days_held=days_held,
        details={"profit_target": settings.leaps_exit_profit_target_pct},
    )


def evaluate_swing(
    ticker: str,
    entry_price: float = 0.0,
    current_price: float = 0.0,
    highest_price: float = 0.0,
    lowest_price: float = 0.0,
) -> SwingEvaluation:
    pl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0
    trailing_stop = highest_price * (1 - settings.swings_trailing_stop_pct / 100)
    breakdown_stop = entry_price * (1 - settings.swings_breakdown_stop_pct / 100)
    profit_target = entry_price * (1 + settings.swings_profit_target_pct / 100)

    action = "hold"
    confidence = 0.5
    rationale = ""
    trailing_triggered = False

    if current_price <= trailing_stop:
        action = "trailing_stop"
        trailing_triggered = True
        confidence = 0.9
        rationale = f"Trailing stop triggered at ${current_price:.2f} (stop: ${trailing_stop:.2f})"
    elif current_price <= breakdown_stop:
        action = "exit"
        confidence = 0.85
        rationale = f"Breakdown stop at ${current_price:.2f} (stop: ${breakdown_stop:.2f})"
    elif current_price >= profit_target:
        action = "close"
        confidence = 0.8
        rationale = f"Profit target ${profit_target:.2f} reached"
    else:
        rationale = f"Swing: P&L {pl_pct:.1f}%, trail ${trailing_stop:.2f}, target ${profit_target:.2f}"

    return SwingEvaluation(
        ticker=ticker,
        strategy_type="swing",
        action=action,
        confidence=round(confidence, 2),
        rationale=rationale,
        entry_price=entry_price,
        current_price=current_price,
        highest_price=highest_price,
        lowest_price=lowest_price,
        pl_pct=round(pl_pct, 2),
        trailing_stop_triggered=trailing_triggered,
        details={
            "trailing_stop": round(trailing_stop, 2),
            "breakdown_stop": round(breakdown_stop, 2),
        },
    )


def evaluate_pmcc(
    ticker: str,
    short_call_strike: float = 0.0,
    short_call_dte: int = 0,
    short_call_pl_pct: float = 0.0,
    short_call_delta: float = 0.0,
    underlying_price: float = 0.0,
) -> PmccEvaluation:
    action = "hold"
    confidence = 0.5
    rationale = ""
    roll_strike = 0.0

    if short_call_dte <= settings.pmcc_short_call_dte_threshold:
        action = "roll"
        confidence = 0.85
        rationale = f"Short call at {short_call_dte} DTE (threshold: {settings.pmcc_short_call_dte_threshold})"
        roll_strike = round(underlying_price * 1.05, 2)
    elif short_call_pl_pct >= settings.pmcc_short_call_profit_target_pct:
        action = "roll"
        confidence = 0.8
        rationale = f"Short call profit {short_call_pl_pct:.1f}% >= {settings.pmcc_short_call_profit_target_pct}%"
        roll_strike = round(underlying_price * 1.05, 2)
    elif short_call_delta > 0.35:
        action = "adjust"
        confidence = 0.6
        rationale = f"Short call delta {short_call_delta:.2f} > 0.35, consider rolling up"
        roll_strike = round(short_call_strike * 1.1, 2)
    else:
        rationale = f"PMCC healthy: DTE {short_call_dte}, P&L {short_call_pl_pct:.1f}%, delta {short_call_delta:.2f}"

    return PmccEvaluation(
        ticker=ticker,
        strategy_type="pmcc",
        action=action,
        confidence=round(confidence, 2),
        rationale=rationale,
        short_call_strike=short_call_strike,
        short_call_dte=short_call_dte,
        short_call_pl_pct=short_call_pl_pct,
        short_call_delta=short_call_delta,
        underlying_price=underlying_price,
        roll_candidate_strike=roll_strike,
        details={},
    )


def run_watchdog(positions: list[dict]) -> WatchdogResult:
    from datetime import datetime

    actions: list[ManagementResult] = []
    for pos in positions:
        st = pos.get("strategy_type", "equity")
        ticker = pos.get("ticker", "")
        result = ManagementResult(
            ticker=ticker,
            strategy_type=st,
            action_taken="hold",
            success=True,
            message="No action needed",
        )
        actions.append(result)
    return WatchdogResult(
        timestamp=datetime.now(),
        positions_evaluated=len(positions),
        actions_taken=actions,
        summary=f"Evaluated {len(positions)} positions",
    )
