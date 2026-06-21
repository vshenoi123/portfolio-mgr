import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.breakout.tasks import compute_breakouts as compute_breakouts_task
from app.engines.data.service import PolygonDataService
from app.engines.breakout.service import full_breakout_scan
from app.engines.breakout.schemas import BreakoutResponse, BreakoutSignal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/breakouts/{ticker}")
def get_breakouts(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return BreakoutResponse(ticker=ticker.upper())
    signals_data = full_breakout_scan(df)
    signals = [BreakoutSignal(ticker=ticker.upper(), **s) for s in signals_data]
    strengths = [s.strength for s in signals] if signals else [0.0]
    return BreakoutResponse(
        ticker=ticker.upper(),
        signals=signals,
        total_signals=len(signals),
        max_strength=max(strengths),
    )


@router.post("/breakouts/compute/{ticker}", status_code=202)
def compute_breakouts_endpoint(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_breakouts_task.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}
