import logging
from typing import Any

logger = logging.getLogger(__name__)


def dispatch_task(task_func, *args, **kwargs) -> dict:
    """Dispatch a Celery task with retry on connection failure."""
    task_name = task_func.name if hasattr(task_func, 'name') else str(task_func)

    # Log which Celery app will be used
    from celery._state import current_app
    logger.info("Dispatching task: %s | args=%s kwargs=%s | app_id=%s broker=%s",
        task_name, args, kwargs, id(current_app), current_app.conf.broker_url)

    try:
        task = task_func.delay(*args, **kwargs)
        logger.info("Task dispatched successfully: %s | task_id=%s", task_name, task.id)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        logger.error("Failed to dispatch task %s: %s", task_name, e)
        return {"task_id": None, "status": "failed", "error": str(e)}
