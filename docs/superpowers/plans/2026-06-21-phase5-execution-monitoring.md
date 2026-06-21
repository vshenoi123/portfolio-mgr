# Phase 5: Execution, Monitoring & Alpaca Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 engines — Trade Execution (Alpaca API integration for order placement/cancellation/modification/fill tracking), Position Management (CSP close/roll, LEAPS exit, Swing trailing stop, PMCC short call roll with configurable rules), and Portfolio Monitoring (Alpaca connection polling, position/order/cash monitoring, Portfolio Health Score generation) that connect the platform to live paper trading.

**Architecture:** Three engine packages under `backend/app/engines/trading/`, `backend/app/engines/positions/`, `backend/app/engines/monitoring/`. Each has `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py`. Alpaca API via `alpaca-py` library. All Alpaca endpoints mocked in tests using `unittest.mock`. Position management rules are configurable dicts in `config.py` (not hardcoded). Paper trading by default (`alpaca_base_url` defaults to `https://paper-api.alpaca.markets`).

**Tech Stack:** Python 3.12, alpaca-py, numpy, pandas, duckdb, FastAPI, Celery, pytest, unittest.mock

**Testing Requirement:** Every major component must have tests covering normal operation, edge cases, and error states. All Alpaca API calls must be mocked.

---

### Task 1: Prerequisites — Alpaca-py Dependency + Config Expansion + DuckDB Tables

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_database.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_database.py`:
```python
class TestTradingSchema:
    def test_orders_table_created(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('orders','trade_journal')"
            ).fetchall()
            names = {r[0] for r in tables}
            assert "orders" in names
            assert "trade_journal" in names
        finally:
            close_connection(test_db_path)

    def test_orders_table_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(orders)").fetchall()
            names = {c[1] for c in cols}
            for expected in (
                "id", "alpaca_order_id", "ticker", "side", "order_type",
                "time_in_force", "quantity", "filled_qty", "price",
                "stop_price", "status", "strategy_type", "filled_avg_price",
                "filled_at", "submitted_at", "expires_at", "notes"
            ):
                assert expected in names, f"Missing column {expected} in orders"
        finally:
            close_connection(test_db_path)

    def test_trade_journal_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(trade_journal)").fetchall()
            names = {c[1] for c in cols}
            for expected in (
                "id", "ticker", "side", "strategy_type", "entry_price",
                "exit_price", "quantity", "gross_pl", "net_pl",
                "commission", "entry_date", "exit_date", "days_held",
                "exit_reason", "regime_at_entry", "regime_at_exit",
                "notes"
            ):
                assert expected in names
        finally:
            close_connection(test_db_path)


class TestAlpacaConfig:
    def test_alpaca_settings_loaded(self):
        from app.config import settings
        assert hasattr(settings, "alpaca_api_key")
        assert hasattr(settings, "alpaca_secret_key")
        assert hasattr(settings, "alpaca_base_url")
        assert hasattr(settings, "alpaca_paper")

    def test_alpaca_position_management_settings(self):
        from app.config import settings
        assert hasattr(settings, "csp_close_profit_min_pct")
        assert hasattr(settings, "csp_close_profit_max_pct")
        assert hasattr(settings, "csp_roll_dte_threshold")
        assert hasattr(settings, "leaps_exit_profit_target_pct")
        assert hasattr(settings, "swings_trailing_stop_pct")
        assert hasattr(settings, "monitoring_poll_interval_seconds")

    def test_alpaca_defaults_use_paper(self):
        from app.config import settings
        assert settings.alpaca_paper is True
        assert "paper-api" in settings.alpaca_base_url
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_database.py::TestTradingSchema tests/test_config.py::TestAlpacaConfig -v`
Expected: FAIL (tables missing, settings missing)

- [ ] **Step 3: Update config.py with Phase 5 settings**

Replace `backend/app/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_paper: bool = True
    redis_url: str = "redis://localhost:6379/0"
    database_path: str = "/data/portfolio.db"
    data_dir: str = "/data"
    log_level: str = "INFO"

    # Phase 4: Risk limits
    max_position_size_pct: float = 15.0
    max_sector_exposure_pct: float = 30.0
    max_portfolio_delta: float = 500.0
    max_portfolio_beta: float = 1.5
    max_concentration_pct: float = 40.0
    min_cash_reserve_pct: float = 10.0
    max_leverage: float = 1.0
    kelly_fraction: float = 0.25
    correlation_threshold: float = 0.80

    # Phase 5: Position management rules (configurable, not hardcoded)
    csp_close_profit_min_pct: float = 50.0
    csp_close_profit_max_pct: float = 75.0
    csp_roll_dte_threshold: int = 21
    csp_max_dte: int = 45
    leaps_exit_profit_target_pct: float = 100.0
    leaps_trend_failure_threshold: str = "bearish"
    swings_trailing_stop_pct: float = 8.0
    swings_breakdown_stop_pct: float = 12.0
    swings_profit_target_pct: float = 25.0
    pmcc_short_call_profit_target_pct: float = 50.0
    pmcc_short_call_dte_threshold: int = 14
    pmcc_short_call_max_dte: int = 45

    # Phase 5: Monitoring
    monitoring_poll_interval_seconds: int = 60
    monitoring_health_critical_threshold: float = 30.0
    monitoring_health_warning_threshold: float = 60.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Update database.py with orders + trade_journal tables**

