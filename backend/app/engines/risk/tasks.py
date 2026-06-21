import logging
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def assess_risk_and_alert(self) -> dict:
    try:
        from app.engines.risk.service import assess_portfolio_risk
        assessment = assess_portfolio_risk(settings.database_path)
        alerts = []
        if not assessment.is_safe:
            for v in assessment.violations:
                alerts.append(f"Violation: {v.get('type', 'unknown')} = {v.get('value', 0):.1f}")
            if assessment.portfolio_health_score < 50:
                alerts.append("CRITICAL: Portfolio health below 50")
        return {"status": "success", "is_safe": assessment.is_safe,
                "health_score": assessment.portfolio_health_score,
                "violations_count": len(assessment.violations),
                "alerts": alerts,
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Risk assessment failed")
        return {"status": "error", "message": str(e)}
