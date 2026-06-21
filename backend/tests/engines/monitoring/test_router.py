import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


def _make_mock_snapshot():
    from app.engines.monitoring.schemas import PortfolioSnapshot
    return PortfolioSnapshot(
        timestamp=datetime.now(timezone.utc),
        total_value=100000.0, cash=25000.0,
        equity_value=70000.0, options_value=5000.0,
        num_positions=2, portfolio_beta=1.2, portfolio_delta_e=500.0,
    )


def _make_mock_health():
    from app.engines.monitoring.schemas import PortfolioHealthScore
    return PortfolioHealthScore(score=85.0)


def _make_mock_assessment():
    from app.engines.risk.schemas import RiskAssessment
    return RiskAssessment(
        portfolio_health_score=85.0,
        max_drawdown=-5.0,
        current_exposure=75000.0,
        total_value=100000.0,
        concentration_pct=21.25,
        violations=[],
        is_safe=True,
        details={"exposure_pct": 75.0, "cash_pct": 25.0},
    )


@pytest_asyncio.fixture
async def client():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMonitoringRouter:
    async def test_get_summary(self, client):
        from app.engines.monitoring.schemas import MonitoringSummary
        mock_summary = MonitoringSummary(
            portfolio=_make_mock_snapshot(),
            health=_make_mock_health(),
            timestamp=datetime.now(timezone.utc),
        )
        with patch(
            "app.engines.monitoring.router.collect_monitoring_summary",
            return_value=mock_summary,
        ):
            resp = await client.get("/api/v1/monitoring/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["health"]["score"] == 85.0

    async def test_get_health(self, client):
        with (
            patch(
                "app.engines.monitoring.router.collect_portfolio_snapshot",
                return_value=_make_mock_snapshot(),
            ),
            patch(
                "app.engines.monitoring.router.assess_portfolio_risk",
                return_value=_make_mock_assessment(),
            ),
            patch(
                "app.engines.monitoring.router.compute_health_score",
                return_value=_make_mock_health(),
            ),
        ):
            resp = await client.get("/api/v1/monitoring/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 85.0
        assert data["level"] == "healthy"

    async def test_get_alerts(self, client):
        from app.engines.monitoring.schemas import AlertEvent
        mock_alerts = [
            AlertEvent(
                alert_type="low_cash", severity="warning",
                message="Cash low", timestamp=datetime.now(timezone.utc),
            ),
        ]
        with (
            patch(
                "app.engines.monitoring.router.collect_portfolio_snapshot",
                return_value=_make_mock_snapshot(),
            ),
            patch(
                "app.engines.monitoring.router.assess_portfolio_risk",
                return_value=_make_mock_assessment(),
            ),
            patch(
                "app.engines.monitoring.router.compute_health_score",
                return_value=_make_mock_health(),
            ),
            patch(
                "app.engines.monitoring.router.check_alerts",
                return_value=mock_alerts,
            ),
        ):
            resp = await client.get("/api/v1/monitoring/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["alert_type"] == "low_cash"

    async def test_get_snapshot(self, client):
        with patch(
            "app.engines.monitoring.router.collect_portfolio_snapshot",
            return_value=_make_mock_snapshot(),
        ):
            resp = await client.get("/api/v1/monitoring/snapshot")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == 100000.0
        assert data["num_positions"] == 2
