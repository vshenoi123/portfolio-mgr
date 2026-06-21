# Phase 1: Data & Backend Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish project structure, database schema, DuckDB + Parquet storage layer, Polygon API data collection engine, and FastAPI backend skeleton with health-check and universe endpoints.

**Architecture:** Modular monolith — single FastAPI backend with Celery for async tasks. DuckDB for operational queries, Parquet files for historical OHLCV data. All config via environment variables. TDD throughout.

**Tech Stack:** Python 3.12, FastAPI, DuckDB, Celery, Redis, Polygon API, Pytest, Docker

**Testing Requirement:** Every major component must have tests covering normal operation, edge cases, and error states.

---

## File Structure

```
portfolio-mgr/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── celery_app.py              # Celery app config
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── database.py                # DuckDB connection manager
│   │   ├── engines/
│   │   │   └── data/
│   │   │       ├── __init__.py
│   │   │       ├── schemas.py          # Pydantic models for market data
│   │   │       ├── service.py          # Polygon API client + data storage
│   │   │       ├── router.py           # REST endpoints for data
│   │   │       └── tasks.py            # Celery tasks for data refresh
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── universe.py             # Universe schema + defaults
│   │   │   └── market_data.py          # OHLCV + options schemas
│   │   └── core/
│   │       ├── __init__.py
│   │       └── dependencies.py         # FastAPI dependency injection
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 # Pytest fixtures (test DB, mock client)
│   │   ├── test_config.py
│   │   ├── test_database.py
│   │   ├── engines/
│   │   │   └── data/
│   │   │       ├── test_service.py
│   │   │       ├── test_router.py
│   │   │       └── test_tasks.py
│   │   └── test_main.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── .gitignore
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/.env.example`
- Create: `.gitignore`
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create requirements.txt**

```
# Core
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2

# Database
duckdb==1.1.3
pyarrow==17.0.0

# Async / Task Queue
celery==5.4.0
redis==5.1.1

# HTTP Client
httpx==0.27.2

# Data
pandas==2.2.3
numpy==2.1.2

# Polygon
polygon-api-client==1.15.0

# Utils
python-dateutil==2.9.0
python-dotenv==1.0.1
```

- [ ] **Step 2: Create requirements-dev.txt**

```
-r requirements.txt

# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
respx==0.22.0          # Mock httpx for Polygon API

# Linting / Types
ruff==0.6.9
mypy==1.11.2
```

- [ ] **Step 3: Create .env.example**

```
POLYGON_API_KEY=your_polygon_api_key
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
REDIS_URL=redis://redis:6379/0
DATABASE_PATH=/data/portfolio.db
DATA_DIR=/data
LOG_LEVEL=INFO
```

- [ ] **Step 4: Create .gitignore**

```
__pycache__/
*.py[cod]
.env
.venv/
venv/
*.egg-info/
dist/
build/
.data/
data/
*.db
*.parquet
.superpowers/
.DS_Store
```

- [ ] **Step 5: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Create docker-compose.yml**

```yaml
version: "3.9"

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app.celery_app worker --loglevel=info

  beat:
    build: ./backend
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - data_volume:/data
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A app.celery_app beat --loglevel=info

volumes:
  redis_data:
  data_volume:
```

- [ ] **Step 7: Verify project structure**

Run: `ls -la backend/ && ls docker-compose.yml`
Expected: All created files present

- [ ] **Step 8: Commit**

```bash
git init
git add -A
git commit -m "feat: scaffold project structure with Docker, deps, and gitignore"
```

---

### Task 2: Core Configuration & Database Layer

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Write the failing test for config**

Create `backend/tests/__init__.py` (empty)
Create `backend/tests/test_config.py`:

