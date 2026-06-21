import duckdb
from datetime import datetime, timezone

from app.engines.monitoring.schemas import (
    PortfolioSnapshot, PositionSnapshot, OrderSnapshot,
    PortfolioHealthScore, AlertEvent, MonitoringSummary,
)
from app.engines.risk.service import calculate_portfolio_health


def collect_portfolio_snapshot(db_path: str) -> PortfolioSnapshot:
    conn = duckdb.connect(db_path)
    try:
        row = conn.execute(
            "SELECT total_value, cash, equity_value, options_value, "
            "portfolio_beta, portfolio_delta_e "
            "FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        count = conn.execute(
            "SELECT COUNT(*) FROM positions WHERE quantity != 0"
        ).fetchone()[0]

        if row:
            return PortfolioSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_value=float(row[0]),
                cash=float(row[1]),
                equity_value=float(row[2]),
                options_value=float(row[3]),
                num_positions=int(count),
                portfolio_beta=float(row[4]),
                portfolio_delta_e=float(row[5]),
            )
        return PortfolioSnapshot(timestamp=datetime.now(timezone.utc))
    finally:
        conn.close()


def collect_position_snapshots(db_path: str) -> list[PositionSnapshot]:
    conn = duckdb.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT ticker, quantity, market_value, unrealized_pl, "
            "unrealized_pl_pct, strategy_type, sector "
            "FROM positions WHERE quantity != 0"
        ).fetchall()
        return [
            PositionSnapshot(
                ticker=str(r[0]), quantity=float(r[1]),
                market_value=float(r[2]), unrealized_pl=float(r[3]),
                unrealized_pl_pct=float(r[4]),
                strategy_type=str(r[5]), sector=str(r[6]),
            ) for r in rows
        ]
    finally:
        conn.close()


def collect_order_snapshots(db_path: str) -> list[OrderSnapshot]:
    conn = duckdb.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT alpaca_order_id, ticker, side, order_type, quantity, "
            "filled_qty, status, submitted_at "
            "FROM orders WHERE status IN ('pending', 'open', 'partial_fill')"
        ).fetchall()
        return [
            OrderSnapshot(
                alpaca_order_id=str(r[0]), ticker=str(r[1]),
                side=str(r[2]), order_type=str(r[3]),
                quantity=float(r[4]), filled_qty=float(r[5]),
                status=str(r[6]),
                submitted_at=r[7] if r[7] else None,
            ) for r in rows
        ]
    finally:
        conn.close()


def compute_health_score(assessment: dict) -> PortfolioHealthScore:
    score = calculate_portfolio_health(
        max_drawdown=assessment.get("max_drawdown", 0),
        concentration_pct=assessment.get("concentration_pct", 0),
        portfolio_beta=assessment.get("portfolio_beta", 0),
        total_exposure_pct=assessment.get("total_exposure_pct", 0),
        cash_pct=assessment.get("cash_pct", 0),
        num_violations=assessment.get("num_violations", 0),
        unrealized_volatility=assessment.get("unrealized_volatility", 0),
    )
    return PortfolioHealthScore(
        score=score,
        components={k: v for k, v in assessment.items() if k != "components"},
    )


def check_alerts(
    snapshot: PortfolioSnapshot,
    health_score: PortfolioHealthScore,
) -> list[AlertEvent]:
    alerts = []
    now = datetime.now(timezone.utc)

    if snapshot.total_value > 0:
        cash_pct = snapshot.cash / snapshot.total_value * 100
        if cash_pct <= 0:
            alerts.append(AlertEvent(
                alert_type="low_cash", severity="critical",
                message="Cash balance is zero or negative",
                timestamp=now,
            ))
        elif cash_pct < 5:
            alerts.append(AlertEvent(
                alert_type="low_cash", severity="warning",
                message=f"Cash is {cash_pct:.1f}% of portfolio (below 5%)",
                timestamp=now,
            ))

    if health_score.level == "critical":
        alerts.append(AlertEvent(
            alert_type="health", severity="critical",
            message=f"Portfolio health score is {health_score.score:.1f}",
            timestamp=now,
        ))
    elif health_score.level == "warning":
        alerts.append(AlertEvent(
            alert_type="health", severity="warning",
            message=f"Portfolio health score is {health_score.score:.1f}",
            timestamp=now,
        ))

    return alerts


def collect_monitoring_summary(db_path: str) -> MonitoringSummary:
    snapshot = collect_portfolio_snapshot(db_path)
    positions = collect_position_snapshots(db_path)
    orders = collect_order_snapshots(db_path)

    total_exposure = snapshot.equity_value + snapshot.options_value
    exposure_pct = (total_exposure / snapshot.total_value * 100) if snapshot.total_value > 0 else 0
    cash_pct = (snapshot.cash / snapshot.total_value * 100) if snapshot.total_value > 0 else 0

    assessment = {
        "max_drawdown": 0,
        "concentration_pct": 0,
        "portfolio_beta": snapshot.portfolio_beta,
        "total_exposure_pct": exposure_pct,
        "cash_pct": cash_pct,
        "num_violations": 0,
        "unrealized_volatility": 0,
    }

    health = compute_health_score(assessment)
    alerts = check_alerts(snapshot, health)

    return MonitoringSummary(
        portfolio=snapshot,
        positions=positions,
        open_orders=orders,
        health=health,
        alerts=alerts,
        timestamp=datetime.now(timezone.utc),
    )
