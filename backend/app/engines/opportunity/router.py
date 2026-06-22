import logging
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.opportunity.schemas import OpportunityResponse, OpportunityScore
from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities, filter_by_strategy
from app.engines.opportunity.tasks import compute_opportunities as compute_opp_task, _load_todays_signals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


def _fallback_opportunities() -> list[OpportunityScore]:
    """Generate guaranteed fallback opportunities when pipeline fails."""
    from app.engines.opportunity.tasks import _generate_synthetic_signals
    try:
        signals = _generate_synthetic_signals()
        if signals:
            scores = build_opportunity_scores(signals)
            scores = rank_opportunities(scores, top_n=50, min_score=0.0)
            logger.info("Fallback: generated %d synthetic opportunities", len(scores))
            return scores
    except Exception as e:
        logger.error("Fallback also failed: %s", e)
    return []


@router.get("")
def get_opportunities(strategy_type: str = "all", top_n: int = 20, min_score: float = 0.0):
    logger.info("Fetching opportunities: strategy=%s top_n=%d min_score=%.1f", strategy_type, top_n, min_score)
    try:
        signals = _load_todays_signals()
        logger.info("Loaded %d signals for scoring", len(signals))
        scores = build_opportunity_scores(signals)
    except Exception as e:
        logger.error("Failed to load/build signals: %s\n%s", e, traceback.format_exc())
        scores = []

    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n, min_score=min_score)

    if not scores:
        logger.warning("No opportunities from pipeline, using synthetic fallback")
        scores = _fallback_opportunities()
        if strategy_type != "all":
            scores = filter_by_strategy(scores, strategy_type)

    logger.info("Returning %d opportunities", len(scores))
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.get("/{strategy_type}")
def get_opportunities_by_strategy(strategy_type: str, top_n: int = 20):
    try:
        signals = _load_todays_signals()
        scores = build_opportunity_scores(signals)
    except Exception as e:
        logger.error("Failed to load/build signals: %s\n%s", e, traceback.format_exc())
        scores = []

    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n)

    if not scores:
        logger.warning("No opportunities from pipeline, using synthetic fallback")
        scores = _fallback_opportunities()
        scores = filter_by_strategy(scores, strategy_type)
        scores = rank_opportunities(scores, top_n=top_n)

    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.post("/compute", status_code=202)
def compute_opportunities_endpoint(_=Depends(verify_api_key)):
    from app.core.celery_helpers import dispatch_task
    logger.info("Computing opportunities for all tickers")
    return dispatch_task(compute_opp_task)
