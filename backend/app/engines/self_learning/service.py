"""Self-learning engine that tracks signal efficacy and trade performance."""

from datetime import datetime, timezone
import duckdb
from app.config import settings
from app.engines.self_learning.schemas import SelfLearningSummary


def log_trade(ticker: str, side: str, strategy_type: str, entry_price: float,
              quantity: float, entry_date: datetime | None = None,
              regime: str = "Unknown") -> dict:
    conn = duckdb.connect(settings.database_path)
    try:
        conn.execute("""
            INSERT INTO trade_journal (ticker, side, strategy_type, entry_price,
                quantity, entry_date, regime_at_entry)
            VALUES (?, ?, ?, ?, ?, COALESCE(?, NOW()), ?)
        """, (ticker, side, strategy_type, entry_price, quantity, entry_date, regime))
        return {"status": "success", "ticker": ticker}
    finally:
        conn.close()


def close_trade(trade_id: int, exit_price: float, exit_reason: str = "",
                regime: str = "Unknown") -> dict:
    conn = duckdb.connect(settings.database_path)
    try:
        trade = conn.execute("SELECT entry_price, quantity, entry_date FROM trade_journal WHERE id = ?",
                            (trade_id,)).fetchone()
        if not trade:
            return {"status": "error", "message": "Trade not found"}
        entry_price, quantity, entry_date = trade
        gross_pl = (exit_price - entry_price) * quantity
        days_held = (datetime.now(timezone.utc) - entry_date.replace(tzinfo=timezone.utc)).days
        conn.execute("""
            UPDATE trade_journal SET exit_price = ?, gross_pl = ?, net_pl = ?,
                days_held = ?, exit_reason = ?, exit_date = NOW(),
                regime_at_exit = ?
            WHERE id = ?
        """, (exit_price, gross_pl, gross_pl, days_held, exit_reason, regime, trade_id))
        return {"status": "success", "gross_pl": gross_pl}
    finally:
        conn.close()


def compute_signal_efficacy(db_path: str | None = None) -> SelfLearningSummary:
    path = db_path or settings.database_path
    conn = duckdb.connect(path)
    try:
        trades = conn.execute("""
            SELECT COUNT(*), COALESCE(AVG(CASE WHEN gross_pl > 0 THEN gross_pl END), 0),
                   COALESCE(AVG(CASE WHEN gross_pl < 0 THEN gross_pl END), 0),
                   COALESCE(SUM(CASE WHEN gross_pl > 0 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0), 0)
            FROM trade_journal WHERE exit_price IS NOT NULL
        """).fetchone()
        total = trades[0] or 0
        avg_win = trades[1] or 0.0
        avg_loss = abs(trades[2]) or 0.0
        win_rate = trades[3] or 0.0
        profit_factor = (avg_win * win_rate * total) / (avg_loss * (1 - win_rate) * total + 1) if total > 0 else 0

        strategy_counts = conn.execute("""
            SELECT strategy_type, COUNT(*), AVG(gross_pl) FROM trade_journal
            WHERE exit_price IS NOT NULL GROUP BY strategy_type
        """).fetchall()

        return SelfLearningSummary(
            total_trades=total, win_rate=round(win_rate * 100, 2),
            avg_win=round(avg_win, 2), avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            strategy_breakdown={r[0]: {"count": r[1], "avg_pl": round(r[2], 2)} for r in strategy_counts},
        )
    finally:
        conn.close()
