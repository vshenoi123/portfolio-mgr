import logging
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

import duckdb
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
    TrailingStopOrderRequest,
)

from app.config import settings
from app.engines.trading.schemas import (
    CancelRequest,
    ModifyRequest,
    OrderRequest,
    OrderResponse,
    TradeResult,
)

logger = logging.getLogger(__name__)

SIDE_MAP = {"buy": OrderSide.BUY, "sell": OrderSide.SELL}
TIF_MAP: dict[str, TimeInForce] = {
    "day": TimeInForce.DAY,
    "gtc": TimeInForce.GTC,
    "opg": TimeInForce.OPG,
    "cls": TimeInForce.CLS,
    "ioc": TimeInForce.IOC,
    "fok": TimeInForce.FOK,
}


def _row_to_order_response(row: tuple) -> OrderResponse:
    return OrderResponse(
        id=row[0],
        alpaca_order_id=row[1],
        ticker=row[2],
        side=row[3],
        order_type=row[4],
        quantity=float(row[5]) if row[5] is not None else 0,
        filled_qty=float(row[6]) if row[6] is not None else 0,
        price=float(row[7]) if row[7] is not None else None,
        stop_price=float(row[8]) if row[8] is not None else None,
        status=row[9],
        strategy_type=row[10],
        filled_avg_price=float(row[11]) if row[11] is not None else None,
        filled_at=row[12],
        submitted_at=row[13],
        notes=row[15] if len(row) > 15 else "",
    )


