import logging
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.trading.schemas import CancelRequest, ModifyRequest, OrderRequest, OrderResponse, TradeResult
from app.engines.trading.service import AlpacaClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


def get_client() -> AlpacaClient:
    return AlpacaClient()


@router.post("/orders", response_model=TradeResult)
def place_order(req: OrderRequest, client: AlpacaClient = Depends(get_client)):
    return client.place_order(req)


@router.delete("/orders", response_model=TradeResult)
def cancel_order(req: CancelRequest, client: AlpacaClient = Depends(get_client)):
    return client.cancel_order(req)


@router.patch("/orders", response_model=TradeResult)
def modify_order(req: ModifyRequest, client: AlpacaClient = Depends(get_client)):
    return client.modify_order(req)


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(
    status: str = "open",
    limit: int = 50,
    client: AlpacaClient = Depends(get_client),
):
    return client.list_orders(status=status, limit=limit)


@router.get("/orders/{order_id}", response_model=Optional[OrderResponse])
def get_order(order_id: int, client: AlpacaClient = Depends(get_client)):
    return client.get_order(order_id=order_id)


@router.get("/positions", response_model=list[dict])
def list_positions(client: AlpacaClient = Depends(get_client)):
    import duckdb
    from app.config import settings
    conn = duckdb.connect(settings.database_path)
    try:
        rows = conn.execute(
            "SELECT ticker, quantity, avg_price, current_price, market_value, cost_basis, unrealized_pl, strategy_type FROM positions ORDER BY ticker"
        ).fetchall()
        return [
            {
                "ticker": r[0],
                "quantity": float(r[1]),
                "avg_price": float(r[2]) if r[2] else 0,
                "current_price": float(r[3]) if r[3] else 0,
                "market_value": float(r[4]) if r[4] else 0,
                "cost_basis": float(r[5]) if r[5] else 0,
                "unrealized_pl": float(r[6]) if r[6] else 0,
                "strategy_type": r[7],
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/positions/{ticker}", response_model=Optional[dict])
def get_position(ticker: str, client: AlpacaClient = Depends(get_client)):
    import duckdb
    from app.config import settings
    conn = duckdb.connect(settings.database_path)
    try:
        row = conn.execute(
            "SELECT ticker, quantity, avg_price, current_price, market_value, cost_basis, unrealized_pl, strategy_type FROM positions WHERE ticker = ?",
            (ticker.upper(),),
        ).fetchone()
        if not row:
            return None
        return {
            "ticker": row[0],
            "quantity": float(row[1]),
            "avg_price": float(row[2]) if row[2] else 0,
            "current_price": float(row[3]) if row[3] else 0,
            "market_value": float(row[4]) if row[4] else 0,
            "cost_basis": float(row[5]) if row[5] else 0,
            "unrealized_pl": float(row[6]) if row[6] else 0,
            "strategy_type": row[7],
        }
    finally:
        conn.close()


@router.post("/sync", response_model=TradeResult)
def sync_positions(
    client: AlpacaClient = Depends(get_client),
    _=Depends(verify_api_key),
):
    return client.sync_positions()
