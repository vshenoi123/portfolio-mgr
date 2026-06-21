import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.regime.schemas import RegimeRequest
from app.engines.regime.tasks import compute_regime as compute_regime_task
from app.engines.data.service import PolygonDataService
from app.engines.regime.service import full_regime_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/regime")
def get_global_regime(lookback_days: int = 756):
    service = PolygonDataService()
    df = service.load_ohlcv("SPY", days=lookback_days)
    if df.empty:
        return {"ticker": "SPY", "overall_regime": None, "state_probabilities": {}, "trained_on_bars": 0}
    returns = df["close"].pct_change().dropna()
    analysis = full_regime_analysis(returns)
    return {"ticker": "SPY", **analysis}


@router.get("/regime/{ticker}")
def get_regime_for_ticker(ticker: str, lookback_days: int = 756):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=lookback_days)
    if df.empty:
        return {"ticker": ticker.upper(), "overall_regime": None, "state_probabilities": {}, "trained_on_bars": 0}
    returns = df["close"].pct_change().dropna()
    analysis = full_regime_analysis(returns)
    return {"ticker": ticker.upper(), **analysis}


@router.post("/regime/compute", status_code=202)
def compute_regime_endpoint(req: RegimeRequest, _=Depends(verify_api_key)):
    task = compute_regime_task.delay(ticker=req.ticker, n_states=req.n_states, lookback_days=req.lookback_days)
    return {"task_id": task.id, "ticker": req.ticker, "status": "queued"}


@router.post("/regime/compute-all", status_code=202)
def compute_all_regimes_endpoint(n_states: int = 4, _=Depends(verify_api_key)):
    from app.engines.regime.tasks import compute_all_regimes
    task = compute_all_regimes.delay(n_states=n_states)
    return {"task_id": task.id, "status": "queued", "message": "Computing regimes for all tickers"}