class AlpacaClient:
    def __init__(self):
        self._settings = settings
        if settings.alpaca_api_key and settings.alpaca_secret_key:
            self._client = TradingClient(
                settings.alpaca_api_key,
                settings.alpaca_secret_key,
                paper=True,
            )
            self._enabled = True
        else:
            self._client = None
            self._enabled = False
            logger.warning("Alpaca API keys not configured; trading disabled")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _execute(self, action: Callable[[], Any]) -> TradeResult:
        if not self._enabled:
            return TradeResult(success=False, message="Alpaca API not configured")
        try:
            return action()
        except Exception as e:
            logger.exception("Alpaca API call failed")
            return TradeResult(success=False, message=str(e))

    def _build_alpaca_order(self, req: OrderRequest) -> Any:
        side = SIDE_MAP[req.side]
        tif = TIF_MAP[req.time_in_force]

        if req.order_type == "market":
            return MarketOrderRequest(
                symbol=req.ticker, qty=req.quantity, side=side, time_in_force=tif
            )
        elif req.order_type == "limit":
            return LimitOrderRequest(
                symbol=req.ticker, qty=req.quantity, side=side,
                time_in_force=tif, limit_price=req.price,
            )
        elif req.order_type == "stop":
            return StopOrderRequest(
                symbol=req.ticker, qty=req.quantity, side=side,
                time_in_force=tif, stop_price=req.stop_price,
            )
        elif req.order_type == "stop_limit":
            return StopLimitOrderRequest(
                symbol=req.ticker, qty=req.quantity, side=side,
                time_in_force=tif, limit_price=req.price,
                stop_price=req.stop_price,
            )
        elif req.order_type == "trailing_stop":
            return TrailingStopOrderRequest(
                symbol=req.ticker, qty=req.quantity, side=side,
                time_in_force=tif, trail_price=req.price,
            )
        raise ValueError(f"Unknown order_type: {req.order_type}")

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        from app.database import get_connection
        return get_connection(self._settings.database_path)

    def _save_to_db(self, order_data: dict, conn: duckdb.DuckDBPyConnection) -> int:
        conn.execute(
            """
            INSERT INTO orders
                (alpaca_order_id, ticker, side, order_type, time_in_force,
                 quantity, filled_qty, price, stop_price, status,
                 filled_avg_price, filled_at, submitted_at, strategy_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_data.get("alpaca_order_id"),
                order_data["ticker"],
                order_data["side"],
                order_data["order_type"],
                order_data.get("time_in_force", "day"),
                order_data["quantity"],
                order_data.get("filled_qty", 0),
                order_data.get("price"),
                order_data.get("stop_price"),
                order_data.get("status", "pending"),
                order_data.get("filled_avg_price"),
                order_data.get("filled_at"),
                order_data.get("submitted_at", datetime.now(timezone.utc)),
                order_data.get("strategy_type", "equity"),
                order_data.get("notes", ""),
            ),
        )
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        return int(row[0]) if row else 0

    def _update_order_in_db(
        self, alpaca_order_id: str, update_data: dict,
        conn: duckdb.DuckDBPyConnection,
    ) -> None:
        fields = []
        values = []
        for key, val in update_data.items():
            fields.append(f"{key} = ?")
            values.append(val)
        values.append(alpaca_order_id)
        conn.execute(
            f"UPDATE orders SET {', '.join(fields)} WHERE alpaca_order_id = ?",
            values,
        )

    def _alpaca_order_to_dict(self, order: Any, req: OrderRequest | None = None) -> dict:
        return {
            "alpaca_order_id": str(order.id),
            "ticker": order.symbol,
            "side": order.side.value if hasattr(order.side, "value") else str(order.side),
            "order_type": order.type.value if hasattr(order.type, "value") else str(order.type),
            "time_in_force": order.time_in_force.value if hasattr(order.time_in_force, "value") else str(order.time_in_force),
            "quantity": float(order.qty),
            "filled_qty": float(order.filled_qty or 0),
            "price": float(order.limit_price) if order.limit_price else None,
            "stop_price": float(order.stop_price) if order.stop_price else None,
            "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            "submitted_at": order.submitted_at,
            "filled_at": order.filled_at,
            "strategy_type": req.strategy_type if req else "equity",
            "notes": req.notes if req else "",
        }

    def place_order(self, req: OrderRequest) -> TradeResult:
        def _place() -> TradeResult:
            alpaca_req = self._build_alpaca_order(req)
            order = self._client.submit_order(alpaca_req)
            order_data = self._alpaca_order_to_dict(order, req)
            conn = self._get_connection()
            try:
                order_id = self._save_to_db(order_data, conn)
            finally:
                conn.close()
            order_resp = OrderResponse(
                id=order_id, **{k: v for k, v in order_data.items() if k in OrderResponse.model_fields},
            )
            return TradeResult(
                success=True, message="Order placed",
                order_id=order_id,
                alpaca_order_id=str(order.id),
                order=order_resp,
            )

        return self._execute(_place)

    def cancel_order(self, req: CancelRequest) -> TradeResult:
        def _cancel() -> TradeResult:
            if req.alpaca_order_id:
                alpaca_id = req.alpaca_order_id
            else:
                conn = self._get_connection()
                try:
                    row = conn.execute(
                        "SELECT alpaca_order_id FROM orders WHERE id = ?", (req.order_id,)
                    ).fetchone()
                finally:
                    conn.close()
                if not row or not row[0]:
                    return TradeResult(success=False, message="Order not found in DB")
                alpaca_id = row[0]

            self._client.cancel_order_by_id(alpaca_id)
            conn = self._get_connection()
            try:
                self._update_order_in_db(alpaca_id, {"status": "canceled"}, conn)
            finally:
                conn.close()
            return TradeResult(success=True, message="Order canceled", alpaca_order_id=alpaca_id)

        return self._execute(_cancel)

    def modify_order(self, req: ModifyRequest) -> TradeResult:
        def _modify() -> TradeResult:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT alpaca_order_id, ticker, side, order_type, quantity, price, stop_price, time_in_force, strategy_type, notes FROM orders WHERE id = ?",
                    (req.order_id,),
                ).fetchone()
            finally:
                conn.close()

            if not row:
                return TradeResult(success=False, message="Order not found")

            alpaca_id = row[0]
            self._client.cancel_order_by_id(alpaca_id)

            new_qty = req.quantity if req.quantity is not None else float(row[4])
            new_price = req.price if req.price is not None else (float(row[5]) if row[5] else None)
            new_stop = req.stop_price if req.stop_price is not None else (float(row[6]) if row[6] else None)
            new_tif = req.time_in_force if req.time_in_force else row[7]

            modify_req = OrderRequest(
                ticker=row[1],
                side=row[2],
                order_type=row[3],
                quantity=new_qty,
                time_in_force=new_tif,
                price=new_price,
                stop_price=new_stop,
                strategy_type=row[8],
                notes=row[9] or "",
            )
            return self.place_order(modify_req)

        return self._execute(_modify)

    def get_order(
        self, order_id: int | None = None, alpaca_order_id: str | None = None,
    ) -> OrderResponse | None:
        conn = self._get_connection()
        try:
            if order_id:
                row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            elif alpaca_order_id:
                row = conn.execute(
                    "SELECT * FROM orders WHERE alpaca_order_id = ?", (alpaca_order_id,),
                ).fetchone()
            else:
                return None
            return _row_to_order_response(row) if row else None
        finally:
            conn.close()

    def list_orders(self, status: str = "open", limit: int = 50) -> list[OrderResponse]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
            return [_row_to_order_response(r) for r in rows]
        finally:
            conn.close()

    def sync_positions(self) -> TradeResult:
        def _sync() -> TradeResult:
            logger.info("Syncing positions from Alpaca...")
            positions = self._client.get_all_positions()
            logger.info("Found %d positions on Alpaca", len(positions))
            for pos in positions:
                logger.info("  Position: %s qty=%s avg_entry=$%s current=$%s market_value=$%s pl=$%s",
                    pos.symbol, pos.qty, pos.avg_entry_price, pos.current_price,
                    pos.market_value, pos.unrealized_pl)
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM positions")
                for pos in positions:
                    ticker = pos.symbol
                    qty = float(pos.qty)
                    conn.execute(
                        """
                        INSERT INTO positions
                            (ticker, quantity, avg_price, current_price,
                             market_value, cost_basis, unrealized_pl,
                             unrealized_pl_pct, strategy_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'trading')
                        """,
                        (
                            ticker,
                            qty,
                            float(pos.avg_entry_price),
                            float(pos.current_price),
                            float(pos.market_value),
                            float(pos.cost_basis),
                            float(pos.unrealized_pl),
                            float(pos.unrealized_plpc or 0),
                        ),
                    )
                logger.info("Synced %d positions to DuckDB", len(positions))
                return TradeResult(
                    success=True,
                    message=f"Synced {len(positions)} positions",
                )
            finally:
                conn.close()

        return self._execute(_sync)