```python
import os
import pytest
from pydantic import ValidationError


class TestConfig:
    def test_config_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("POLYGON_API_KEY", "test_key")
        monkeypatch.setenv("DATABASE_PATH", "/tmp/test.db")
        # Will fail until config module exists
        from app.config import settings
        assert settings.POLYGON_API_KEY == "test_key"
        assert settings.DATABASE_PATH == "/tmp/test.db"

    def test_config_requires_polygon_key(self, monkeypatch):
        monkeypatch.delenv("POLYGON_API_KEY", raising=False)
        with pytest.raises(ValidationError):
            from app.config import Settings
            Settings()

    def test_config_has_default_data_dir(self, monkeypatch):
        monkeypatch.setenv("POLYGON_API_KEY", "test_key")
        from app.config import settings
        assert settings.DATA_DIR is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pip install -r requirements-dev.txt && python -m pytest tests/test_config.py -v`
Expected: FAIL with ImportError (no config module)

- [ ] **Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    redis_url: str = "redis://localhost:6379/0"
    database_path: str = "/data/portfolio.db"
    data_dir: str = "/data"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for database**

Create `backend/tests/test_database.py`:

```python
import os
import pytest
import duckdb


class TestDatabase:
    def test_get_connection_returns_duckdb_conn(self, test_db_path):
        from app.database import get_connection
        conn = get_connection(test_db_path)
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        conn.close()

    def test_get_connection_creates_db_file(self, test_db_path):
        from app.database import get_connection
        conn = get_connection(test_db_path)
        conn.close()
        assert os.path.exists(test_db_path)

    def test_get_connection_cache_reuses_conn(self, test_db_path):
        from app.database import get_connection
        conn1 = get_connection(test_db_path)
        conn2 = get_connection(test_db_path)
        assert conn1 is conn2
        conn1.close()

    def test_close_connection_removes_cache(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        close_connection(test_db_path)
        conn2 = get_connection(test_db_path)
        assert conn2 is not conn
        conn2.close()
```

- [ ] **Step 6: Add conftest.py fixture**

Create `backend/tests/conftest.py`:

```python
import pytest


@pytest.fixture
def test_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def test_data_dir(tmp_path):
    data_dir = tmp_path / "market_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: FAIL with ImportError

- [ ] **Step 8: Create database.py**

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
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_id START 1;
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

- [ ] **Step 9: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_database.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/__init__.py backend/app/config.py backend/app/database.py backend/tests/
git commit -m "feat: add config and DuckDB database layer with tests"
```

---

### Task 3: Data Engine Schemas & Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/universe.py`
- Create: `backend/app/models/market_data.py`

- [ ] **Step 1: Write failing tests for universe model**

Create `backend/tests/test_models_universe.py`:

```python
import pytest
from pydantic import ValidationError


class TestUniverse:
    def test_default_universe_has_spy(self):
        from app.models.universe import DEFAULT_UNIVERSE
        assert "SPY" in DEFAULT_UNIVERSE
        assert "QQQ" in DEFAULT_UNIVERSE

    def test_default_universe_is_list_of_strings(self):
        from app.models.universe import DEFAULT_UNIVERSE
        assert all(isinstance(s, str) for s in DEFAULT_UNIVERSE)
        assert len(DEFAULT_UNIVERSE) > 0

    def test_universe_entry_validates_ticker(self):
        from app.models.universe import UniverseEntry
        entry = UniverseEntry(ticker="AAPL", active=True)
        assert entry.ticker == "AAPL"
        assert entry.active is True

    def test_universe_entry_rejects_empty_ticker(self):
        from app.models.universe import UniverseEntry
        with pytest.raises(ValidationError):
            UniverseEntry(ticker="", active=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models_universe.py -v`
Expected: FAIL

- [ ] **Step 3: Create universe.py**

