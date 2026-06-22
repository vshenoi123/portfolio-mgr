import logging
from celery import shared_task
from app.engines.ai_manager.service import ReportService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_daily_report_task(self):
    try:
        logger.info("Starting daily report generation")
        service = ReportService()
        result = service.generate_daily_report()
        logger.info("Daily report generated: %d sections, summary=%d chars",
            len(result.sections), len(result.summary))
        for s in result.sections:
            logger.info("  Section: %s (priority=%s)", s.title, s.priority)
        return {"status": "success", "sections": len(result.sections)}
    except Exception as e:
        logger.error("Failed to generate daily report: %s", e)
        raise self.retry(exc=e)
