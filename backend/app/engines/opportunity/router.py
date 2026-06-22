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


def _enrich_with_prices(scores: list[OpportunityScore]) -> None:
    """Fetch live prices for the given scores and attach last_price in-place."""
    tickers = [s.ticker for s in scores]
    if not tickers:
        return
    try:
        from app.engines.data.ticker_details import get_ticker_details
        details = get_ticker_details(tickers)
        for s in scores:
            info = details.get(s.ticker, {})
            s.last_price = info.get("last_price") or None
    except Exception as e:
        logger.warning("Failed to enrich with live prices: %s", e)


def _respond(scores: list[OpportunityScore], asset_type: str, top_n: int,
             min_market_cap: float = 2_000_000_000) -> OpportunityResponse:
    if asset_type == "etfs":
        scores = [s for s in scores if s.asset_type == "etf"]
    else:
        scores = [s for s in scores if s.asset_type != "etf"]
    if min_market_cap > 0:
        scores = [s for s in scores if not s.market_cap or s.market_cap >= min_market_cap]
    scores = scores[:top_n]
    _enrich_with_prices(scores)

    return OpportunityResponse(
        date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores,
        total_analyzed=len(scores),
    )


@router.get("")
def get_opportunities(strategy_type: str = "all", top_n: int = 20, min_score: float = 10.0,
                      asset_type: str = "stocks", min_market_cap: float = 2_000_000_000):
    logger.info("Fetching opportunities: strategy=%s top_n=%d min_score=%.1f asset=%s",
                strategy_type, top_n, min_score, asset_type)
    try:
        signals = _load_todays_signals()
        logger.info("Loaded %d signals for scoring", len(signals))
        scores = build_opportunity_scores(signals)
    except Exception as e:
        logger.error("Failed to load/build signals: %s\n%s", e, traceback.format_exc())
        scores = []

    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=None, min_score=min_score)

    if not scores:
        logger.info("No opportunities found — pipeline may still be running")

    tickers_returned = [s.ticker for s in scores]
    logger.info("Returning %d opportunities (stocks=%d etfs=%d scores=%.1f-%.1f). Top: %s",
                len(scores), len([s for s in scores if s.asset_type != "etf"]),
                len([s for s in scores if s.asset_type == "etf"]),
                scores[-1].total_score if scores else 0,
                scores[0].total_score if scores else 0,
                tickers_returned[:10] if tickers_returned else [])
    return _respond(scores, asset_type, top_n, min_market_cap)


@router.get("/{strategy_type}")
def get_opportunities_by_strategy(strategy_type: str, top_n: int = 20, asset_type: str = "stocks",
                                  min_score: float = 10.0, min_market_cap: float = 2_000_000_000):
    try:
        signals = _load_todays_signals()
        scores = build_opportunity_scores(signals)
    except Exception as e:
        logger.error("Failed to load/build signals: %s\n%s", e, traceback.format_exc())
        scores = []

    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=None, min_score=min_score)

    if not scores:
        logger.info("No opportunities found — pipeline may still be running")

    return _respond(scores, asset_type, top_n, min_market_cap)


@router.post("/compute", status_code=202)
def compute_opportunities_endpoint(_=Depends(verify_api_key)):
    from app.core.celery_helpers import dispatch_task
    logger.info("Computing opportunities for all tickers")
    return dispatch_task(compute_opp_task)
