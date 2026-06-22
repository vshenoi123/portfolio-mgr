import logging
import os
import traceback
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.database import get_data_dir
from app.engines.opportunity.schemas import OpportunityResponse, OpportunityScore
from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities, filter_by_strategy
from app.engines.opportunity.tasks import compute_opportunities as compute_opp_task, _load_todays_signals

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


def _get_ticker_types() -> dict[str, str]:
    """Load ticker type mapping (stock/etf) from cached ticker_details."""
    path = os.path.join(get_data_dir(), "cache", "ticker_details.parquet")
    if not os.path.exists(path):
        return {}
    try:
        df = pd.read_parquet(path)
        return {row["ticker"]: row.get("type", "stock") for _, row in df.iterrows()}
    except Exception:
        return {}


def _split_by_asset(scores: list[OpportunityScore], ticker_types: dict[str, str]) -> tuple[list[OpportunityScore], list[OpportunityScore]]:
    stocks, etfs = [], []
    for s in scores:
        ttype = ticker_types.get(s.ticker, "stock")
        if ttype == "etf":
            etfs.append(s)
        else:
            stocks.append(s)
    return stocks, etfs


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

    ticker_types = _get_ticker_types()
    stocks, etfs = _split_by_asset(scores, ticker_types)

    if asset_type == "stocks":
        scores = stocks[:top_n]
    elif asset_type == "etfs":
        scores = etfs[:top_n]
    else:
        scores = _interleave(stocks, etfs, top_n)

    tickers_returned = [s.ticker for s in scores]
    logger.info("Returning %d opportunities (stocks=%d etfs=%d scores=%.1f-%.1f). Top: %s",
                len(scores), len([s for s in scores if ticker_types.get(s.ticker, "stock") != "etf"]),
                len([s for s in scores if ticker_types.get(s.ticker, "stock") == "etf"]),
                scores[-1].total_score if scores else 0,
                scores[0].total_score if scores else 0,
                tickers_returned[:10] if tickers_returned else [])
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


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

    ticker_types = _get_ticker_types()
    stocks, etfs = _split_by_asset(scores, ticker_types)

    if asset_type == "stocks":
        scores = stocks[:top_n]
    elif asset_type == "etfs":
        scores = etfs[:top_n]
    else:
        scores = _interleave(stocks, etfs, top_n)

    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.post("/compute", status_code=202)
def compute_opportunities_endpoint(_=Depends(verify_api_key)):
    from app.core.celery_helpers import dispatch_task
    logger.info("Computing opportunities for all tickers")
    return dispatch_task(compute_opp_task)
