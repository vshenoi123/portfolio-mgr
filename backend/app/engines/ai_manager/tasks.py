import logging
from celery import shared_task
from app.engines.ai_manager.service import ReportService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_daily_report_task(self):
    try:
        service = ReportService()
        result = service.generate_daily_report()
        logger.info("Daily report generated: %s sections", len(result.sections))
        return {"status": "success", "sections": len(result.sections)}
    except Exception as e:
        logger.error("Failed to generate daily report: %s", e)
        raise self.retry(exc=e)
