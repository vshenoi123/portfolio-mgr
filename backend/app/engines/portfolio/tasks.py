import logging
import duckdb
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_portfolio_snapshot(self, max_drawdown: float = 0.0) -> dict:
    try:
        from app.engines.risk.service import assess_portfolio_risk
        risk = assess_portfolio_risk(settings.database_path, max_drawdown=max_drawdown)
        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(settings.database_path)
        conn = duckdb.connect(settings.database_path)
        try:
            conn.execute("""
                INSERT INTO portfolio_snapshots (date, total_value, cash, equity_value,
                    options_value, total_exposure, max_drawdown, portfolio_beta,
                    portfolio_delta_e, concentration_pct_top5, portfolio_health_score)
                VALUES (CURRENT_DATE, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.total_value, state.cash, state.equity_value,
                state.options_value, state.equity_value + state.options_value,
                max_drawdown, state.portfolio_beta, state.portfolio_delta_e,
                risk.concentration_pct, risk.portfolio_health_score,
            ))
        finally:
            conn.close()
        return {"status": "success", "health_score": risk.portfolio_health_score,
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Portfolio snapshot failed")
        return {"status": "error", "message": str(e)}
