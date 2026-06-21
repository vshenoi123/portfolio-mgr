import pytest
from pydantic import ValidationError
from datetime import datetime, timezone


class TestOrderRequest:
    def test_valid_market_order(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100)
        assert req.ticker == "AAPL"
        assert req.side == "buy"
        assert req.time_in_force == "day"

    def test_valid_limit_order(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="sell", order_type="limit", quantity=50, price=150.0)
        assert req.price == 150.0

    def test_valid_stop_order(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="buy", order_type="stop", quantity=100, stop_price=145.0)
        assert req.stop_price == 145.0

    def test_valid_stop_limit_order(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="buy", order_type="stop_limit", quantity=100, price=150.0, stop_price=148.0)
        assert req.price == 150.0
        assert req.stop_price == 148.0

    def test_valid_trailing_stop(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="sell", order_type="trailing_stop", quantity=10, price=5.0)
        assert req.price == 5.0

    def test_invalid_quantity_zero(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError) as exc:
            OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=0)
        assert "quantity must be positive" in str(exc.value)

    def test_invalid_quantity_negative(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=-5)

    def test_limit_order_missing_price(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError) as exc:
            OrderRequest(ticker="AAPL", side="buy", order_type="limit", quantity=100)
        assert "price is required" in str(exc.value)

    def test_stop_order_missing_stop_price(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError) as exc:
            OrderRequest(ticker="AAPL", side="buy", order_type="stop", quantity=100)
        assert "stop_price is required" in str(exc.value)

    def test_stop_limit_missing_both(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="buy", order_type="stop_limit", quantity=100)


class TestCancelRequest:
    def test_valid_by_order_id(self):
        from app.engines.trading.schemas import CancelRequest
        req = CancelRequest(order_id=42)
        assert req.order_id == 42

    def test_valid_by_alpaca_id(self):
        from app.engines.trading.schemas import CancelRequest
        req = CancelRequest(alpaca_order_id="abc-123")
        assert req.alpaca_order_id == "abc-123"

    def test_invalid_no_ids(self):
        from app.engines.trading.schemas import CancelRequest
        with pytest.raises(ValidationError) as exc:
            CancelRequest()
        assert "Must provide order_id or alpaca_order_id" in str(exc.value)


class TestModifyRequest:
    def test_valid_quantity_change(self):
        from app.engines.trading.schemas import ModifyRequest
        req = ModifyRequest(order_id=1, quantity=200)
        assert req.quantity == 200

    def test_valid_price_change(self):
        from app.engines.trading.schemas import ModifyRequest
        req = ModifyRequest(order_id=1, price=155.0)
        assert req.price == 155.0

    def test_valid_all_fields(self):
        from app.engines.trading.schemas import ModifyRequest
        req = ModifyRequest(order_id=1, quantity=100, price=150.0, stop_price=145.0, time_in_force="gtc")
        assert req.time_in_force == "gtc"

    def test_invalid_no_changes(self):
        from app.engines.trading.schemas import ModifyRequest
        with pytest.raises(ValidationError) as exc:
            ModifyRequest(order_id=1)
        assert "Must provide at least one field" in str(exc.value)


class TestOrderResponse:
    def test_default_construction(self):
        from app.engines.trading.schemas import OrderResponse
        resp = OrderResponse()
        assert resp.status == "pending"
        assert resp.ticker == ""
        assert resp.quantity == 0

    def test_full_construction(self):
        from app.engines.trading.schemas import OrderResponse
        dt = datetime.now(timezone.utc)
        resp = OrderResponse(
            id=1, alpaca_order_id="abc", ticker="AAPL", side="buy",
            order_type="market", quantity=100, filled_qty=100,
            price=150.0, status="filled", filled_avg_price=150.5,
            submitted_at=dt, filled_at=dt,
        )
        assert resp.id == 1
        assert resp.status == "filled"
        assert resp.filled_avg_price == 150.5


class TestTradeResult:
    def test_success_result(self):
        from app.engines.trading.schemas import TradeResult, OrderResponse
        order = OrderResponse(id=1, ticker="AAPL", status="filled")
        result = TradeResult(success=True, message="OK", order_id=1, order=order)
        assert result.success is True
        assert result.order_id == 1

    def test_failure_result(self):
        from app.engines.trading.schemas import TradeResult
        result = TradeResult(success=False, message="Insufficient funds")
        assert result.success is False
        assert result.order_id is None
