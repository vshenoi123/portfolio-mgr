import logging
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_daily_allocation(self, regime: str = "Range") -> dict:
    try:
        from app.engines.portfolio.service import load_portfolio_state
        from app.engines.allocation.service import get_strategy_allocation, calculate_position_size
        state = load_portfolio_state(settings.database_path)
        allocs = get_strategy_allocation(regime)
        results = []
        for alloc in allocs:
            result = calculate_position_size(
                total_portfolio_value=state.total_value,
                cash_available=state.cash,
                kelly_fraction_value=settings.kelly_fraction,
                opportunity_score=50.0, strategy=alloc.strategy, regime=regime,
            )
            results.append(result.model_dump())
        return {"status": "success", "regime": regime,
                "allocations": results,
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Daily allocation failed")
        return {"status": "error", "message": str(e)}
