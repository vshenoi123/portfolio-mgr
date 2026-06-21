import logging
from fastapi import APIRouter
from app.engines.strategy.schemas import StrategyResponse
from app.engines.strategy.service import select_strategy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.get("/strategy/{ticker}")
def get_strategy(ticker: str):
    context = {
        "ticker": ticker.upper(),
        "regime": "Range",
        "regime_score": 50.0,
        "momentum": 0.0,
        "trend_strength": 0.5,
        "breakout_score": 50.0,
        "relative_strength_score": 50.0,
        "cusum_score": 50.0,
        "volume_score": 50.0,
        "trend_score": 50.0,
        "iv_percentile": 0.5,
        "put_skew": 0.0,
        "term_structure": 0.0,
        "drawdown": 0.0,
        "days_to_expiry": 0,
        "has_position": False,
        "dte_remaining": 0,
        "rsi": 50.0,
    }
    output = select_strategy(context)
    return StrategyResponse(ticker=output.ticker, recommendation=output.recommendation,
        confidence=output.confidence, reasoning=output.reasoning,
        risk_assessment=output.risk_assessment)
