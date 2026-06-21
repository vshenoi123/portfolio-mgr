from celery import Celery
from app.config import settings

celery_app = Celery(
    "portfolio_mgr",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-all-data-daily": {
            "task": "app.engines.data.tasks.refresh_all_data",
            "schedule": 86400.0,
        },
    },
)