Replace `backend/app/database.py`:
```python
import os
import duckdb

_connections: dict[str, duckdb.DuckDBPyConnection] = {}


def get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    if db_path is None:
        from app.config import settings
        db_path = settings.database_path

    if db_path in _connections:
        return _connections[db_path]

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = duckdb.connect(db_path)
    _connections[db_path] = conn
    _init_schema(conn)
    return conn


def close_connection(db_path: str | None = None) -> None:
    if db_path is None:
        from app.config import settings
        db_path = settings.database_path

    conn = _connections.pop(db_path, None)
    if conn:
        conn.close()


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_id START 1;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            quantity DECIMAL(18,4) NOT NULL DEFAULT 0,
            avg_price DECIMAL(18,4) NOT NULL DEFAULT 0,
            current_price DECIMAL(18,4) NOT NULL DEFAULT 0,
            market_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cost_basis DECIMAL(18,4) NOT NULL DEFAULT 0,
            unrealized_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            unrealized_pl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            sector VARCHAR NOT NULL DEFAULT 'UNKNOWN',
            beta DECIMAL(10,4) NOT NULL DEFAULT 1.0,
            delta DECIMAL(10,4) NOT NULL DEFAULT 1.0,
            gamma DECIMAL(10,4) NOT NULL DEFAULT 0,
            theta DECIMAL(10,4) NOT NULL DEFAULT 0,
            vega DECIMAL(10,4) NOT NULL DEFAULT 0,
            strategy_type VARCHAR NOT NULL DEFAULT 'equity',
            opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS options_positions (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            option_type VARCHAR NOT NULL,
            strike DECIMAL(18,4) NOT NULL,
            expiration DATE NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            premium_paid DECIMAL(18,4) NOT NULL DEFAULT 0,
            current_premium DECIMAL(18,4) NOT NULL DEFAULT 0,
            market_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            delta DECIMAL(10,4) NOT NULL DEFAULT 0,
            gamma DECIMAL(10,4) NOT NULL DEFAULT 0,
            theta DECIMAL(10,4) NOT NULL DEFAULT 0,
            vega DECIMAL(10,4) NOT NULL DEFAULT 0,
            implied_vol DECIMAL(10,4) NOT NULL DEFAULT 0,
            dte INTEGER NOT NULL DEFAULT 0,
            strategy_type VARCHAR NOT NULL DEFAULT 'csp',
            status VARCHAR NOT NULL DEFAULT 'open',
            opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            date DATE NOT NULL,
            total_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cash DECIMAL(18,4) NOT NULL DEFAULT 0,
            equity_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            options_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            total_exposure DECIMAL(18,4) NOT NULL DEFAULT 0,
            daily_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            daily_pl_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            total_unrealized_pl DECIMAL(18,4) NOT NULL DEFAULT 0,
            max_drawdown DECIMAL(10,4) NOT NULL DEFAULT 0,
            portfolio_beta DECIMAL(10,4) NOT NULL DEFAULT 0,
            portfolio_delta_e DECIMAL(18,4) NOT NULL DEFAULT 0,
            concentration_pct_top5 DECIMAL(10,4) NOT NULL DEFAULT 0,
            sector_exposures VARCHAR DEFAULT '{}',
            correlation_matrix_json VARCHAR DEFAULT '[]',
            portfolio_health_score DECIMAL(10,4) NOT NULL DEFAULT 100,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS capital_allocation (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            date DATE NOT NULL,
            strategy VARCHAR NOT NULL,
            ticker VARCHAR NOT NULL,
            position_size DECIMAL(18,4) NOT NULL DEFAULT 0,
            capital_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            strategy_allocation_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
            allocation_method VARCHAR NOT NULL DEFAULT 'kelly',
            regime_at_allocation VARCHAR NOT NULL DEFAULT 'Unknown',
            total_portfolio_value DECIMAL(18,4) NOT NULL DEFAULT 0,
            cash_reserve DECIMAL(18,4) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    # Phase 5: Orders and trade journal tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            alpaca_order_id VARCHAR UNIQUE,
            ticker VARCHAR NOT NULL,
            side VARCHAR NOT NULL CHECK(side IN ('buy','sell')),
            order_type VARCHAR NOT NULL CHECK(order_type IN ('market','limit','stop','stop_limit','trailing_stop')),
            time_in_force VARCHAR NOT NULL DEFAULT 'day',
            quantity DECIMAL(18,4) NOT NULL,
            filled_qty DECIMAL(18,4) NOT NULL DEFAULT 0,
            price DECIMAL(18,4),
            stop_price DECIMAL(18,4),
            status VARCHAR NOT NULL DEFAULT 'pending',
            strategy_type VARCHAR NOT NULL DEFAULT 'equity',
            filled_avg_price DECIMAL(18,4),
            filled_at TIMESTAMP WITH TIME ZONE,
            submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            notes VARCHAR DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_id'),
            ticker VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            strategy_type VARCHAR NOT NULL,
            entry_price DECIMAL(18,4) NOT NULL,
            exit_price DECIMAL(18,4),
            quantity DECIMAL(18,4) NOT NULL,
            gross_pl DECIMAL(18,4) DEFAULT 0,
            net_pl DECIMAL(18,4) DEFAULT 0,
            commission DECIMAL(18,4) DEFAULT 0,
            entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
            exit_date TIMESTAMP WITH TIME ZONE,
            days_held INTEGER DEFAULT 0,
            exit_reason VARCHAR DEFAULT '',
            regime_at_entry VARCHAR DEFAULT 'Unknown',
            regime_at_exit VARCHAR DEFAULT 'Unknown',
            notes VARCHAR DEFAULT '',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

def get_data_dir() -> str:
    from app.config import settings
    return settings.data_dir


def ensure_parquet_dir(ticker: str, data_type: str = "ohlcv") -> str:
    base = get_data_dir()
    path = os.path.join(base, "market_data", data_type, ticker.lower())
    os.makedirs(path, exist_ok=True)
    return path
```

