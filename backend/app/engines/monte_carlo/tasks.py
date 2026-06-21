from celery import shared_task
from app.engines.monte_carlo.service import MonteCarloService
from app.engines.monte_carlo.schemas import MonteCarloRequest
import numpy as np

service = MonteCarloService()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_daily_monte_carlo(self, ticker: str):
    try:
        from app.engines.data.service import PolygonDataService
        from app.config import settings
        data_service = PolygonDataService(data_dir=settings.data_dir)
        ohlcv = data_service.load_ohlcv(ticker, days=756)
        if ohlcv.empty:
            return {"ticker": ticker, "status": "no_data"}
        returns = ohlcv["close"].pct_change().dropna().values.astype(np.float64)
        req = MonteCarloRequest(ticker=ticker)
        result = service.run_simulation(req, returns)
        return {"ticker": ticker, "status": "success", "var_95": result.var_95}
    except Exception as exc:
        raise self.retry(exc=exc)