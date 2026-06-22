import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.opportunity.schemas import OpportunityResponse
from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities, filter_by_strategy
from app.engines.opportunity.tasks import compute_opportunities as compute_opp_task, _load_todays_signals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.get("")
def get_opportunities(strategy_type: str = "all", top_n: int = 20, min_score: float = 0.0):
    logger.info("Fetching opportunities: strategy=%s top_n=%d min_score=%.1f", strategy_type, top_n, min_score)
    signals = _load_todays_signals()
    logger.info("Loaded %d signals for scoring", len(signals))
    scores = build_opportunity_scores(signals)
    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n, min_score=min_score)
    logger.info("Returning %d opportunities (from %d analyzed)", len(scores), len(signals))
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.get("/{strategy_type}")
def get_opportunities_by_strategy(strategy_type: str, top_n: int = 20):
    signals = _load_todays_signals()
    scores = build_opportunity_scores(signals)
    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n)
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.post("/compute", status_code=202)
def compute_opportunities_endpoint(_=Depends(verify_api_key)):
    from app.core.celery_helpers import dispatch_task
    logger.info("Computing opportunities for all tickers")
    return dispatch_task(compute_opp_task)