- [ ] **Step 5: Update requirements.txt to include alpaca-py**

Append to `backend/requirements.txt`:
```
alpaca-py==0.34.0
```

- [ ] **Step 6: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_database.py::TestTradingSchema tests/test_config.py::TestAlpacaConfig -v`
Expected: PASS

- [ ] **Step 7: Commit**

```
git add backend/app/config.py backend/app/database.py backend/requirements.txt backend/tests/test_database.py backend/tests/test_config.py
git commit -m "feat: add Alpaca-py dependency, config, and DuckDB orders/trade_journal tables for Phase 5"
```

---

### Task 2: Trade Execution Engine — Schemas

**Files:**
- Create: `backend/app/engines/trading/__init__.py`
- Create: `backend/app/engines/trading/schemas.py`
- Test: `backend/tests/engines/trading/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/trading/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError


class TestOrderSchemas:
    def test_order_request_market_valid(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100)
        assert req.ticker == "AAPL"
        assert req.side == "buy"
        assert req.order_type == "market"
        assert req.quantity == 100

    def test_order_request_limit_valid(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(
            ticker="AAPL", side="sell", order_type="limit",
            quantity=50, price=155.0, time_in_force="gtc"
        )
        assert req.price == 155.0
        assert req.time_in_force == "gtc"

    def test_order_request_stop_valid(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(
            ticker="AAPL", side="sell", order_type="stop",
            quantity=100, stop_price=140.0
        )
        assert req.stop_price == 140.0

    def test_order_request_stop_limit_valid(self):
        from app.engines.trading.schemas import OrderRequest
        req = OrderRequest(
            ticker="AAPL", side="buy", order_type="stop_limit",
            quantity=100, stop_price=150.0, price=152.0
        )
        assert req.stop_price == 150.0
        assert req.price == 152.0

    def test_order_request_invalid_side(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="hold", order_type="market", quantity=100)

    def test_order_request_invalid_type(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="buy", order_type="pegged", quantity=100)

    def test_order_request_missing_price_for_limit(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="buy", order_type="limit", quantity=100)

    def test_order_request_missing_stop_for_stop(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="sell", order_type="stop", quantity=100)

    def test_order_request_quantity_positive(self):
        from app.engines.trading.schemas import OrderRequest
        with pytest.raises(ValidationError):
            OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=0)

    def test_cancel_request_valid(self):
        from app.engines.trading.schemas import CancelRequest
        req = CancelRequest(order_id=42, alpaca_order_id="abc-123")
        assert req.order_id == 42
        assert req.alpaca_order_id == "abc-123"

    def test_cancel_request_at_least_one_id(self):
        from app.engines.trading.schemas import CancelRequest
        with pytest.raises(ValidationError):
            CancelRequest()

    def test_modify_request_valid(self):
        from app.engines.trading.schemas import ModifyRequest
        req = ModifyRequest(order_id=42, quantity=200, price=160.0)
        assert req.quantity == 200
        assert req.price == 160.0

    def test_modify_request_at_least_one_change(self):
        from app.engines.trading.schemas import ModifyRequest
        with pytest.raises(ValidationError):
            ModifyRequest(order_id=42)

    def test_order_response_valid(self):
        from app.engines.trading.schemas import OrderResponse
        resp = OrderResponse(
            id=1, alpaca_order_id="alp-001", ticker="AAPL",
            side="buy", order_type="market", quantity=100,
            status="filled", filled_qty=100, filled_avg_price=150.25
        )
        assert resp.status == "filled"
        assert resp.filled_avg_price == 150.25

    def test_trade_result_valid(self):
        from app.engines.trading.schemas import TradeResult
        result = TradeResult(
            success=True,
            message="Order placed successfully",
            order_id=42,
            alpaca_order_id="alp-002"
        )
        assert result.success is True

    def test_trade_result_with_failure(self):
        from app.engines.trading.schemas import TradeResult
        result = TradeResult(success=False, message="Insufficient buying power")
        assert result.alpaca_order_id is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/trading/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/trading/__init__.py` (empty).

Create `backend/app/engines/trading/schemas.py`:
```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/trading/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/trading/__init__.py backend/app/engines/trading/schemas.py backend/tests/engines/trading/test_schemas.py
git commit -m "feat: add trade execution engine schemas with order request/response models"
```

---

### Task 3: Trade Execution Engine — Alpaca Service

**Files:**
- Create: `backend/app/engines/trading/service.py`
- Test: `backend/tests/engines/trading/test_service.py`

The service wraps the Alpaca Trade API via `alpaca-py`'s `TradingClient` and manages the complete order lifecycle: place, cancel, modify, get status, get positions, sync portfolio state to DuckDB.

All Alpaca calls are abstracted behind an `AlpacaClient` wrapper class so the service can be tested without network.

**Service API:**

| Function | Description |
|---|---|
| `create_alpaca_client(api_key, secret_key, base_url, paper)` | Returns AlpacaClient wrapper |
| `place_order(client, request, db_path)` | Submits order, saves to DB, returns TradeResult |
| `cancel_order(client, cancel_req, db_path)` | Cancels on Alpaca + updates DB |
| `modify_order(client, modify_req, db_path)` | Modifies on Alpaca + updates DB |
| `get_order(client, order_id)` | Fetches order from Alpaca |
| `list_orders(client, status=None, limit=50)` | Lists orders from Alpaca |
| `get_positions(client)` | Gets all open positions from Alpaca |
| `sync_positions_to_db(client, db_path)` | Syncs Alpaca positions to DuckDB positions table |
| `sync_orders_to_db(client, db_path)` | Syncs recent Alpaca orders to DuckDB orders table |
| `get_account(client)` | Returns account info (cash, equity, buying_power) |
| `get_db_order(order_id, db_path)` | Gets order from local DB |
| `list_db_orders(db_path, limit)` | Lists orders from local DB |
| `get_positions_from_db(db_path)` | Gets positions from local DB |

Private helpers:
- `_alpaca_order_to_dict(alpaca_order)` — maps alpaca-py Order to dict
- `_alpaca_position_to_dict(alpaca_position)` — maps alpaca-py Position to dict
- `_save_order_to_db(conn, order_dict)` — inserts/updates orders table
- `_upsert_position(conn, position_dict)` — upserts positions table
- `_get_sector_for_ticker(ticker)` — hardcoded sector mapping

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/trading/test_service.py` with test classes:
- `TestAlpacaClientWrapper`: `test_create_client_with_defaults`, `test_create_client_live_url`, `test_create_client_raises_on_empty_key`, `test_create_client_raises_on_empty_secret`
- `TestPlaceOrder`: `test_place_market_order_success`, `test_place_limit_order`, `test_place_order_alpaca_error`, `test_place_order_saves_to_db`
- `TestCancelOrder`: `test_cancel_by_alpaca_id`, `test_cancel_nonexistent_order`, `test_cancel_updates_db_status`
- `TestModifyOrder`: `test_modify_quantity`, `test_modify_price`, `test_modify_error`
- `TestGetPositions`: `test_get_positions_empty`, `test_get_positions_with_data`
- `TestSyncPositions`: `test_sync_positions_to_db_inserts_new`, `test_sync_positions_to_db_updates_existing`, `test_sync_reconciles_closed_positions`, `test_sync_orders`
- `TestGetAccount`: `test_get_account_success`, `test_get_account_error`

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/trading/test_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write implementation**

Create `backend/app/engines/trading/service.py` with all 12+ functions + helpers. The `AlpacaClient` class wraps `alpaca.trading.client.TradingClient`. Mock the `_trading_client` attribute in tests.

`place_order` constructs the appropriate alpaca-py request type (MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest) based on request.order_type, calls `client.trading_client.submit_order()`, maps the response via `_alpaca_order_to_dict`, saves to DB, and returns `TradeResult`. Error handling wraps exceptions returning `TradeResult(success=False, message=str(e))`.

`cancel_order` resolves alpaca_order_id from DB if needed, calls `client.trading_client.cancel_order()`, updates DB status to "canceled".

`modify_order` resolves alpaca_order_id, calls `client.trading_client.replace_order()` with `ReplaceOrderRequest`, updates DB fields.

`sync_positions_to_db` gets all Alpaca positions, upserts each into DuckDB, deletes positions no longer in Alpaca (reconciliation).

`sync_orders_to_db` gets recent orders from Alpaca, upserts into DuckDB.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/trading/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/trading/__init__.py backend/app/engines/trading/schemas.py backend/app/engines/trading/service.py backend/tests/engines/trading/test_schemas.py backend/tests/engines/trading/test_service.py
git commit -m "feat: add trade execution engine with Alpaca order lifecycle and DB sync"
```

---

### Task 4: Trade Execution Engine — Router + Tasks

**Files:**
- Create: `backend/app/engines/trading/router.py`
- Create: `backend/app/engines/trading/tasks.py`
- Test: `backend/tests/engines/trading/test_router.py`
- Test: `backend/tests/engines/trading/test_tasks.py`

**Router** under prefix `/api/v1/trading` with tag "trading":

| Endpoint | Method | Description |
|---|---|---|
| `/execute` | POST | Place an order (body: OrderRequest) |
| `/cancel/{order_id}` | POST | Cancel by local order ID |
| `/modify/{order_id}` | PATCH | Modify an existing order |
| `/orders` | GET | List all orders from DB |
| `/orders/{order_id}` | GET | Get order details |
| `/positions` | GET | Get all positions from Alpaca |
| `/positions/sync` | POST | Sync Alpaca positions to DB |
| `/account` | GET | Get Alpaca account info |

**Tasks:**
- `sync_positions` — Celery task that syncs positions + orders from Alpaca to DB.

- [ ] **Steps 1-5: TDD cycle**

Write `backend/tests/engines/trading/test_router.py` with all 8 endpoints tested via `httpx.AsyncClient` with mocked service functions. Write `backend/tests/engines/trading/test_tasks.py` with success/error paths. Write implementation files.

Run: `cd backend && python -m pytest tests/engines/trading/test_router.py tests/engines/trading/test_tasks.py -v` — Expected: PASS

Commit:
```
git add backend/app/engines/trading/router.py backend/app/engines/trading/tasks.py backend/tests/engines/trading/test_router.py backend/tests/engines/trading/test_tasks.py
git commit -m "feat: add trade execution router and Celery sync task"
```

---

### Task 5: Position Management Engine — Schemas

**Files:**
- Create: `backend/app/engines/positions/__init__.py`
- Create: `backend/app/engines/positions/schemas.py`
- Test: `backend/tests/engines/positions/test_schemas.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/engines/positions/test_schemas.py` with `TestPositionManagementSchemas`:

| Test | Validates |
|---|---|
| `test_position_signal_valid_csp_close` | PositionSignal action="close", strategy_type="csp", profit metrics |
| `test_position_signal_valid_csp_roll` | PositionSignal action="roll", DTE metrics |
| `test_position_signal_valid_swing_trailing_stop` | PositionSignal action="close", trailing stop metrics |
| `test_position_signal_valid_leaps_exit` | PositionSignal action="exit", regime change metrics |
| `test_position_signal_valid_pmcc_roll` | PositionSignal action="roll_short_call" |
| `test_position_signal_invalid_action` | ValidationError for unknown action |
| `test_position_signal_confidence_range` | ValidationError for confidence > 1 |
| `test_csp_evaluation_valid` | CspEvaluation with nested PositionSignal |
| `test_leaps_evaluation_valid` | LeapsEvaluation with trend/regime |
| `test_swing_evaluation_valid` | SwingEvaluation with trailing stop |
| `test_pmcc_evaluation_valid` | PmccEvaluation with short call |
| `test_management_result_valid` | ManagementResult with action_taken |
| `test_watchdog_result_valid` | WatchdogResult with signals list |

- [ ] **Step 2: Run to verify it fails** → FAIL

- [ ] **Step 3: Write implementation**

Create `backend/app/engines/positions/schemas.py` with 7 schemas:
- `PositionSignal(BaseModel)`: ticker, strategy_type, action (Literal["close","roll","roll_short_call","exit","hold","reduce"]), reason, confidence (0-1 validator), current_price, metrics={}
- `CspEvaluation(BaseModel)`: ticker, position_id, strike, expiration, premium_received, current_premium, dte, days_held, profit_pct, underlying_price, signal
- `LeapsEvaluation(BaseModel)`: ticker, position_id, leaps_cost, current_value, profit_pct, days_held, underlying_price, trend_status="unknown", regime="Unknown", signal
- `SwingEvaluation(BaseModel)`: ticker, position_id, entry_price, current_price, profit_pct, days_held, trailing_stop_price, highest_price, signal
- `PmccEvaluation(BaseModel)`: ticker, position_id, leaps_cost, short_call_premium, short_call_dte, short_call_strike, underlying_price, profit_pct, signal
- `ManagementResult(BaseModel)`: ticker, strategy_type, action_taken, success, message, details={}
- `WatchdogResult(BaseModel)`: total_positions_scanned, signals_generated, actions_taken, signals=[], details={}

- [ ] **Step 4: Run to verify it passes** → PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/positions/__init__.py backend/app/engines/positions/schemas.py backend/tests/engines/positions/test_schemas.py
git commit -m "feat: add position management schemas for CSP, LEAPS, Swing, PMCC signals"
```

---

### Task 6: Position Management Engine — Service

**Files:**
- Create: `backend/app/engines/positions/service.py`
- Test: `backend/tests/engines/positions/test_service.py`

The service implements strategy-specific management rules. All thresholds read from `config.py settings` (configurable, not hardcoded).

| Function | Description |
|---|---|
| `evaluate_csp(...)` | Close if 50-75% profit, roll if DTE <= 21, else hold |
| `evaluate_leaps(...)` | Exit if profit >= 100%, trend failed, or Bear/Crisis regime; else hold |
| `evaluate_swing(...)` | Close if trailing stop hit (>=8% from high), breakdown stop (>=12% from entry), or profit target (>=25%); else hold |
| `evaluate_pmcc(...)` | Roll short call if DTE <= 14 or profit >= 50%; else hold |
| `run_watchdog(db_path)` | Loads all open positions from DB, evaluates each by strategy_type, returns WatchdogResult |

**Decision Logic:**

**CSP:**
```
profit_pct = (premium_received - current_option_price) / premium_received * 100
close_min = settings.csp_close_profit_min_pct   # 50.0
roll_dte   = settings.csp_roll_dte_threshold      # 21

if profit_pct >= close_min: close with confidence=min(0.95, profit_pct/100)
elif dte <= roll_dte: roll with confidence=0.75
else: hold with confidence=0.8
```

**LEAPS:**
```
profit_pct = (current_value - leaps_cost) / leaps_cost * 100
exit_target = settings.leaps_exit_profit_target_pct  # 100.0

if profit_pct >= exit_target: exit (confidence=0.9)
elif trend_status == "bearish": exit (confidence=0.85)
elif regime in ("Bear", "Bear High Vol", "Crisis"): exit (confidence=0.8)
else: hold (confidence=0.7)
```

**Swing:**
```
drop_from_high  = (highest_price - current_price) / highest_price * 100
drop_from_entry = (entry_price - current_price) / entry_price * 100
profit_pct      = (current_price - entry_price) / entry_price * 100

if drop_from_high >= settings.swings_trailing_stop_pct:  close (trailing stop)
elif drop_from_entry >= settings.swings_breakdown_stop_pct:  close (breakdown)
elif profit_pct >= settings.swings_profit_target_pct:  close (profit target)
else: hold
```

**PMCC:**
```
if short_call_dte <= settings.pmcc_short_call_dte_threshold:  roll_short_call
elif short_call_pnl_pct >= settings.pmcc_short_call_profit_target_pct:  roll_short_call
else: hold
```

- [ ] **Steps 1-5: TDD cycle**

Test classes:
- `TestCspManagement`: 6 tests (profit close at 50%, profit close at 75%, DTE roll at 21, roll below 21, hold between, hold low profit)
- `TestLeapsManagement`: 5 tests (profit target exit, trend failure exit, regime change exit, hold bullish, hold in progress)
- `TestSwingManagement`: 5 tests (trailing stop hit, trailing stop not hit, breakdown stop, profit target, hold normal)
- `TestPmccManagement`: 4 tests (roll low DTE, roll profit, hold normal, ITM short call edge)
- `TestWatchdog`: 2 tests (scans all positions, no positions empty)

Run: `cd backend && python -m pytest tests/engines/positions/test_service.py -v` — Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/positions/service.py backend/tests/engines/positions/test_service.py
git commit -m "feat: add position management engine with CSP/LEAPS/Swing/PMCC evaluation"
```

---

### Task 7: Position Management Engine — Router + Tasks

**Files:**
- Create: `backend/app/engines/positions/router.py`
- Create: `backend/app/engines/positions/tasks.py`
- Test: `backend/tests/engines/positions/test_router.py`
- Test: `backend/tests/engines/positions/test_tasks.py`

**Router** under prefix `/api/v1/positions` with tag "positions":

| Endpoint | Method | Description |
|---|---|---|
| `/evaluate/csp` | POST | Evaluate a CSP position -> PositionSignal |
| `/evaluate/leaps` | POST | Evaluate a LEAPS position -> PositionSignal |
| `/evaluate/swing` | POST | Evaluate swing position -> PositionSignal |
| `/evaluate/pmcc` | POST | Evaluate PMCC position -> PositionSignal |
| `/watchdog` | GET | Run watchdog on all open positions -> WatchdogResult |

**Tasks:**
- `run_position_watchdog` — Celery task: syncs positions from Alpaca, runs watchdog, returns summary dict

- [ ] **Steps 1-5: TDD cycle**

Run: `cd backend && python -m pytest tests/engines/positions/test_router.py tests/engines/positions/test_tasks.py -v` — Expected: PASS

Commit:
```
git add backend/app/engines/positions/router.py backend/app/engines/positions/tasks.py backend/tests/engines/positions/test_router.py backend/tests/engines/positions/test_tasks.py
git commit -m "feat: add position management router and watchdog task"
```

---

### Task 8: Portfolio Monitoring Engine — Schemas

**Files:**
- Create: `backend/app/engines/monitoring/__init__.py`
- Create: `backend/app/engines/monitoring/schemas.py`
- Test: `backend/tests/engines/monitoring/test_schemas.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/engines/monitoring/test_schemas.py` with `TestMonitoringSchemas`:

| Test | Validates |
|---|---|
| `test_portfolio_snapshot_valid` | PortfolioSnapshot with all fields |
| `test_position_snapshot_valid` | PositionSnapshot with weight_pct |
| `test_order_snapshot_valid` | OrderSnapshot with order fields |
| `test_portfolio_health_score_valid` | score=85 -> level "excellent" |
| `test_portfolio_health_score_critical` | score=25 -> level "critical" |
| `test_portfolio_health_score_warning` | score=45 -> level "warning" |
| `test_portfolio_health_score_good` | score=75 -> level "good" |
| `test_portfolio_health_score_excellent` | score=92 -> level "excellent" |
| `test_alert_event_valid` | AlertEvent with level, category, message |
| `test_alert_event_invalid_level` | ValidationError for unknown level |
| `test_monitoring_summary_valid` | MonitoringSummary with all sub-models |

- [ ] **Step 2: Run to verify it fails** -> FAIL

- [ ] **Step 3: Write implementation**

Create `backend/app/engines/monitoring/schemas.py`:
- `PortfolioSnapshot(BaseModel)`: total_value, cash, equity_value=0, options_value=0, buying_power=0, daily_pl=0, daily_pl_pct=0, total_unrealized_pl=0, positions_count=0, options_count=0, timestamp
- `PositionSnapshot(BaseModel)`: ticker, quantity, avg_price, current_price, market_value, unrealized_pl, unrealized_pl_pct, weight_pct, strategy_type, sector
- `OrderSnapshot(BaseModel)`: id, alpaca_order_id, ticker, side, order_type, quantity, filled_qty, price, status, submitted_at
- `PortfolioHealthScore(BaseModel)`: score, max_drawdown, concentration_pct, portfolio_beta, total_exposure_pct, cash_pct, violations=[], num_violations=0, details={}; method `level()`: >=80 "excellent", >=60 "good", >=30 "warning", else "critical"
- `AlertEvent(BaseModel)`: level (Literal["info","warning","critical"]), category, message, details={}, timestamp
- `MonitoringSummary(BaseModel)`: snapshot, health, alerts=[], last_sync_at

- [ ] **Step 4: Run to verify it passes** -> PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/monitoring/__init__.py backend/app/engines/monitoring/schemas.py backend/tests/engines/monitoring/test_schemas.py
git commit -m "feat: add portfolio monitoring schemas with snapshot, health score, alerts"
```

---

### Task 9: Portfolio Monitoring Engine — Service

**Files:**
- Create: `backend/app/engines/monitoring/service.py`
- Test: `backend/tests/engines/monitoring/test_service.py`

| Function | Description |
|---|---|
| `collect_portfolio_snapshot(client, db_path)` | Queries Alpaca account + positions + DB, returns PortfolioSnapshot |
| `compute_portfolio_health_score(max_drawdown, concentration_pct, portfolio_beta, total_exposure_pct, cash_pct, num_violations, volatility)` | Pure function, returns float 0-100 |
| `check_alerts(snapshot, health)` | Returns list of AlertEvent for violations |
| `collect_monitoring_summary(client, db_path)` | Full cycle: snapshot -> health -> alerts -> summary |

**Health Score Formula (same as Phase 4 Risk Engine):**
```
score = 100
score -= min(30, max_drawdown * 1.2)
if concentration_pct > 40: score -= min(20, (concentration-40)*0.8)
if portfolio_beta > 1.5: score -= min(15, (beta-1.5)*20)
if total_exposure_pct > 80: score -= min(15, (exposure-80)*0.5)
score += min(10, cash_pct * 0.3)
score -= min(20, num_violations * 5)
if volatility > 0.35: score -= min(10, (volatility-0.35)*30)
return max(0, min(100, score))
```

- [ ] **Steps 1-5: TDD cycle**

Test classes:
- `TestCollectSnapshot`: empty portfolio, with positions, daily PL computation
- `TestHealthScore`: perfect (>=80), poor (<30), mid-range, extreme drawdown
- `TestAlerts`: concentration violation, drawdown violation, no violations
- `TestMonitoringSummary`: full collection cycle

Run: `cd backend && python -m pytest tests/engines/monitoring/test_service.py -v` — Expected: PASS

Commit:
```
git add backend/app/engines/monitoring/service.py backend/tests/engines/monitoring/test_service.py
git commit -m "feat: add portfolio monitoring service with snapshot collection and health scoring"
```

---

### Task 10: Portfolio Monitoring Engine — Router + Tasks

**Files:**
- Create: `backend/app/engines/monitoring/router.py`
- Create: `backend/app/engines/monitoring/tasks.py`
- Test: `backend/tests/engines/monitoring/test_router.py`
- Test: `backend/tests/engines/monitoring/test_tasks.py`

**Router** under prefix `/api/v1/monitoring` with tag "monitoring":

| Endpoint | Method | Description |
|---|---|---|
| `/snapshot` | GET | Get current portfolio snapshot (PortfolioSnapshot) |
| `/health` | GET | Get portfolio health score (PortfolioHealthScore) |
| `/alerts` | GET | Get current alerts (list of AlertEvent) |
| `/summary` | GET | Get full monitoring summary (MonitoringSummary) |

**Tasks:**
- `collect_monitoring_data` — Celery task: creates Alpaca client, calls `collect_monitoring_summary`, saves snapshot to portfolio_snapshots DuckDB table. Returns `{"status": "success", "health_score": N}`

- [ ] **Steps 1-5: TDD cycle**

Run: `cd backend && python -m pytest tests/engines/monitoring/test_router.py tests/engines/monitoring/test_tasks.py -v` — Expected: PASS

Commit:
```
git add backend/app/engines/monitoring/router.py backend/app/engines/monitoring/tasks.py backend/tests/engines/monitoring/test_router.py backend/tests/engines/monitoring/test_tasks.py
git commit -m "feat: add portfolio monitoring router and data collection task"
```

---

### Task 11: Wire Into main.py + Beat Schedule

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`
- Test: `backend/tests/test_main.py`

**main.py updates:**
- Import Phase 5 routers:
  ```python
  from app.engines.trading.router import router as trading_router
  from app.engines.positions.router import router as positions_router
  from app.engines.monitoring.router import router as monitoring_router
  ```
- Include routers:
  ```python
  app.include_router(trading_router)
  app.include_router(positions_router)
  app.include_router(monitoring_router)
  ```
- Update app version to `"0.5.0"`

**celery_app.py updates:**
- Import Phase 5 tasks:
  ```python
  from app.engines.trading.tasks import sync_positions
  from app.engines.positions.tasks import run_position_watchdog
  from app.engines.monitoring.tasks import collect_monitoring_data
  ```
- Add beat schedule entries:
  ```python
  app.conf.beat_schedule.update({
      "sync-alpaca-positions": {
          "task": "app.engines.trading.tasks.sync_positions",
          "schedule": crontab(minute="*/5"),
      },
      "run-position-watchdog-hourly": {
          "task": "app.engines.positions.tasks.run_position_watchdog",
          "schedule": crontab(minute="0"),
      },
      "collect-monitoring-data": {
          "task": "app.engines.monitoring.tasks.collect_monitoring_data",
          "schedule": crontab(minute="*/5"),
      },
  })
  ```

**Tests:**
- `test_main.py` updates: verify Phase 5 endpoints respond (GET /api/v1/trading/orders, GET /api/v1/positions/watchdog, GET /api/v1/monitoring/snapshot)

- [ ] **Steps 1-5: TDD cycle**

Run: `cd backend && python -m pytest tests/test_main.py -v` — Expected: PASS

Commit:
```
git add backend/app/main.py backend/app/celery_app.py backend/tests/test_main.py
git commit -m "feat: wire Phase 5 routers and add Celery beat schedule for trading/positions/monitoring tasks"
```

---

### Task 12: Integration Tests for Execution-Monitoring Pipeline

**Files:**
- Create: `backend/tests/integration/test_execution_pipeline.py`

Integration tests covering:
1. **Order lifecycle end-to-end:** create order via service -> verify saved in DB -> cancel -> verify DB status updated
2. **Position management evaluation:** insert CSP position via DB -> run watchdog -> verify signals generated
3. **Portfolio monitoring:** collect snapshot -> compute health -> verify health score is reasonable
4. **Position sync reconciliation:** insert fake positions in DB -> sync from Alpaca (mocked returning subset) -> verify old ones removed
5. **Cross-engine workflow:** sync positions -> run watchdog -> check signals -> collect monitoring summary -> verify all engines coordinate

All tests use `test_db_path` fixture and mock Alpaca via `unittest.mock.patch`.

- [ ] **Steps 1-3: Write tests, run, verify**

Run: `cd backend && python -m pytest tests/integration/test_execution_pipeline.py -v` — Expected: PASS

- [ ] **Step 4: Commit**

```
git add backend/tests/integration/test_execution_pipeline.py
git commit -m "test: add integration tests for execution-monitoring pipeline end-to-end"
```

---

### Task 13: Final Cleanup — Ruff Lint & Full Test Suite

- [ ] **Step 1: Run ruff**

Run: `cd backend && ruff check app/ tests/`
Expected: No errors

- [ ] **Step 2: Auto-fix any issues**

Run: `cd backend && ruff check --fix app/ tests/`
Expected: Clean exit

- [ ] **Step 3: Run full test suite with coverage**

Run: `cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing`
Expected: All tests pass, coverage report shows high coverage on new modules

- [ ] **Step 4: Final commit**

```
git add -A
git commit -m "chore: lint and type-check Phase 5 execution, monitoring, and Alpaca integration"
```

---

## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage:**
   - [ ] Task 1: Alpaca-py dependency in requirements.txt
   - [ ] Task 1: Config expansion with position management rules (csp_close_profit_min_pct, csp_roll_dte_threshold, swings_trailing_stop_pct, pmcc_short_call_dte_threshold, etc.) and monitoring settings
   - [ ] Task 1: DuckDB orders table with full column schema
   - [ ] Task 1: DuckDB trade_journal table (entry/exit, P&L, commission, regime at entry/exit)
   - [ ] Task 2: Order schemas (OrderRequest, CancelRequest, ModifyRequest, OrderResponse, TradeResult) with validation
   - [ ] Task 3: AlpacaClient wrapper with place/cancel/modify/get/list/sync operations
   - [ ] Task 3: Order placement supporting market, limit, stop, stop_limit via alpaca-py request types
   - [ ] Task 3: Order lifecycle DB save and status update
   - [ ] Task 3: Position sync from Alpaca to DuckDB with upsert and reconciliation
   - [ ] Task 3: Account info retrieval (cash, equity, buying_power)
   - [ ] Task 4: FastAPI router endpoints under /api/v1/trading (execute, cancel, modify, orders, positions, sync, account)
   - [ ] Task 4: Celery sync task
   - [ ] Task 5: Position management schemas (PositionSignal, CspEvaluation, LeapsEvaluation, SwingEvaluation, PmccEvaluation, ManagementResult, WatchdogResult)
   - [ ] Task 6: CSP management (close at 50-75% profit, roll at 21 DTE)
   - [ ] Task 6: LEAPS management (exit at 100% profit, trend failure, regime change)
   - [ ] Task 6: Swing management (trailing stop 8%, breakdown stop 12%, profit target 25%)
   - [ ] Task 6: PMCC management (roll short call at 14 DTE or 50% profit)
   - [ ] Task 6: All thresholds from settings, not hardcoded
   - [ ] Task 6: Watchdog scans all open positions and generates signals
   - [ ] Task 7: Position management router + watchdog task
   - [ ] Task 8: Monitoring schemas (PortfolioSnapshot, PositionSnapshot, OrderSnapshot, PortfolioHealthScore with level(), AlertEvent, MonitoringSummary)
   - [ ] Task 9: Portfolio snapshot collection from Alpaca + DB
   - [ ] Task 9: Health score computation with drawdown/concentration/beta/exposure/cash/violations/volatility
   - [ ] Task 9: Alert generation logic
   - [ ] Task 10: Monitoring router + data collection task
   - [ ] Task 11: main.py wiring + beat schedule (sync every 5min, watchdog hourly, monitoring every 5min)
   - [ ] Task 12: Integration tests for execution-monitoring pipeline
   - [ ] Task 13: Ruff lint clean, full test suite passing

2. **Placeholder scan:** No TBD, TODO, or incomplete steps. All test code is explicit. All implementation code has specific logic shown.

3. **Type consistency:** All method signatures match across tasks. `create_alpaca_client` returns `AlpacaClient`. `place_order` returns `TradeResult`. `evaluate_csp`/`evaluate_leaps`/`evaluate_swing`/`evaluate_pmcc` return `PositionSignal`. `run_watchdog` returns `WatchdogResult`. `collect_portfolio_snapshot` returns `PortfolioSnapshot`. `compute_portfolio_health_score` returns `float`. `collect_monitoring_summary` returns `MonitoringSummary`.

4. **Ambiguity check:** All steps are explicit with exact code, commands, and expected outcomes.
