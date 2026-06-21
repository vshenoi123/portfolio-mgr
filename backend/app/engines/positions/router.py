import logging
from fastapi import APIRouter, Query
from app.engines.positions.schemas import CspEvaluation, PositionSignal, WatchdogResult
from app.engines.positions.service import evaluate_csp, evaluate_swing, run_watchdog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/positions", tags=["positions"])


@router.get("/evaluate/{ticker}")
def get_evaluate_position(ticker: str, strategy: str = Query("csp")):
    if strategy == "csp":
        result = evaluate_csp(ticker)
    else:
        result = CspEvaluation(ticker=ticker, strategy_type=strategy, action="hold")
    return result


@router.post("/evaluate")
def post_evaluate_position(signal: PositionSignal):
    return signal


@router.post("/watchdog")
def post_watchdog():
    positions = []
    result = run_watchdog(positions)
    return result


@router.get("/csp/{ticker}")
def get_csp_evaluation(
    ticker: str,
    current_dte: int = Query(30),
    current_pl_pct: float = Query(0.0),
    current_delta: float = Query(-0.25),
    days_to_expiration: int = Query(30),
    strike: float = Query(0.0),
    premium_collected: float = Query(0.0),
    current_premium: float = Query(0.0),
    underlying_price: float = Query(0.0),
):
    result = evaluate_csp(
        ticker=ticker,
        current_dte=current_dte,
        current_pl_pct=current_pl_pct,
        current_delta=current_delta,
        days_to_expiration=days_to_expiration,
        strike=strike,
        premium_collected=premium_collected,
        current_premium=current_premium,
        underlying_price=underlying_price,
    )
    return result


@router.get("/swing/{ticker}")
def get_swing_evaluation(
    ticker: str,
    entry_price: float = Query(0.0),
    current_price: float = Query(0.0),
    highest_price: float = Query(0.0),
    lowest_price: float = Query(0.0),
):
    result = evaluate_swing(
        ticker=ticker,
        entry_price=entry_price,
        current_price=current_price,
        highest_price=highest_price,
        lowest_price=lowest_price,
    )
    return result
