import logging
from fastapi import APIRouter

from app.config import settings
from app.engines.monitoring.service import (
    collect_portfolio_snapshot,
    collect_position_snapshots,
    collect_order_snapshots,
    compute_health_score,
    check_alerts,
    collect_monitoring_summary,
)
from app.engines.risk.service import assess_portfolio_risk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/summary")
def get_summary():
    summary = collect_monitoring_summary(settings.database_path)
    return summary.model_dump()


@router.get("/health")
def get_health():
    snapshot = collect_portfolio_snapshot(settings.database_path)
    assessment = assess_portfolio_risk(settings.database_path)
    health = compute_health_score(assessment.model_dump())
    return health.model_dump()


@router.get("/alerts")
def get_alerts():
    snapshot = collect_portfolio_snapshot(settings.database_path)
    assessment = assess_portfolio_risk(settings.database_path)
    health = compute_health_score(assessment.model_dump())
    alerts = check_alerts(snapshot, health)
    return [a.model_dump() for a in alerts]


@router.get("/snapshot")
def get_snapshot():
    snapshot = collect_portfolio_snapshot(settings.database_path)
    return snapshot.model_dump()
