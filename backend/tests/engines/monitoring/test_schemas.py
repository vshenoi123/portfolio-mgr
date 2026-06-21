import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestMonitoringSchemas:
    def test_portfolio_snapshot_valid(self):
        from app.engines.monitoring.schemas import PortfolioSnapshot
        snap = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=100000.0, cash=25000.0,
            equity_value=70000.0, options_value=5000.0,
            num_positions=3, portfolio_beta=1.2, portfolio_delta_e=500.0,
        )
        assert snap.total_value == 100000.0
        assert snap.num_positions == 3

    def test_position_snapshot_valid(self):
        from app.engines.monitoring.schemas import PositionSnapshot
        pos = PositionSnapshot(ticker="AAPL", quantity=100.0, market_value=16500.0)
        assert pos.ticker == "AAPL"
        assert pos.sector == "UNKNOWN"

    def test_order_snapshot_valid(self):
        from app.engines.monitoring.schemas import OrderSnapshot
        now = datetime.now(timezone.utc)
        order = OrderSnapshot(
            alpaca_order_id="ord_123", ticker="NVDA",
            side="buy", order_type="market", quantity=10.0,
            submitted_at=now,
        )
        assert order.status == "pending"
        assert order.filled_qty == 0.0

    def test_health_score_level_healthy(self):
        from app.engines.monitoring.schemas import PortfolioHealthScore
        hs = PortfolioHealthScore(score=85.0)
        assert hs.level == "healthy"

    def test_health_score_level_warning(self):
        from app.engines.monitoring.schemas import PortfolioHealthScore
        hs = PortfolioHealthScore(score=45.0)
        assert hs.level == "warning"

    def test_health_score_level_critical(self):
        from app.engines.monitoring.schemas import PortfolioHealthScore
        hs = PortfolioHealthScore(score=15.0)
        assert hs.level == "critical"

    def test_health_score_invalid_score(self):
        from app.engines.monitoring.schemas import PortfolioHealthScore
        with pytest.raises(ValidationError):
            PortfolioHealthScore(score=150.0)
        with pytest.raises(ValidationError):
            PortfolioHealthScore(score=-10.0)

    def test_alert_event_valid(self):
        from app.engines.monitoring.schemas import AlertEvent
        now = datetime.now(timezone.utc)
        alert = AlertEvent(
            alert_type="low_cash", severity="warning",
            message="Cash below threshold", timestamp=now,
        )
        assert alert.details == {}

    def test_monitoring_summary_valid(self):
        from app.engines.monitoring.schemas import (
            MonitoringSummary, PortfolioSnapshot, PortfolioHealthScore,
        )
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now)
        health = PortfolioHealthScore(score=75.0)
        summary = MonitoringSummary(
            portfolio=snap, health=health, timestamp=now,
        )
        assert summary.health.score == 75.0
        assert summary.health.level == "healthy"
