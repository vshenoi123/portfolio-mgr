import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_positions(self) -> dict:
    try:
        logger.info("Starting position sync from Alpaca")
        from app.engines.trading.service import AlpacaClient
        client = AlpacaClient()
        if not client.enabled:
            logger.warning("Alpaca API not configured, skipping sync")
            return {"status": "skipped", "message": "Alpaca API not configured"}
        result = client.sync_positions()
        logger.info("Position sync result: success=%s message=%s", result.success, result.message)
        return {
            "status": "success" if result.success else "error",
            "message": result.message,
        }
    except Exception as e:
        logger.exception("sync_positions task failed")
        return {"status": "error", "message": str(e)}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def place_order_task(self, ticker: str, side: str, order_type: str, quantity: float,
                     price: float | None = None, stop_price: float | None = None,
                     time_in_force: str = "day", strategy_type: str = "equity",
                     notes: str = "") -> dict:
    try:
        from app.engines.trading.schemas import OrderRequest
        from app.engines.trading.service import AlpacaClient

        req = OrderRequest(
            ticker=ticker, side=side, order_type=order_type,
            quantity=quantity, time_in_force=time_in_force,
            price=price, stop_price=stop_price,
            strategy_type=strategy_type, notes=notes,
        )
        client = AlpacaClient()
        result = client.place_order(req)
        return {
            "status": "success" if result.success else "error",
            "message": result.message,
            "order_id": result.order_id,
            "alpaca_order_id": result.alpaca_order_id,
        }
    except Exception as e:
        logger.exception("place_order_task failed")
        return {"status": "error", "message": str(e)}
