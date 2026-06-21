import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestCollectSnapshots:
    @patch("app.engines.monitoring.service.duckdb")
    def test_collect_portfolio_snapshot(self, mock_duckdb):
        from app.engines.monitoring.service import collect_portfolio_snapshot
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [
            (100000.0, 25000.0, 70000.0, 5000.0, 1.2, 500.0),
            (3,),
        ]
        result = collect_portfolio_snapshot("/fake/path")
        assert result.total_value == 100000.0
        assert result.cash == 25000.0
        assert result.num_positions == 3
        assert result.portfolio_beta == 1.2

    @patch("app.engines.monitoring.service.duckdb")
    def test_collect_portfolio_snapshot_empty(self, mock_duckdb):
        from app.engines.monitoring.service import collect_portfolio_snapshot
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.side_effect = [None, (0,)]
        result = collect_portfolio_snapshot("/fake/path")
        assert result.total_value == 0.0
        assert result.num_positions == 0

    @patch("app.engines.monitoring.service.duckdb")
    def test_collect_position_snapshots(self, mock_duckdb):
        from app.engines.monitoring.service import collect_position_snapshots
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("AAPL", 100, 16500, 1500, 10.0, "equity", "TECHNOLOGY"),
            ("NVDA", 50, 4750, 750, 18.75, "swing", "TECHNOLOGY"),
        ]
        result = collect_position_snapshots("/fake/path")
        assert len(result) == 2
        assert result[0].ticker == "AAPL"
        assert result[1].strategy_type == "swing"

    @patch("app.engines.monitoring.service.duckdb")
    def test_collect_order_snapshots(self, mock_duckdb):
        from app.engines.monitoring.service import collect_order_snapshots
        mock_conn = MagicMock()
        mock_duckdb.connect.return_value = mock_conn
        now = datetime.now(timezone.utc)
        mock_conn.execute.return_value.fetchall.return_value = [
            ("ord_1", "AAPL", "buy", "market", 10, 5, "partial_fill", now),
            ("ord_2", "NVDA", "sell", "limit", 5, 0, "pending", None),
        ]
        result = collect_order_snapshots("/fake/path")
        assert len(result) == 2
        assert result[0].alpaca_order_id == "ord_1"
        assert result[0].submitted_at == now
        assert result[1].submitted_at is None


class TestHealthScore:
    @patch("app.engines.monitoring.service.calculate_portfolio_health")
    def test_healthy(self, mock_calc):
        mock_calc.return_value = 85.0
        from app.engines.monitoring.service import compute_health_score
        hs = compute_health_score({"max_drawdown": 5, "cash_pct": 25})
        assert hs.score == 85.0
        assert hs.level == "healthy"

    @patch("app.engines.monitoring.service.calculate_portfolio_health")
    def test_warning(self, mock_calc):
        mock_calc.return_value = 45.0
        from app.engines.monitoring.service import compute_health_score
        hs = compute_health_score({"max_drawdown": 15})
        assert hs.score == 45.0
        assert hs.level == "warning"

    @patch("app.engines.monitoring.service.calculate_portfolio_health")
    def test_critical(self, mock_calc):
        mock_calc.return_value = 15.0
        from app.engines.monitoring.service import compute_health_score
        hs = compute_health_score({"num_violations": 5})
        assert hs.score == 15.0
        assert hs.level == "critical"


class TestAlerts:
    def test_low_cash_critical(self):
        from app.engines.monitoring.service import check_alerts
        from app.engines.monitoring.schemas import PortfolioSnapshot, PortfolioHealthScore
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now, total_value=100000, cash=0)
        health = PortfolioHealthScore(score=75.0)
        alerts = check_alerts(snap, health)
        assert any(a.alert_type == "low_cash" and a.severity == "critical" for a in alerts)

    def test_low_cash_warning(self):
        from app.engines.monitoring.service import check_alerts
        from app.engines.monitoring.schemas import PortfolioSnapshot, PortfolioHealthScore
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now, total_value=100000, cash=2000)
        health = PortfolioHealthScore(score=75.0)
        alerts = check_alerts(snap, health)
        assert any(a.alert_type == "low_cash" and a.severity == "warning" for a in alerts)

    def test_health_alert_critical(self):
        from app.engines.monitoring.service import check_alerts
        from app.engines.monitoring.schemas import PortfolioSnapshot, PortfolioHealthScore
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now, total_value=100000, cash=25000)
        health = PortfolioHealthScore(score=15.0)
        alerts = check_alerts(snap, health)
        assert any(a.alert_type == "health" and a.severity == "critical" for a in alerts)

    def test_health_alert_warning(self):
        from app.engines.monitoring.service import check_alerts
        from app.engines.monitoring.schemas import PortfolioSnapshot, PortfolioHealthScore
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now, total_value=100000, cash=25000)
        health = PortfolioHealthScore(score=45.0)
        alerts = check_alerts(snap, health)
        assert any(a.alert_type == "health" and a.severity == "warning" for a in alerts)

    def test_no_alerts_healthy(self):
        from app.engines.monitoring.service import check_alerts
        from app.engines.monitoring.schemas import PortfolioSnapshot, PortfolioHealthScore
        now = datetime.now(timezone.utc)
        snap = PortfolioSnapshot(timestamp=now, total_value=100000, cash=25000)
        health = PortfolioHealthScore(score=85.0)
        alerts = check_alerts(snap, health)
        assert len(alerts) == 0


class TestMonitoringSummary:
    @patch("app.engines.monitoring.service.collect_portfolio_snapshot")
    @patch("app.engines.monitoring.service.collect_position_snapshots")
    @patch("app.engines.monitoring.service.collect_order_snapshots")
    @patch("app.engines.monitoring.service.compute_health_score")
    def test_full_summary(self, mock_health, mock_orders, mock_positions, mock_snapshot):
        from app.engines.monitoring.schemas import (
            PortfolioSnapshot, PortfolioHealthScore, PositionSnapshot, OrderSnapshot,
        )
        from app.engines.monitoring.service import collect_monitoring_summary
        now = datetime.now(timezone.utc)
        mock_snapshot.return_value = PortfolioSnapshot(
            timestamp=now, total_value=100000, cash=25000,
            equity_value=70000, options_value=5000, num_positions=2,
        )
        mock_positions.return_value = [
            PositionSnapshot(ticker="AAPL", quantity=100, market_value=16500),
        ]
        mock_orders.return_value = [
            OrderSnapshot(alpaca_order_id="ord_1", ticker="AAPL", side="buy"),
        ]
        mock_health.return_value = PortfolioHealthScore(score=85.0)

        summary = collect_monitoring_summary("/fake/path")
        assert summary.portfolio.total_value == 100000
        assert len(summary.positions) == 1
        assert len(summary.open_orders) == 1
        assert summary.health.score == 85.0
