import logging
from fastapi import APIRouter

from app.engines.self_learning.schemas import TradeRecord
from app.engines.self_learning.service import log_trade, close_trade, compute_signal_efficacy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/self-learning", tags=["self-learning"])


@router.post("/trades")
def record_trade(trade: TradeRecord):
    result = log_trade(
        ticker=trade.ticker, side=trade.side, strategy_type=trade.strategy_type,
        entry_price=trade.entry_price, quantity=trade.quantity,
        entry_date=trade.entry_date, regime=trade.regime_at_entry,
    )
    return result


@router.post("/trades/close/{trade_id}")
def close_trade_route(trade_id: int, exit_price: float, exit_reason: str = "", regime: str = "Unknown"):
    result = close_trade(trade_id, exit_price, exit_reason, regime)
    return result


@router.get("/efficacy")
def get_efficacy():
    summary = compute_signal_efficacy()
    return summary.model_dump()
