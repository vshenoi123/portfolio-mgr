from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator, model_validator


class OrderRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop", "stop_limit", "trailing_stop"]
    quantity: float
    time_in_force: Literal["day", "gtc", "opg", "cls", "ioc", "fok"] = "day"
    price: float | None = None
    stop_price: float | None = None
    strategy_type: str = "equity"
    notes: str = ""

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v

    @model_validator(mode="after")
    def validate_order_type_requirements(self) -> "OrderRequest":
        if self.order_type in ("limit", "stop_limit") and self.price is None:
            raise ValueError(f"price is required for {self.order_type} orders")
        if self.order_type in ("stop", "stop_limit") and self.stop_price is None:
            raise ValueError(f"stop_price is required for {self.order_type} orders")
        return self


class CancelRequest(BaseModel):
    order_id: int | None = None
    alpaca_order_id: str | None = None

    @model_validator(mode="after")
    def at_least_one_id(self) -> "CancelRequest":
        if self.order_id is None and self.alpaca_order_id is None:
            raise ValueError("Must provide order_id or alpaca_order_id")
        return self


class ModifyRequest(BaseModel):
    order_id: int
    quantity: float | None = None
    price: float | None = None
    stop_price: float | None = None
    time_in_force: str | None = None

    @model_validator(mode="after")
    def at_least_one_change(self) -> "ModifyRequest":
        if all(v is None for v in (self.quantity, self.price, self.stop_price, self.time_in_force)):
            raise ValueError("Must provide at least one field to modify")
        return self


class OrderResponse(BaseModel):
    id: int | None = None
    alpaca_order_id: str | None = None
    ticker: str = ""
    side: str = ""
    order_type: str = ""
    quantity: float = 0
    filled_qty: float = 0
    price: float | None = None
    stop_price: float | None = None
    status: str = "pending"
    filled_avg_price: float | None = None
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    strategy_type: str = "equity"
    notes: str = ""


class TradeResult(BaseModel):
    success: bool
    message: str
    order_id: int | None = None
    alpaca_order_id: str | None = None
    order: OrderResponse | None = None
