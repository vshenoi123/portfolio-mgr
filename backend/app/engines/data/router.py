import logging
from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.data.schemas import DataHealthResponse
from app.engines.data.service import PolygonDataService
from app.engines.data.tasks import refresh_ticker_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data"])


@router.get("/universe")
def get_universe():
    from app.models.universe import get_universe as _get_universe
    tickers = _get_universe()
    return {"tickers": tickers, "count": len(tickers)}


@router.get("/universe/polygon")
def get_polygon_universe():
    from app.models.universe import fetch_universe_from_polygon
    tickers = fetch_universe_from_polygon()
    return {"tickers": tickers, "count": len(tickers)}


@router.get("/ohlcv/{ticker}")
def get_ohlcv(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return {"ticker": ticker.upper(), "days": days, "bars": []}
    bars = df.to_dict(orient="records")
    for b in bars:
        if isinstance(b["timestamp"], datetime):
            b["timestamp"] = b["timestamp"].isoformat()
    return {"ticker": ticker.upper(), "days": days, "bars": bars}


@router.post("/refresh/{ticker}", status_code=202)
def refresh_ticker(
    ticker: str,
    days: int = 365,
    _=Depends(verify_api_key),
):
    from app.core.celery_helpers import dispatch_task
    logger.info("Refreshing ticker: %s (days=%d)", ticker.upper(), days)
    result = dispatch_task(refresh_ticker_data, ticker, days=days)
    result["ticker"] = ticker.upper()
    return result


@router.post("/refresh-all", status_code=202)
def refresh_all(_=Depends(verify_api_key)):
    from app.engines.data.tasks import run_full_refresh_pipeline
    from app.core.celery_helpers import dispatch_task
    from app.models.universe import get_universe
    tickers = get_universe()
    logger.info("Running full refresh pipeline for %d tickers (live from Polygon)", len(tickers))
    result = dispatch_task(run_full_refresh_pipeline)
    result["message"] = "Full refresh pipeline started: OHLCV → ticker_details → regime → breakouts → CUSUM → features"
    result["tickers"] = tickers
    return result


@router.get("/health")
def data_health():
    from app.models.universe import get_universe
    return DataHealthResponse(
        tickers_in_universe=len(get_universe()),
        total_ohlcv_bars=0,
        last_refresh=None,
        status="healthy",
    )


@router.get("/refresh/status")
def refresh_status():
    from app.core.celery_helpers import dispatch_task
    from celery.app.control import Inspect
    from app.celery_app import celery_app
    i = celery_app.control.inspect(timeout=1.0)
    active = i.active() or {}
    return {"active_tasks": active}


@router.get("/ticker-details")
def get_ticker_details_endpoint(tickers: str = ""):
    from app.engines.data.ticker_details import get_ticker_details
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else None
    details = get_ticker_details(ticker_list)
    return {"details": details, "count": len(details)}


@router.post("/ticker-details/refresh", status_code=202)
def refresh_ticker_details_endpoint(_=Depends(verify_api_key)):
    from app.engines.data.ticker_details import refresh_ticker_details
    count = refresh_ticker_details()
    return {"status": "success", "count": count}