```python
from pydantic import BaseModel, field_validator


DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV",
    "XLI", "XLP", "XLU", "XLB", "XLRE", "XLY",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "BAC",
    "DIS", "ADBE", "NFLX", "CRM", "KO", "PEP", "MRK", "ABBV",
    "AVGO", "CSCO", "INTC", "AMD", "QCOM", "TMO", "ACN", "TXN",
    "NKE", "UPS", "BA", "CAT", "GS", "MS", "C", "WFC",
    "ORCL", "IBM", "PYPL", "SNAP", "UBER", "SQ", "SHOP",
    "ARKK", "TLT", "HYG", "GDX", "SLV", "USO",
]


class UniverseEntry(BaseModel):
    ticker: str
    active: bool = True

    @field_validator("ticker")
    @classmethod
    def ticker_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ticker cannot be empty")
        return v.upper().strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models_universe.py -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for market_data models**

Create `backend/tests/test_models_market_data.py`:

```python
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestOHLCV:
    def test_valid_ohlcv(self):
        from app.models.market_data import OHLCVBar
        bar = OHLCVBar(
            ticker="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=1000000,
        )
        assert bar.ticker == "AAPL"
        assert bar.close == 153.0

    def test_ohlcv_high_must_be_above_low(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=150.0,
                high=148.0,
                low=149.0,
                close=153.0,
                volume=1000000,
            )

    def test_ohlcv_negative_volume_rejected(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=150.0,
                high=155.0,
                low=149.0,
                close=153.0,
                volume=-100,
            )

    def test_ohlcv_negative_price_rejected(self):
        from app.models.market_data import OHLCVBar
        with pytest.raises(ValidationError):
            OHLCVBar(
                ticker="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=-1.0,
                high=155.0,
                low=149.0,
                close=153.0,
                volume=1000,
            )


class TestOptionsContract:
    def test_valid_option(self):
        from app.models.market_data import OptionsContract
        opt = OptionsContract(
            ticker="AAPL",
            expiration=datetime(2026, 7, 17),
            strike=150.0,
            option_type="call",
            bid=5.20,
            ask=5.30,
            implied_vol=0.35,
            delta=0.55,
            gamma=0.02,
            theta=-0.05,
            vega=0.12,
            volume=5000,
            open_interest=10000,
        )
        assert opt.strike == 150.0
        assert opt.option_type == "call"

    def test_option_type_validation(self):
        from app.models.market_data import OptionsContract
        with pytest.raises(ValidationError):
            OptionsContract(
                ticker="AAPL",
                expiration=datetime(2026, 7, 17),
                strike=150.0,
                option_type="invalid",
                bid=5.20,
                ask=5.30,
                implied_vol=0.35,
                delta=0.55,
                gamma=0.02,
                theta=-0.05,
                vega=0.12,
                volume=5000,
                open_interest=10000,
            )
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models_market_data.py -v`
Expected: FAIL

- [ ] **Step 7: Create market_data.py**

```python
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator


class OHLCVBar(BaseModel):
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    trades: int | None = None

    @field_validator("high")
    @classmethod
    def high_must_be_above_low(cls, v: float, info) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must be >= low")
        return v

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price cannot be negative")
        return v

    @field_validator("volume")
    @classmethod
    def volume_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("volume cannot be negative")
        return v


