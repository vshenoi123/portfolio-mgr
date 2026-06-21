import logging
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings
from app.database import get_connection, close_connection

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def collect_monitoring_data(self) -> dict:
    try:
        from app.engines.monitoring.service import collect_monitoring_summary
        summary = collect_monitoring_summary(settings.database_path)

        conn = get_connection(settings.database_path)
        try:
            conn.execute(
                "INSERT INTO portfolio_snapshots (date, total_value, cash, equity_value, "
                "options_value, portfolio_beta, portfolio_delta_e, portfolio_health_score, "
                "created_at) VALUES (CURRENT_DATE, ?, ?, ?, ?, ?, ?, ?, NOW())",
                [
                    summary.portfolio.total_value if summary.portfolio else 0,
                    summary.portfolio.cash if summary.portfolio else 0,
                    summary.portfolio.equity_value if summary.portfolio else 0,
                    summary.portfolio.options_value if summary.portfolio else 0,
                    summary.portfolio.portfolio_beta if summary.portfolio else 0,
                    summary.portfolio.portfolio_delta_e if summary.portfolio else 0,
                    summary.health.score if summary.health else 100,
                ],
            )
        finally:
            close_connection(settings.database_path)

        return {
            "status": "success",
            "health_score": summary.health.score if summary.health else None,
            "num_positions": len(summary.positions),
            "num_alerts": len(summary.alerts),
            "num_open_orders": len(summary.open_orders),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.exception("Monitoring data collection failed")
        return {"status": "error", "message": str(e)}
