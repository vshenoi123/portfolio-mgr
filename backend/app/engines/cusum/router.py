import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.cusum.tasks import compute_cusum as compute_cusum_task
from app.engines.data.service import PolygonDataService
from app.engines.cusum.service import cusum_detect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/cusum/{ticker}")
def get_cusum(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        from app.engines.cusum.schemas import CUSUMResponse
        return CUSUMResponse(ticker=ticker.upper(), analyzed_bars=0)
    returns = df["close"].pct_change().dropna()
    result = cusum_detect(returns)
    from app.engines.cusum.schemas import ChangePointResult
    return CUSUMResponse(
        ticker=ticker.upper(),
        cusum_result=ChangePointResult(**result),
        analyzed_bars=len(returns),
    )


@router.post("/cusum/compute/{ticker}", status_code=202)
def compute_cusum_endpoint(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_cusum_task.delay(ticker, lookback_days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}