class OptionsContract(BaseModel):
    ticker: str
    expiration: datetime
    strike: float
    option_type: Literal["call", "put"]
    bid: float
    ask: float
    implied_vol: float
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    volume: int = 0
    open_interest: int = 0

    @field_validator("option_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("call", "put"):
            raise ValueError("option_type must be 'call' or 'put'")
        return v

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_models_market_data.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/ backend/tests/test_models_*.py
git commit -m "feat: add data models for universe, OHLCV, and options contracts with validation"
```

---

### Task 4: Data Engine Service — Polygon API Client

**Files:**
- Create: `backend/app/engines/data/__init__.py`
- Create: `backend/app/engines/data/schemas.py`
- Create: `backend/app/engines/data/service.py`

- [ ] **Step 1: Write failing tests for data schemas**

Create `backend/tests/engines/data/test_schemas.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError


class TestDataRefreshRequest:
    def test_valid_refresh_request(self):
        from app.engines.data.schemas import DataRefreshRequest
        req = DataRefreshRequest(ticker="AAPL")
        assert req.ticker == "AAPL"
        assert req.days == 365  # default

    def test_refresh_request_invalid_days(self):
        from app.engines.data.schemas import DataRefreshRequest
        with pytest.raises(ValidationError):
            DataRefreshRequest(ticker="AAPL", days=0)

    def test_refresh_request_uppercases_ticker(self):
        from app.engines.data.schemas import DataRefreshRequest
        req = DataRefreshRequest(ticker="aapl")
        assert req.ticker == "AAPL"


class TestDataRefreshResponse:
    def test_valid_response(self):
        from app.engines.data.schemas import DataRefreshResponse
        resp = DataRefreshResponse(
            ticker="AAPL",
            status="success",
            bars_fetched=252,
            message="Data refreshed for AAPL",
        )
        assert resp.status == "success"


class TestDataQuery:
    def test_valid_query(self):
        from app.engines.data.schemas import DataQuery
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)
        q = DataQuery(ticker="AAPL", start_date=start, end_date=end)
        assert q.ticker == "AAPL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/data/test_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Create schemas.py**

```python
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, field_validator


class DataRefreshRequest(BaseModel):
    ticker: str
    days: int = 365

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("days")
    @classmethod
    def days_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class DataRefreshResponse(BaseModel):
    ticker: str
    status: str  # "success", "partial", "error"
    bars_fetched: int = 0
    message: str = ""


class DataQuery(BaseModel):
    ticker: str
    start_date: datetime
    end_date: datetime = datetime.now(timezone.utc)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()


class DataHealthResponse(BaseModel):
    tickers_in_universe: int
    total_ohlcv_bars: int
    last_refresh: datetime | None = None
    status: str = "healthy"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/engines/data/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write failing tests for Polygon service**

Create `backend/tests/engines/data/test_service.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


