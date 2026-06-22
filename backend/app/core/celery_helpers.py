import logging
from typing import Any

logger = logging.getLogger(__name__)


def dispatch_task(task_func, *args, **kwargs) -> dict:
    """Dispatch a Celery task with retry on connection failure."""
    try:
        task = task_func.delay(*args, **kwargs)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        logger.error("Failed to dispatch task %s: %s", task_func.name, e)
        return {"task_id": None, "status": "failed", "error": str(e)}
