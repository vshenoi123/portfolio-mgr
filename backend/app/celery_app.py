import os
import logging
from celery import Celery
from app.config import settings

logger = logging.getLogger(__name__)

redis_url = settings.redis_url
env_url = os.environ.get("REDIS_URL", "NOT SET")
logger.critical("CELERY DEBUG: settings.redis_url=%s, env REDIS_URL=%s", redis_url, env_url)

if not redis_url or "localhost" in redis_url:
    redis_url = env_url if env_url != "NOT SET" else "redis://redis:6379/0"
    logger.critical("CELERY DEBUG: fell back to %s", redis_url)

celery_app = Celery("portfolio_mgr", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_connection_retry_delay=1.0,
    beat_schedule={
        # Phase 1
        "refresh-all-data-daily": {
            "task": "app.engines.data.tasks.refresh_all_data",
            "schedule": 86400.0,
        },
        # Phase 2
        "compute-all-features-daily": {
            "task": "app.engines.features.tasks.compute_all_features",
            "schedule": 86400.0,
        },
        "compute-regime-daily": {
            "task": "app.engines.regime.tasks.compute_regime",
            "schedule": 86400.0,
            "kwargs": {"ticker": "SPY", "n_states": 4},
        },
        "compute-all-cusum-daily": {
            "task": "app.engines.cusum.tasks.compute_all_cusum",
            "schedule": 86400.0,
        },
        "compute-all-breakouts-daily": {
            "task": "app.engines.breakout.tasks.compute_all_breakouts",
            "schedule": 86400.0,
        },
        # Phase 3
        "compute-opportunities-daily": {
            "task": "app.engines.opportunity.tasks.compute_opportunities",
            "schedule": 86400.0,
        },
        "compute-all-strategies-daily": {
            "task": "app.engines.strategy.tasks.compute_all_strategies",
            "schedule": 86400.0,
        },
        # Phase 4
        "compute-portfolio-snapshot-daily": {
            "task": "app.engines.portfolio.tasks.compute_portfolio_snapshot",
            "schedule": 86400.0,
        },
        "run-daily-allocation": {
            "task": "app.engines.allocation.tasks.run_daily_allocation",
            "schedule": 86400.0,
        },
        "evaluate-opportunity-cost-daily": {
            "task": "app.engines.cost.tasks.evaluate_opportunity_cost",
            "schedule": 86400.0,
        },
        "evaluate-replacements-daily": {
            "task": "app.engines.replacement.tasks.evaluate_replacements",
            "schedule": 86400.0,
        },
        "assess-risk-daily": {
            "task": "app.engines.risk.tasks.assess_risk_and_alert",
            "schedule": 86400.0,
        },
        # Phase 5
        "sync-positions-5min": {
            "task": "app.engines.trading.tasks.sync_positions",
            "schedule": 300.0,
        },
        "run-position-watchdog-hourly": {
            "task": "app.engines.positions.tasks.run_position_watchdog",
            "schedule": 3600.0,
        },
        "collect-monitoring-data-5min": {
            "task": "app.engines.monitoring.tasks.collect_monitoring_data",
            "schedule": 300.0,
        },
        # Phase 6
        "generate-daily-report": {
            "task": "app.engines.ai_manager.tasks.generate_daily_report_task",
            "schedule": 86400.0,
        },
        "compute-signal-efficacy-daily": {
            "task": "app.engines.self_learning.tasks.compute_signal_efficacy_task",
            "schedule": 86400.0,
        },
        # Phase 7
        "run-daily-monte-carlo": {
            "task": "app.engines.monte_carlo.tasks.run_daily_monte_carlo",
            "schedule": 86400.0,
            "kwargs": {"ticker": "SPY"},
        },
        "run-weekly-stress-test": {
            "task": "app.engines.stress_test.tasks.run_weekly_stress_test",
            "schedule": 604800.0,
        },
    },
)