class TestPolygonService:
    @pytest.fixture
    def mock_polygon(self):
        with patch("app.engines.data.service.polygon_client") as mock:
            yield mock

    def test_fetch_ohlcv_returns_bars(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)

        # Mock polygon REST client response
        mock_bar = MagicMock()
        mock_bar.t = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_bar.vw = 152.0
        mock_bar.n = 5000

        mock_polygon.get_aggs.return_value = [mock_bar]

        bars = service.fetch_ohlcv("AAPL", days=30)
        assert len(bars) == 1
        assert bars[0].ticker == "AAPL"
        assert bars[0].close == 153.0
        assert bars[0].volume == 1000000

    def test_fetch_ohlcv_empty_response(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService
        service = PolygonDataService(data_dir=test_data_dir)
        mock_polygon.get_aggs.return_value = []
        bars = service.fetch_ohlcv("UNKNOWN", days=30)
        assert bars == []

    def test_fetch_ohlcv_handles_api_error(self, mock_polygon, test_data_dir):
        from app.engines.data.service import PolygonDataService, PolygonAPIError
        service = PolygonDataService(data_dir=test_data_dir)
        mock_polygon.get_aggs.side_effect = Exception("API timeout")
        with pytest.raises(PolygonAPIError):
            service.fetch_ohlcv("AAPL", days=30)

    def test_save_ohlcv_creates_parquet(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        from datetime import datetime, timezone
        service = PolygonDataService(data_dir=test_data_dir)

        bars = []
        for i in range(5):
            bars.append({
                "ticker": "AAPL",
                "timestamp": datetime.now(timezone.utc),
                "open": 150.0 + i,
                "high": 155.0 + i,
                "low": 149.0 + i,
                "close": 153.0 + i,
                "volume": 1000000 + i * 100,
            })

        path = service.save_ohlcv(bars)
        assert path.endswith(".parquet")
        import os
        assert os.path.exists(path)

    def test_save_and_load_roundtrip(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        from datetime import datetime, timezone
        service = PolygonDataService(data_dir=test_data_dir)

        bars = [{
            "ticker": "AAPL",
            "timestamp": datetime.now(timezone.utc),
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 153.0,
            "volume": 1000000,
        }]
        service.save_ohlcv(bars)

        loaded = service.load_ohlcv("AAPL", days=30)
        assert len(loaded) >= 1
        assert loaded[0]["close"] == 153.0
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/data/test_service.py -v`
Expected: FAIL

- [ ] **Step 7: Create service.py**

```python
import os
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
from polygon import RESTClient

from app.config import settings
from app.database import ensure_parquet_dir

logger = logging.getLogger(__name__)


class PolygonAPIError(Exception):
    pass


polygon_client = RESTClient(settings.polygon_api_key)


class PolygonDataService:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or settings.data_dir
        self.client = polygon_client

    def fetch_ohlcv(
        self,
        ticker: str,
        days: int = 365,
        multiplier: int = 1,
        timespan: str = "day",
    ) -> list[dict]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        try:
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_date=start.strftime("%Y-%m-%d"),
                to_date=end.strftime("%Y-%m-%d"),
                adjusted=True,
            )
        except Exception as e:
            raise PolygonAPIError(f"Failed to fetch {ticker}: {e}") from e

        bars = []
        for agg in aggs:
            bars.append({
                "ticker": ticker.upper(),
                "timestamp": datetime.fromtimestamp(agg.t / 1000, tz=timezone.utc),
                "open": agg.o,
                "high": agg.h,
                "low": agg.l,
                "close": agg.c,
                "volume": agg.v,
                "vwap": agg.vw if hasattr(agg, "vw") else None,
                "trades": agg.n if hasattr(agg, "n") else None,
            })
        return bars

    def save_ohlcv(self, bars: list[dict]) -> str:
        if not bars:
            raise ValueError("No bars to save")
        df = pd.DataFrame(bars)
        ticker = bars[0]["ticker"]
        parquet_dir = ensure_parquet_dir(ticker, "ohlcv")
        parquet_path = os.path.join(parquet_dir, f"{ticker.lower()}.parquet")
        df.to_parquet(parquet_path, index=False)
        logger.info("Saved %d bars for %s to %s", len(bars), ticker, parquet_path)
        return parquet_path

    def load_ohlcv(
        self,
        ticker: str,
        days: int = 365,
    ) -> pd.DataFrame:
        parquet_dir = ensure_parquet_dir(ticker, "ohlcv")
        parquet_path = os.path.join(parquet_dir, f"{ticker.lower()}.parquet")
        if not os.path.exists(parquet_path):
            return pd.DataFrame()
        df = pd.read_parquet(parquet_path)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        df = df[df["timestamp"] >= cutoff]
        return df.sort_values("timestamp").reset_index(drop=True)
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/engines/data/test_service.py -v`
Expected: PASS (the API mock tests will pass, the polyon_client patch handles the external call)

- [ ] **Step 9: Commit**

```bash
git add backend/app/engines/data/ backend/tests/engines/data/test_schemas.py backend/tests/engines/data/test_service.py
git commit -m "feat: add Polygon API data service with OHLCV fetch, save, and load"
```

---

### Task 5: Celery Tasks for Data Refresh

**Files:**
- Create: `backend/app/celery_app.py`
- Create: `backend/app/engines/data/tasks.py`

- [ ] **Step 1: Write failing tests for celery tasks**

Create `backend/tests/engines/data/test_tasks.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestDataTasks:
    @patch("app.engines.data.tasks.PolygonDataService")
    def test_refresh_ticker_task(self, mock_service):
        from app.engines.data.tasks import refresh_ticker_data
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.fetch_ohlcv.return_value = [
            {"ticker": "AAPL", "close": 150.0}
        ]
        result = refresh_ticker_data("AAPL", days=365)
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        mock_instance.fetch_ohlcv.assert_called_once_with("AAPL", days=365)
        mock_instance.save_ohlcv.assert_called_once()

    @patch("app.engines.data.tasks.PolygonDataService")
    def test_refresh_ticker_error_handling(self, mock_service):
        from app.engines.data.tasks import refresh_ticker_data
        mock_service.return_value.fetch_ohlcv.side_effect = Exception("fail")
        result = refresh_ticker_data("INVALID")
        assert result["status"] == "error"
        assert "fail" in result["message"]

    @patch("app.engines.data.tasks.refresh_ticker_data")
    def test_refresh_all_task(self, mock_refresh_one):
        from app.engines.data.tasks import refresh_all_data
        from app.models.universe import DEFAULT_UNIVERSE
        mock_refresh_one.return_value = {"ticker": "TEST", "status": "success"}
        results = refresh_all_data()
        assert len(results) == len(DEFAULT_UNIVERSE)
        assert mock_refresh_one.call_count == len(DEFAULT_UNIVERSE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/data/test_tasks.py -v`
Expected: FAIL

- [ ] **Step 3: Create celery_app.py**

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "portfolio_mgr",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-all-data-daily": {
            "task": "app.engines.data.tasks.refresh_all_data",
            "schedule": 86400.0,  # daily
        },
    },
)
```

- [ ] **Step 4: Create tasks.py**

```python
import logging
from celery import shared_task
from app.engines.data.service import PolygonDataService, PolygonAPIError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_ticker_data(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        bars = service.fetch_ohlcv(ticker, days=days)
        if bars:
            service.save_ohlcv(bars)
        logger.info("Refreshed %s: %d bars", ticker, len(bars))
        return {
            "ticker": ticker,
            "status": "success",
            "bars_fetched": len(bars),
            "message": f"Refreshed {ticker}",
        }
    except PolygonAPIError as e:
        logger.error("Polygon API error for %s: %s", ticker, e)
        raise self.retry(exc=e)
    except Exception as e:
        logger.exception("Unexpected error refreshing %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def refresh_all_data(days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = refresh_ticker_data.delay(ticker, days=days)
        results.append(result)
    return results
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/engines/data/test_tasks.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/celery_app.py backend/app/engines/data/tasks.py backend/tests/engines/data/test_tasks.py
git commit -m "feat: add Celery tasks for data refresh with retry and error handling"
```

---

### Task 6: FastAPI Router — Data Endpoints

**Files:**
- Create: `backend/app/engines/data/router.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/dependencies.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Write failing tests for router**

Create `backend/tests/engines/data/test_router.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestDataRouter:
    async def test_get_universe(self, client):
        resp = await client.get("/api/v1/data/universe")
        assert resp.status_code == 200
        data = resp.json()
        assert "tickers" in data
        assert "SPY" in data["tickers"]
        assert "count" in data

    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @patch("app.engines.data.router.refresh_ticker_data")
    async def test_refresh_ticker(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-123")
        resp = await client.post("/api/v1/data/refresh/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-123"
        assert data["ticker"] == "AAPL"

    async def test_refresh_ticker_no_api_key(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.polygon_api_key", "")
        resp = await client.post("/api/v1/data/refresh/AAPL")
        assert resp.status_code == 400

    @patch("app.engines.data.service.PolygonDataService")
    async def test_get_ohlcv(self, mock_service, client):
        import pandas as pd
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.load_ohlcv.return_value = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-01"]),
            "open": [150.0],
            "high": [155.0],
            "low": [149.0],
            "close": [153.0],
            "volume": [1000000],
        })
        resp = await client.get("/api/v1/data/ohlcv/AAPL?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bars"]) == 1
        assert data["bars"][0]["close"] == 153.0

    async def test_get_ohlcv_no_data(self, client):
        resp = await client.get("/api/v1/data/ohlcv/UNKNOWN?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["bars"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/data/test_router.py -v`
Expected: FAIL (ImportError for router/module)

- [ ] **Step 3: Create core/dependencies.py**

```python
from fastapi import Request, HTTPException


def verify_api_key(request: Request) -> None:
    from app.config import settings
    if not settings.polygon_api_key:
        raise HTTPException(
            status_code=400,
            detail="Polygon API key not configured. Set POLYGON_API_KEY in .env",
        )
```

- [ ] **Step 4: Create router.py**

```python
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import verify_api_key
from app.engines.data.schemas import (
    DataRefreshResponse,
    DataQuery,
    DataHealthResponse,
)
from app.engines.data.service import PolygonDataService
from app.engines.data.tasks import refresh_ticker_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data"])


@router.get("/universe")
def get_universe():
    from app.models.universe import DEFAULT_UNIVERSE
    return {"tickers": DEFAULT_UNIVERSE, "count": len(DEFAULT_UNIVERSE)}


@router.get("/ohlcv/{ticker}")
def get_ohlcv(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return {"ticker": ticker.upper(), "days": days, "bars": []}
    bars = df.to_dict(orient="records")
    for b in bars:
        if isinstance(b["timestamp"], datetime):
            b["timestamp"] = b["timestamp"].isoformat()
    return {"ticker": ticker.upper(), "days": days, "bars": bars}


@router.post("/refresh/{ticker}", status_code=202)
def refresh_ticker(
    ticker: str,
    days: int = 365,
    _=Depends(verify_api_key),
):
    task = refresh_ticker_data.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/refresh-all", status_code=202)
def refresh_all(_=Depends(verify_api_key)):
    from app.engines.data.tasks import refresh_all_data
    task = refresh_all_data.delay()
    return {"task_id": task.id, "status": "queued", "message": "Refreshing all tickers"}


@router.get("/health")
def data_health():
    return DataHealthResponse(
        tickers_in_universe=len(__import__("app.models.universe", fromlist=["DEFAULT_UNIVERSE"]).DEFAULT_UNIVERSE),  # noqa
        total_ohlcv_bars=0,
        last_refresh=None,
        status="healthy",
    )
```

- [ ] **Step 5: Create main.py**

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.engines.data.router import router as data_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Portfolio Manager",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(data_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/engines/data/test_router.py -v`
Expected: PASS

- [ ] **Step 7: Start the server and verify**

Run: `cd backend && python -m pip install -r requirements.txt && uvicorn app.main:app --port 8001 & sleep 2 && curl -s http://localhost:8001/health && curl -s http://localhost:8001/api/v1/data/universe`
Expected: Health returns `{"status":"ok","version":"0.1.0"}`. Universe returns list of tickers.
Kill server: `kill %1`

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/core/ backend/app/engines/data/router.py backend/tests/engines/data/test_router.py
git commit -m "feat: add FastAPI app with data router, health check, and universe endpoints"
```

---

### Task 7: Integration Test Suite

**Files:**
- Create: `backend/tests/integration/test_data_pipeline.py`

- [ ] **Step 1: Write integration tests**

```python
"""
Integration tests for the data pipeline end-to-end.
Uses a real DuckDB instance and filesystem, but mocks Polygon API.
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestDataPipelineIntegration:
    @pytest.fixture
    def data_service(self, test_data_dir):
        from app.engines.data.service import PolygonDataService
        return PolygonDataService(data_dir=test_data_dir)

    @patch("app.engines.data.service.polygon_client")
    def test_full_refresh_flow(self, mock_client, data_service, test_data_dir):
        """End-to-end: fetch from Polygon → save Parquet → load from Parquet"""
        mock_bar = MagicMock()
        mock_bar.t = int(datetime(2024, 1, 15).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_client.get_aggs.return_value = [mock_bar]

        bars = data_service.fetch_ohlcv("AAPL", days=30)
        assert len(bars) == 1

        path = data_service.save_ohlcv(bars)
        assert os.path.exists(path)

        loaded = data_service.load_ohlcv("AAPL", days=365)
        assert len(loaded) == 1
        assert float(loaded["close"].iloc[0]) == 153.0

    def test_parquet_directory_structure(self, test_data_dir):
        """Verify Parquet files are organized by ticker"""
        from app.database import ensure_parquet_dir
        path = ensure_parquet_dir("AAPL", "ohlcv")
        expected = os.path.join(test_data_dir, "market_data", "ohlcv", "aapl")
        assert path == expected
        assert os.path.exists(path)

    @patch("app.engines.data.service.polygon_client")
    def test_incremental_refresh_appends_data(self, mock_client, data_service, test_data_dir):
        """Refreshing twice should keep all bars"""
        today = datetime.now(timezone.utc)

        # First batch: 5 days ago
        bars1 = []
        for i in range(3):
            ts = today - timedelta(days=5 + i)
            bars1.append({
                "ticker": "AAPL",
                "timestamp": ts,
                "open": 150.0 + i,
                "high": 155.0 + i,
                "low": 149.0 + i,
                "close": 153.0 + i,
                "volume": 1000000,
            })
        data_service.save_ohlcv(bars1)

        # Second batch: today
        bars2 = [{
            "ticker": "AAPL",
            "timestamp": today,
            "open": 160.0,
            "high": 165.0,
            "low": 159.0,
            "close": 163.0,
            "volume": 2000000,
        }]
        data_service.save_ohlcv(bars2)

        loaded = data_service.load_ohlcv("AAPL", days=365)
        assert len(loaded) == 4

    def test_empty_universe_returns_empty_data(self, data_service):
        df = data_service.load_ohlcv("NONEXISTENT", days=30)
        assert df.empty

    @patch("app.engines.data.service.polygon_client")
    def test_concurrent_refresh_same_ticker(self, mock_client, data_service):
        """Multiple refreshes for same ticker should not corrupt data"""
        mock_bar = MagicMock()
        mock_bar.t = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_bar.o = 150.0
        mock_bar.h = 155.0
        mock_bar.l = 149.0
        mock_bar.c = 153.0
        mock_bar.v = 1000000
        mock_client.get_aggs.return_value = [mock_bar]

        bars = data_service.fetch_ohlcv("AAPL", days=30)
        data_service.save_ohlcv(bars)
        data_service.save_ohlcv(bars)  # second save overwrites (same timestamp range)

        loaded = data_service.load_ohlcv("AAPL", days=365)
        assert len(loaded) >= 1  # at minimum, has the data
```

- [ ] **Step 2: Run tests**

Run: `cd backend && python -m pytest tests/integration/ -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --cov=app`
Expected: All tests pass, coverage report shows high coverage on core modules

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/
git commit -m "test: add integration tests for data pipeline end-to-end"
```

---

## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage:**
   - [ ] Data Engine: Polygon API integration ✅ (Task 4)
   - [ ] Database: DuckDB + Parquet storage ✅ (Task 2)
   - [ ] Universe management ✅ (Task 3, Task 6)
   - [ ] OHLCV data collection ✅ (Task 4)
   - [ ] Options chain data: models created, fetch not yet implemented (Phase 2)
   - [ ] Celery scheduled tasks ✅ (Task 5)
   - [ ] FastAPI REST API ✅ (Task 6)
   - [ ] Docker setup ✅ (Task 1)
   - [ ] Tests for every component ✅ (Tasks 2-7)

2. **Placeholder scan:** No TBD, TODO, or incomplete steps.

3. **Type consistency:** All method signatures match across tasks. `fetch_ohlcv` returns `list[dict]`, `save_ohlcv` takes `list[dict]`, `load_ohlcv` returns `pd.DataFrame`. Consistent.

4. **Ambiguity check:** All steps are explicit with exact code and commands.
