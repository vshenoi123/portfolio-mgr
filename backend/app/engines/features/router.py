import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.features.schemas import IndicatorResponse, EngineHealthResponse
from app.engines.features.service import compute_all_indicators
from app.engines.features.tasks import compute_features as compute_features_task
from app.engines.data.service import PolygonDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/indicators/{ticker}")
def get_indicators(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return IndicatorResponse(ticker=ticker.upper(), indicators={}, bars_analyzed=0)
    spy_df = service.load_ohlcv("SPY", days=days)
    spy_close = spy_df["close"] if not spy_df.empty else None
    indicators = compute_all_indicators(df, spy_close=spy_close)
    return IndicatorResponse(
        ticker=ticker.upper(),
        indicators=indicators,
        bars_analyzed=len(df),
    )


@router.post("/indicators/compute/{ticker}", status_code=202)
def compute_indicators(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_features_task.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/indicators/compute-all", status_code=202)
def compute_all_indicators_endpoint(_=Depends(verify_api_key)):
    from app.engines.features.tasks import compute_all_features
    task = compute_all_features.delay()
    return {"task_id": task.id, "status": "queued", "message": "Computing features for all tickers"}


@router.get("/features/health")
def features_health():
    return EngineHealthResponse(engine="features")
