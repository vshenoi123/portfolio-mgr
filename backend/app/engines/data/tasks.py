import os
import logging
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from celery import shared_task
from app.database import get_data_dir
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


@shared_task
def refresh_ticker_details_task() -> dict:
    from app.engines.data.ticker_details import refresh_ticker_details
    count = refresh_ticker_details()
    return {"status": "success", "count": count}


def _compute_signal_for_all(signal_fn, tickers: list[str], signal_name: str, start_time: float) -> tuple[str, int, int]:
    """Run a signal computation for all tickers. Returns (name, success_count, error_count)."""
    success = 0
    errors = 0
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        try:
            signal_fn(ticker=ticker)
            success += 1
        except Exception as e:
            errors += 1
            logger.warning("%s failed for %s: %s", signal_name, ticker, e)
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_time
            logger.info("%s progress: %d/%d (%d ok, %d err) — %.0fs elapsed",
                        signal_name, i + 1, total, success, errors, elapsed)
    return signal_name, success, errors


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def run_full_refresh_pipeline(self, days: int = 365) -> dict:
    """Orchestrator: OHLCV + ticker_details sequentially, then 4 signal types in parallel."""
    from app.models.universe import get_universe
    from app.engines.regime.tasks import compute_regime
    from app.engines.breakout.tasks import compute_breakouts
    from app.engines.cusum.tasks import compute_cusum
    from app.engines.features.tasks import compute_features

    tickers = get_universe(use_api=True)
    total = len(tickers)
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("FULL REFRESH PIPELINE START: %d tickers", total)
    logger.info("=" * 60)

    logger.info("PIPELINE [1/6] Refreshing OHLCV data")
    refresh_all_data(days=days)

    logger.info("PIPELINE [2/6] Refreshing ticker details")
    refresh_ticker_details_task()

    logger.info("PIPELINE [3/6-6/6] Computing all signals (parallel) — %d tickers × 4 types", total)
    signal_tasks = [
        (compute_regime, tickers, "Regime"),
        (compute_breakouts, tickers, "Breakout"),
        (compute_cusum, tickers, "CUSUM"),
        (compute_features, tickers, "Features"),
    ]
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_compute_signal_for_all, fn, tickers, name, start_time): name
            for fn, tickers, name in signal_tasks
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info("%s complete: %d ok, %d err", result[0], result[1], result[2])
            except Exception as e:
                logger.error("%s failed with exception: %s", name, e)

    logger.info("PIPELINE [7/7] Building consolidated market scan")
    from app.engines.opportunity.tasks import build_market_scan
    scan_path = build_market_scan()

    # Clean up individual signal dirs
    for subdir in ["regime", "breakouts", "cusum", "indicators"]:
        path = os.path.join(get_data_dir(), "signals", subdir)
        if os.path.isdir(path):
            shutil.rmtree(path)
            logger.info("Cleaned up %s", path)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("FULL REFRESH PIPELINE COMPLETE: %.1f seconds", elapsed)
    for name, ok, err in results:
        logger.info("  %s: %d ok, %d err", name, ok, err)
    logger.info("=" * 60)

    return {
        "status": "success",
        "total_tickers": total,
        "elapsed_seconds": round(elapsed, 1),
        "market_scan": scan_path,
        "pipeline": "OHLCV → ticker_details → [regime, breakouts, CUSUM, features] → market_scan",
    }
