import logging
from celery import shared_task
from app.engines.positions.service import run_watchdog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_position_watchdog(self) -> dict:
    try:
        positions = _load_positions()
        result = run_watchdog(positions)
        return {
            "positions_evaluated": result.positions_evaluated,
            "actions_taken": len(result.actions_taken),
            "summary": result.summary,
            "status": "success",
        }
    except Exception as e:
        logger.exception("Watchdog run failed")
        return {"status": "error", "message": str(e)}


def _load_positions() -> list[dict]:
    return []
