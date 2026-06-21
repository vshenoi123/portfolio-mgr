from fastapi import APIRouter, HTTPException
import numpy as np
from app.engines.monte_carlo.schemas import MonteCarloRequest, PortfolioMonteCarloRequest
from app.engines.monte_carlo.service import MonteCarloService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])
service = MonteCarloService()


@router.post("/monte-carlo/{ticker}")
async def run_monte_carlo(ticker: str, req: MonteCarloRequest | None = None):
    if req is None:
        req = MonteCarloRequest(ticker=ticker)
    req.ticker = ticker.upper()

    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
        ohlcv = data_service.load_ohlcv(ticker, days=756)
        if ohlcv.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        returns = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
        if len(returns) < 20:
            raise HTTPException(status_code=400, detail=f"Not enough data for {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = service.run_simulation(req, returns)
    return result.model_dump()


@router.post("/monte-carlo/portfolio")
async def run_portfolio_monte_carlo(req: PortfolioMonteCarloRequest):
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)

        returns_dict = {}
        for pos in req.positions:
            ticker = pos["ticker"]
            ohlcv = data_service.load_ohlcv(ticker, days=756)
            if ohlcv.empty:
                raise HTTPException(status_code=404, detail=f"No data for {ticker}")
            ret = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
            if len(ret) < 20:
                raise HTTPException(status_code=400, detail=f"Not enough data for {ticker}")
            returns_dict[ticker] = ret
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = service.run_portfolio_simulation(req, returns_dict)

    serializable = {}
    for k, v in result.items():
        if isinstance(v, np.ndarray):
            serializable[k] = v.tolist()
        else:
            serializable[k] = v
    return serializable