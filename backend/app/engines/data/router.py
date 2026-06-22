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
def get_universe(use_api: bool = False):
    from app.models.universe import get_universe
    tickers = get_universe(use_api=use_api)
    return {"tickers": tickers, "count": len(tickers), "source": "polygon_api" if use_api else "default"}


@router.get("/universe/default")
def get_default_universe():
    from app.models.universe import DEFAULT_UNIVERSE
    return {"tickers": DEFAULT_UNIVERSE, "count": len(DEFAULT_UNIVERSE)}


@router.get("/universe/polygon")
def get_polygon_universe(tickers_per_type: int = 100, min_market_cap: float = 1e9):
    from app.models.universe import fetch_universe_from_polygon
    tickers = fetch_universe_from_polygon(
        tickers_per_type=tickers_per_type,
        min_market_cap=min_market_cap,
    )
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
    task = refresh_ticker_data.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/refresh-all", status_code=202)
def refresh_all(_=Depends(verify_api_key)):
    from app.engines.data.tasks import refresh_all_data
    task = refresh_all_data.delay()
    return {"task_id": task.id, "status": "queued", "message": "Refreshing all tickers"}


@router.get("/health")
def data_health():
    from app.models.universe import DEFAULT_UNIVERSE
    return DataHealthResponse(
        tickers_in_universe=len(DEFAULT_UNIVERSE),
        total_ohlcv_bars=0,
        last_refresh=None,
        status="healthy",
    )