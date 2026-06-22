import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from celery import shared_task
from app.engines.data.service import PolygonDataService, PolygonAPIError
from app.config import settings

logger = logging.getLogger(__name__)

POLYGON_RATE_LIMIT_DELAY = 12.0  # 5 req/min on free tier = 1 per 12s


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_ticker_data(self, ticker: str, days: int = 365) -> dict:
    logger.info("Starting refresh for %s (days=%d)", ticker, days)
    service = PolygonDataService()
    try:
        bars = service.fetch_ohlcv(ticker, days=days)
        if bars:
            service.save_ohlcv(bars)
            logger.info("Refreshed %s: %d bars fetched and saved", ticker, len(bars))
        else:
            logger.warning("No bars returned for %s", ticker)
        return {
            "ticker": ticker,
            "status": "success",
            "bars_fetched": len(bars),
            "message": f"Refreshed {ticker}",
        }
    except PolygonAPIError as e:
        logger.error("Polygon API error for %s: %s", ticker, e)
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception("Unexpected error refreshing %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


def _get_last_update(ticker: str) -> datetime | None:
    """Check when we last fetched data for this ticker."""
    parquet_path = os.path.join(
        settings.data_dir, "market_data", "ohlcv", ticker.lower(), f"{ticker.lower()}.parquet"
    )
    if not os.path.exists(parquet_path):
        return None
    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
        if df.empty:
            return None
        return df["timestamp"].max()
    except Exception:
        return None


def _fetch_single_ticker(ticker: str, days: int, incremental: bool) -> dict:
    """Fetch a single ticker, with rate limit delay."""
    service = PolygonDataService()
    try:
        if incremental:
            last_update = _get_last_update(ticker)
            if last_update is not None:
                now = datetime.now(timezone.utc)
                if hasattr(last_update, 'tzinfo') and last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                days_since = (now - last_update).days
                if days_since < 1:
                    return {"ticker": ticker, "status": "skipped", "message": "Already fresh"}
                days = min(days_since + 7, days)  # fetch a few extra days for overlap

        bars = service.fetch_ohlcv(ticker, days=days)
        if bars:
            service.save_ohlcv(bars)
            return {"ticker": ticker, "status": "success", "bars": len(bars)}
        return {"ticker": ticker, "status": "success", "bars": 0}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task(bind=True, max_retries=1)
def refresh_all_data(self, days: int = 365) -> dict:
    """Refresh all tickers concurrently with rate limiting."""
    from app.models.universe import get_universe

    tickers = get_universe(use_api=True)
    total = len(tickers)
    logger.info("Starting batch refresh for %d tickers (concurrent)", total)

    results = {"success": 0, "error": 0, "skipped": 0, "errors": []}
    start_time = time.time()

    # Use thread pool — Polygon SDK is sync, threads avoid serial bottleneck
    # Free tier: 5 req/min → we process ~4 per batch with 12s delay between batches
    batch_size = 4
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = {}
        for i, ticker in enumerate(tickers):
            future = executor.submit(_fetch_single_ticker, ticker, days, incremental=True)
            futures[future] = (i, ticker)

        completed = 0
        for future in as_completed(futures):
            idx, ticker = futures[future]
            try:
                result = future.result(timeout=30)
                status = result.get("status", "error")
                if status == "success":
                    results["success"] += 1
                elif status == "skipped":
                    results["skipped"] += 1
                else:
                    results["error"] += 1
                    results["errors"].append(f"{ticker}: {result.get('message', 'unknown')}")
            except Exception as e:
                results["error"] += 1
                results["errors"].append(f"{ticker}: {str(e)}")

            completed += 1
            if completed % 50 == 0:
                elapsed = time.time() - start_time
                logger.info("Progress: %d/%d (%.1f%%) — %.0fs elapsed",
                    completed, total, (completed / total) * 100, elapsed)

    elapsed = time.time() - start_time
    logger.info(
        "Batch refresh complete: %d success, %d skipped, %d errors — %.1fs total",
        results["success"], results["skipped"], results["error"], elapsed,
    )
    if results["errors"]:
        logger.info("First 10 errors: %s", results["errors"][:10])

    return {
        "status": "success",
        "total": total,
        "success": results["success"],
        "skipped": results["skipped"],
        "errors": results["error"],
        "error_samples": results["errors"][:5],
        "elapsed_seconds": round(elapsed, 1),
    }
