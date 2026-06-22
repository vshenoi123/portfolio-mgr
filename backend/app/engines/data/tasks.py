import logging
from celery import shared_task
from app.engines.data.service import PolygonDataService, PolygonAPIError

logger = logging.getLogger(__name__)


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


@shared_task
def refresh_all_data(days: int = 365) -> list[dict]:
    from app.models.universe import get_universe
    tickers = get_universe(use_api=True)
    logger.info("Starting refresh for ALL %d tickers: %s", len(tickers), tickers[:10])
    results = []
    for i, ticker in enumerate(tickers):
        logger.info("Dispatching refresh %d/%d: %s", i + 1, len(tickers), ticker)
        result = refresh_ticker_data.delay(ticker, days=days)
        results.append(result)
    logger.info("All %d ticker refresh tasks dispatched", len(tickers))
    return results
