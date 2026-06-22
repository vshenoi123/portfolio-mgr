import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

redis_url = os.environ.get("REDIS_URL", "")
if not redis_url:
    redis_url = "redis://redis:6379/0"
    logger.critical("REDIS_URL env var not set, using default: %s", redis_url)
else:
    logger.critical("Celery broker URL from env: %s", redis_url)

celery_app = Celery(
    "portfolio_mgr",
    broker=redis_url,
    backend=redis_url,
    include=[
        "app.engines.ai_manager.tasks",
        "app.engines.allocation.tasks",
        "app.engines.options.tasks",
        "app.engines.self_learning.tasks",
        "app.engines.strategy.tasks",
        "app.engines.opportunity.tasks",
        "app.engines.monte_carlo.tasks",
        "app.engines.regime.tasks",
        "app.engines.features.tasks",
        "app.engines.breakout.tasks",
        "app.engines.risk.tasks",
        "app.engines.cost.tasks",
        "app.engines.cusum.tasks",
        "app.engines.trading.tasks",
        "app.engines.stress_test.tasks",
        "app.engines.replacement.tasks",
        "app.engines.data.tasks",
        "app.engines.portfolio.tasks",
        "app.engines.monitoring.tasks",
        "app.engines.positions.tasks",
    ],
)

# Register as the current app so shared_task.delay() uses this broker
import celery._state as _state
_state._current_app = celery_app
_state._apps.add(celery_app)
logger.critical("Registered celery_app as current app: %s", id(celery_app))
logger.critical("_state._current_app: %s", id(_state._current_app))
logger.critical("_state._current_app broker: %s", _state._current_app.conf.broker_url)

celery_app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    broker_transport="redis",
    broker_transport_options={"visibility_timeout": 3600},
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_connection_retry_delay=1.0,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
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

logger.critical("Celery configured: broker=%s transport=%s", celery_app.conf.broker_url, celery_app.conf.broker_transport)
