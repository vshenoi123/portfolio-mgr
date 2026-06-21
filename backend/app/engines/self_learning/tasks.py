import logging
from celery import shared_task
from app.engines.self_learning.service import compute_signal_efficacy

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def compute_signal_efficacy_task(self):
    try:
        result = compute_signal_efficacy()
        logger.info(
            "Signal efficacy computed: %d trades, %.1f%% win rate",
            result.total_trades,
            result.win_rate,
        )
        return {"status": "success", "total_trades": result.total_trades, "win_rate": result.win_rate}
    except Exception as e:
        logger.error("Failed to compute signal efficacy: %s", e)
        raise self.retry(exc=e)
