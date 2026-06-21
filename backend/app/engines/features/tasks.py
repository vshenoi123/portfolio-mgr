import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.features.service import compute_all_indicators
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_features(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        spy_df = service.load_ohlcv("SPY", days=days)
        spy_close = spy_df["close"] if not spy_df.empty else pd.Series()

        result = compute_all_indicators(df, spy_close=spy_close)
        _save_indicators(ticker, result)

        logger.info("Computed %d features for %s", len(result), ticker)
        return {
            "ticker": ticker,
            "status": "success",
            "indicators_count": len(result),
            "message": f"Computed {len(result)} features for {ticker}",
        }
    except Exception as e:
        logger.exception("Failed to compute features for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_features(days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_features.delay(ticker, days=days)
        results.append(result)
    return results


def _save_indicators(ticker: str, indicators: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "indicators")
    os.makedirs(signals_dir, exist_ok=True)
    path = os.path.join(signals_dir, f"{ticker.lower()}_{date_str}.parquet")
    df = pd.DataFrame([{"ticker": ticker, "date": date_str, **indicators}])
    df.to_parquet(path, index=False)
    return path
