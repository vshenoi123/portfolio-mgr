import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.cusum.service import cusum_detect
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_cusum(self, ticker: str, lookback_days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=lookback_days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        returns = df["close"].pct_change().dropna()
        result = cusum_detect(returns)
        _save_cusum(ticker, result)

        logger.info("CUSUM for %s: detected=%s direction=%s", ticker, result["detected"], result["direction"])
        return {"ticker": ticker, "status": "success", **result}
    except Exception as e:
        logger.exception("Failed to compute CUSUM for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_cusum(lookback_days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_cusum.delay(ticker, lookback_days=lookback_days)
        results.append(result)
    return results


def _save_cusum(ticker: str, result: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "cusum")
    os.makedirs(signals_dir, exist_ok=True)
    row = {"ticker": ticker, "date": date_str, **result}
    path = os.path.join(signals_dir, f"{ticker.lower()}_{date_str}.parquet")
    pd.DataFrame([row]).to_parquet(path, index=False)
    return path
