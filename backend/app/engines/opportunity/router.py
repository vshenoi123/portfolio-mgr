import logging
import os
import traceback
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.opportunity.schemas import OpportunityResponse, OpportunityScore
from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities, filter_by_strategy
from app.engines.opportunity.tasks import compute_opportunities as compute_opp_task, _load_todays_signals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


def _interleave(stocks: list, etfs: list, top_n: int) -> list:
    half = max(1, top_n // 2)
    stocks = stocks[:half]
    etfs = etfs[:half]
    result = []
    for i in range(max(len(stocks), len(etfs))):
        if i < len(stocks):
            result.append(stocks[i])
        if i < len(etfs):
            result.append(etfs[i])
    return result


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


def _fallback_opportunities() -> list[OpportunityScore]:
    """Generate guaranteed fallback opportunities when pipeline fails."""
    from app.engines.opportunity.tasks import _generate_synthetic_signals
    try:
        signals = _generate_synthetic_signals()
        if signals:
            scores = build_opportunity_scores(signals)
            scores = rank_opportunities(scores, top_n=50, min_score=0.0)
            _enrich_with_prices(scores)
            logger.info("Fallback: generated %d synthetic opportunities", len(scores))
            return scores
    except Exception as e:
        logger.error("Fallback also failed: %s", e)
    return []


def _respond(scores: list[OpportunityScore], asset_type: str, top_n: int) -> OpportunityResponse:
    stocks = [s for s in scores if s.asset_type != "etf"]
    etfs = [s for s in scores if s.asset_type == "etf"]

    if asset_type == "stocks":
        scores = stocks[:top_n]
    elif asset_type == "etfs":
        scores = etfs[:top_n]
    else:
        scores = _interleave(stocks, etfs, top_n)

    return OpportunityResponse(
        date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores,
        total_analyzed=len(scores),
    )


@router.get("")
def get_opportunities(strategy_type: str = "all", top_n: int = 20, min_score: float = 0.0, asset_type: str = "all"):
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
        logger.warning("No opportunities from pipeline, using synthetic fallback")
        scores = _fallback_opportunities()
        if strategy_type != "all":
            scores = filter_by_strategy(scores, strategy_type)

    _enrich_with_prices(scores)

    tickers_returned = [s.ticker for s in scores]
    logger.info("Returning %d opportunities (stocks=%d etfs=%d scores=%.1f-%.1f). Top: %s",
                len(scores), len([s for s in scores if s.asset_type != "etf"]),
                len([s for s in scores if s.asset_type == "etf"]),
                scores[-1].total_score if scores else 0,
                scores[0].total_score if scores else 0,
                tickers_returned[:10] if tickers_returned else [])
    return _respond(scores, asset_type, top_n)


@router.get("/{strategy_type}")
def get_opportunities_by_strategy(strategy_type: str, top_n: int = 20, asset_type: str = "all"):
    try:
        signals = _load_todays_signals()
        scores = build_opportunity_scores(signals)
    except Exception as e:
        logger.error("Failed to load/build signals: %s\n%s", e, traceback.format_exc())
        scores = []

    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=None)

    if not scores:
        logger.warning("No opportunities from pipeline, using synthetic fallback")
        scores = _fallback_opportunities()
        scores = filter_by_strategy(scores, strategy_type)

    _enrich_with_prices(scores)

    return _respond(scores, asset_type, top_n)


@router.post("/compute", status_code=202)
def compute_opportunities_endpoint(_=Depends(verify_api_key)):
    from app.core.celery_helpers import dispatch_task
    logger.info("Computing opportunities for all tickers")
    return dispatch_task(compute_opp_task)
