import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.breakout.service import full_breakout_scan
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_breakouts(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        signals = full_breakout_scan(df)
        for s in signals:
            s["ticker"] = ticker
        _save_breakouts(ticker, signals)

        logger.info("Breakouts for %s: %d signals", ticker, len(signals))
        return {
            "ticker": ticker, "status": "success",
            "signals_count": len(signals), "signals": signals,
        }
    except Exception as e:
        logger.exception("Failed to compute breakouts for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


def _save_breakouts(ticker: str, signals: list) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "breakouts")
    os.makedirs(signals_dir, exist_ok=True)
    for s in signals:
        s["date"] = date_str
    path = os.path.join(signals_dir, f"{ticker.lower()}_{date_str}.parquet")
    pd.DataFrame(signals).to_parquet(path, index=False)
    return path
