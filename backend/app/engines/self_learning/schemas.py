from datetime import datetime
from pydantic import BaseModel


class TradeRecord(BaseModel):
    ticker: str
    side: str
    strategy_type: str
    entry_price: float
    exit_price: float | None = None
    quantity: float
    gross_pl: float = 0.0
    net_pl: float = 0.0
    entry_date: datetime
    exit_date: datetime | None = None
    days_held: int = 0
    exit_reason: str = ""
    regime_at_entry: str = "Unknown"
    regime_at_exit: str = "Unknown"


class SignalEfficacy(BaseModel):
    signal_type: str
    total_signals: int = 0
    accurate: int = 0
    accuracy_pct: float = 0.0
    avg_return: float = 0.0


class SelfLearningSummary(BaseModel):
    total_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    best_regime: str = ""
    worst_regime: str = ""
    strategy_breakdown: dict = {}
    signal_efficacy: list[SignalEfficacy] = []
