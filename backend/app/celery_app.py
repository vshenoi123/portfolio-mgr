from celery import Celery
from app.config import settings

celery_app = Celery("portfolio_mgr", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
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
    },
)
