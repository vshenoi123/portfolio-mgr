import logging
from celery import shared_task
from app.engines.data.service import PolygonDataService, PolygonAPIError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_ticker_data(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        bars = service.fetch_ohlcv(ticker, days=days)
        if bars:
            service.save_ohlcv(bars)
        logger.info("Refreshed %s: %d bars", ticker, len(bars))
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
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = refresh_ticker_data.delay(ticker, days=days)
        results.append(result)
    return results
