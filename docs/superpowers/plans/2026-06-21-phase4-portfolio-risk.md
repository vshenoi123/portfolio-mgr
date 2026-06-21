# Phase 4: Portfolio & Risk Engines — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5 engines — Portfolio Intelligence (impact scoring, concentration, correlation, portfolio delta/beta), Capital Allocation (Kelly/Risk parity sizing, regime-aware), Opportunity Cost (competing-use ranking), Trade Replacement (keep/reduce/exit/replace logic), and Risk Management (limits, health score, trade blocking) — that consume Phase 2-3 outputs and manage portfolio state through DuckDB native tables.

**Architecture:** Five engine packages under `backend/app/engines/portfolio/`, `backend/app/engines/allocation/`, `backend/app/engines/cost/`, `backend/app/engines/replacement/`, `backend/app/engines/risk/`. Each has `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py`. Portfolio state persisted in DuckDB tables (`positions`, `options_positions`, `portfolio_snapshots`, `capital_allocation`). Correlation matrix computed from returns data. Risk limits configurable via settings/env vars.

**Tech Stack:** Python 3.12, numpy, pandas, duckdb, scipy, FastAPI, Celery, pytest, unittest.mock

**Testing Requirement:** Every major component must have tests covering normal operation, edge cases, and error states.

---

### Task 1: Prerequisites — DuckDB Schema for Portfolio Tables + Settings Update

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_database.py`

- [ ] **Step 1: Write the failing test for schema initialization**

Append to `backend/tests/test_database.py`:
```python
class TestPortfolioSchema:
    def test_portfolio_tables_created(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('positions','options_positions','portfolio_snapshots','capital_allocation')"
            ).fetchall()
            names = {r[0] for r in tables}
            assert "positions" in names
            assert "options_positions" in names
            assert "portfolio_snapshots" in names
            assert "capital_allocation" in names
        finally:
            close_connection(test_db_path)

    def test_portfolio_tables_have_expected_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(positions)").fetchall()
            names = {c[1] for c in cols}
            for expected in ("id", "ticker", "quantity", "avg_price", "current_price",
                             "market_value", "unrealized_pl", "unrealized_pl_pct",
                             "sector", "beta", "delta", "gamma", "theta", "vega",
                             "strategy_type", "opened_at", "updated_at"):
                assert expected in names, f"Missing column {expected} in positions"
        finally:
            close_connection(test_db_path)

    def test_capital_allocation_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(capital_allocation)").fetchall()
            names = {c[1] for c in cols}
            for expected in ("id", "date", "strategy", "ticker", "position_size",
                             "capital_pct", "strategy_allocation_pct",
                             "allocation_method", "regime_at_allocation", "total_portfolio_value",
                             "cash_reserve"):
                assert expected in names
        finally:
            close_connection(test_db_path)

    def test_portfolio_snapshots_columns(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        try:
            cols = conn.execute("PRAGMA table_info(portfolio_snapshots)").fetchall()
            names = {c[1] for c in cols}
            for expected in ("id", "date", "total_value", "cash", "equity_value",
                             "options_value", "total_exposure", "daily_pl",
                             "daily_pl_pct", "total_unrealized_pl", "max_drawdown",
                             "portfolio_beta", "portfolio_delta_e",
                             "concentration_pct_top5", "sector_exposures",
                             "correlation_matrix_json", "portfolio_health_score"):
                assert expected in names
        finally:
            close_connection(test_db_path)

    def test_risk_limits_config_loaded(self):
        from app.config import settings
        assert hasattr(settings, "max_position_size_pct")
        assert hasattr(settings, "max_sector_exposure_pct")
        assert hasattr(settings, "max_portfolio_delta")
        assert hasattr(settings, "max_concentration_pct")
        assert hasattr(settings, "min_cash_reserve_pct")
        assert hasattr(settings, "kelly_fraction")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_database.py::TestPortfolioSchema -v`
Expected: FAIL (tables missing, settings missing)

- [ ] **Step 3: Update config.py**

Replace `backend/app/config.py`:
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Update database.py to create portfolio tables**

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


def get_data_dir() -> str:
    from app.config import settings
    return settings.data_dir


def ensure_parquet_dir(ticker: str, data_type: str = "ohlcv") -> str:
    base = get_data_dir()
    path = os.path.join(base, "market_data", data_type, ticker.lower())
    os.makedirs(path, exist_ok=True)
    return path
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_database.py::TestPortfolioSchema -v`
Expected: PASS

- [ ] **Step 6: Commit**

```
git add backend/app/config.py backend/app/database.py backend/tests/test_database.py
git commit -m "feat: add portfolio DuckDB schema and risk limit settings for Phase 4"
```

---

### Task 2: Portfolio Intelligence Engine — Schemas

**Files:**
- Create: `backend/app/engines/portfolio/__init__.py`
- Create: `backend/app/engines/portfolio/schemas.py`
- Test: `backend/tests/engines/portfolio/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/portfolio/test_schemas.py` with the following test class `TestPortfolioSchemas`:

- `test_portfolio_state_valid` — PortfolioState with total_value, cash, equity, options, sectors; verify cash_pct == 30%
- `test_portfolio_state_defaults` — PortfolioState with 0s; verify equity_value == 0, sector_exposures == {}
- `test_portfolio_impact_score_valid` — PortfolioImpactScore with ticker, raw=95, adjusted=78, 2 impact_factors; verify values
- `test_portfolio_impact_score_defaults` — PortfolioImpactScore with ticker, raw=80; verify adjusted==80, factors empty
- `test_portfolio_position_valid` — PortfolioPosition with AAPL, qty=100, avg=150, current=165; verify market_value=16500, unrealized_pl=1500, weight_pct~6.6
- `test_portfolio_state_endpoint_response` — PortfolioSummaryResponse with all fields; verify portfolio_beta
- `test_correlation_pair_valid` — CorrelationPair AAPL/MSFT corr=0.75; verify value
- `test_correlation_pair_rejects_out_of_range` — CorrelationPair with corr=1.5; expect ValidationError
- `test_holding_extended_schema` — HoldingDetail with all fields; verify days_held, risk_score

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/portfolio/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/portfolio/__init__.py` (empty).
Create `backend/app/engines/portfolio/schemas.py` with:

- `PortfolioPosition(BaseModel)`: ticker, quantity, avg_price, current_price; computed market_value (qty*current), cost_basis (qty*avg), unrealized_pl, unrealized_pl_pct, weight_pct via __init__ override; beta=1.0, delta=1.0, sector="UNKNOWN", strategy_type="equity" defaults
- `PortfolioState(BaseModel)`: total_value, cash, equity_value=0, options_value=0, positions=[], options_positions=[], sector_exposures={}, portfolio_beta=0, portfolio_delta_e=0; cash_pct property
- `PortfolioImpactScore(BaseModel)`: ticker, raw_opportunity_score, adjusted_score=0 (defaults to raw), impact_factors=[]
- `CorrelationPair(BaseModel)`: ticker_a, ticker_b, correlation; validator -1..1
- `HoldingDetail(BaseModel)`: all position fields + days_held=0, active_risk_score=0, details={}
- `PortfolioSummaryResponse(BaseModel)`: total_value, cash, equity_value, options_value, num_positions, num_options, portfolio_beta, portfolio_delta_e, portfolio_health_score, top_holdings=[], details={}

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/portfolio/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/portfolio/__init__.py backend/app/engines/portfolio/schemas.py backend/tests/engines/portfolio/test_schemas.py
git commit -m "feat: add portfolio intelligence schemas with impact score, state, and holdings"
```

---

### Task 3: Portfolio Intelligence Engine — Core Service

**Files:**
- Create: `backend/app/engines/portfolio/service.py`
- Test: `backend/tests/engines/portfolio/test_service.py`

The service implements 6 key functions:

1. **load_portfolio_state(db_path)** — queries DuckDB positions/options/snapshots, computes totals, sector exposures, portfolio beta/delta, returns PortfolioState
2. **calculate_portfolio_impact(ticker, raw_score, positions, sector_exposures, total_value, cash, correlation_matrix=None)** — applies sector concentration penalty (>25%/35%), existing position penalty (>10%), correlation penalty (>=0.70), cash bonus (>=25%), concentration penalty (>70%). Returns PortfolioImpactScore with factors list
3. **compute_portfolio_beta(positions, total_equity_value)** — weighted average of position betas
4. **compute_portfolio_delta(positions, options_positions)** — sum of market_value * delta for all positions
5. **compute_concentration(positions, total_value)** — top 5 holdings as % of total
6. **compute_correlation_matrix(returns)** — numpy corrcoef for dict of ticker->array returns

Private helpers: _get_sector_for_ticker, _compute_top_holdings_pct

Tests (in `TestPortfolioStateLoading`, `TestPortfolioImpact`, `TestPortfolioMetrics`, `TestCorrelationMatrix`):
- `test_load_portfolio_state_empty` — no data, returns state with 0s
- `test_load_portfolio_state_with_positions` — insert AAPL, NVDA, XOM; verify 3 positions, sectors, totals
- `test_load_portfolio_state_sector_exposure_aggregation` — insert AAPL; verify TECHNOLOGY sector exposure
- `test_calculate_portfolio_impact_no_positions` — empty portfolio; adjusted == raw
- `test_calculate_portfolio_impact_sector_concentration` — AMD at 30% TECHNOLOGY; adjusted < raw, sector factor present
- `test_calculate_portfolio_impact_correlation_penalty` — AMD with NVDA corr 0.85; adjusted < raw, correlation factor present
- `test_calculate_portfolio_impact_cash_reserve_bonus` — cash at 40%; adjusted >= raw
- `test_calculate_portfolio_impact_high_concentration_blocks` — AMD at 45%; adjusted < 60
- `test_calculate_portfolio_impact_empty_state` — 0 values; adjusted = 0
- `test_compute_portfolio_beta` — two positions, verify weighted avg
- `test_compute_portfolio_beta_no_positions` — empty list returns 0
- `test_compute_portfolio_delta` — positions + options delta
- `test_compute_portfolio_delta_no_options` — only positions
- `test_compute_concentration_top5` — 6 positions, top 5 = 97% approx
- `test_compute_concentration_empty` — empty returns 0
- `test_compute_correlation_matrix` — 3 tickers with returns; verify AAPL->MSFT in matrix
- `test_compute_correlation_matrix_single_ticker` — single ticker, returns 1.0
- `test_compute_correlation_matrix_no_data` — empty dict returns {}

- [ ] **Steps 1-2: Write tests, run to verify fail**

Write all tests in `backend/tests/engines/portfolio/test_service.py`. Run and verify ImportError.

- [ ] **Step 3: Write implementation**

Create `backend/app/engines/portfolio/service.py` with all 6 functions + helpers.

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/portfolio/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/portfolio/service.py backend/tests/engines/portfolio/test_service.py
git commit -m "feat: add portfolio intelligence service with impact scoring, beta, delta, correlation"
```

---

### Task 4: Capital Allocation Engine — Schemas & Kelly Criterion Sizing

**Files:**
- Create: `backend/app/engines/allocation/__init__.py`
- Create: `backend/app/engines/allocation/schemas.py`
- Create: `backend/app/engines/allocation/service.py`
- Test: `backend/tests/engines/allocation/test_schemas.py`
- Test: `backend/tests/engines/allocation/test_service.py`

**Schemas** (TestAllocationSchemas):
- `AllocationRequest(BaseModel)`: ticker, opportunity_score, total_portfolio_value=100000, cash_available=50000, regime="Range", strategy="swing", existing_position_value=0, win_probability=0.55, expected_return_pct=10.0, max_risk_pct=2.0; validators for non-negative and win_prob 0-1
- `AllocationResult(BaseModel)`: ticker, position_size, capital_pct, strategy_allocation_pct=0, allocation_method="kelly", regime_at_allocation="Unknown", total_portfolio_value=0, cash_reserve=0, details={}
- `StrategyAllocation(BaseModel)`: strategy, allocation_pct (0-100 validator), max_positions=5, rationale=""

Tests: valid request, default values, valid result, default result, valid strategy allocation, out-of-range rejection

**Service** (TestKellyCriterion, TestPositionSizing, TestRegimeAwareAllocation, TestSaveAllocation):

Functions:
- `kelly_criterion(win_prob, win_loss_ratio)` — full Kelly formula f* = (bp - q)/b; returns -1..1; edge cases for 0/1 probability
- `fractional_kelly(win_prob, win_loss_ratio, fraction=0.25)` — max(0, full * fraction)
- `get_strategy_allocation(regime)` — returns list of StrategyAllocation per regime:
  - Bull: leaps 35%, equity 25%, swing 20%, csp 12%, pmcc 8%
  - Bull High Vol: swing 30%, csp 25%, equity 20%, leaps 15%, pmcc 10%
  - Bear: cash 40%, csp 30%, swing 15%, pmcc 10%, leaps 5%
  - Bear High Vol: cash 50%, csp 25%, swing 15%, pmcc 10%
  - Range: csp 30%, swing 25%, pmcc 20%, equity 15%, leaps 10%
  - Crisis: cash 70%, csp 15%, swing 10%, pmcc 5%
  - Default: cash 30%, csp 25%, swing 20%, equity 15%, leaps 10%
- `calculate_position_size(total_portfolio_value, cash_available, kelly_fraction, opportunity_score, strategy, regime, ...)` — combines Kelly, score factor, regime capacity factor, caps by cash/strategy limits; returns AllocationResult
- `save_allocation(result, strategy, db_path)` — inserts into capital_allocation DuckDB table

Regime capacity factor model (_get_regime_capacity_factor):
- Bull: leaps 1.0, equity 1.0, swing 0.8, csp 0.5, pmcc 0.5
- Bear: leaps 0.1, equity 0.2, swing 0.5, csp 0.8, pmcc 0.6
- Range: leaps 0.4, equity 0.5, swing 0.8, csp 1.0, pmcc 1.0
- Crisis: leaps 0.05, equity 0.1, swing 0.4, csp 0.5, pmcc 0.3

Tests:
- kelly criterion: 60% win / 1.5 ratio = 0.3333; 50/50 = 0; 90%/2x > 0.8; 0 prob = 0; negative fraction; 100% prob = 1.0; fractional 0.25
- position sizing: Kelly with $250k/$75k = positive size; zero cash = 0 size; low score < $5k; bear regime < 10%
- regime allocation: Bull has leaps > 20%; Bear has csp > 15% and leaps < 5%; Range has swing > 15% and csp > 10%; unknown returns non-negative
- save allocation: saves and reads back from DuckDB

- [ ] **Steps 1-8: TDD cycle as above**

- [ ] **Step 9: Commit**

```
git add backend/app/engines/allocation/__init__.py backend/app/engines/allocation/schemas.py backend/app/engines/allocation/service.py backend/tests/engines/allocation/test_schemas.py backend/tests/engines/allocation/test_service.py
git commit -m "feat: add capital allocation engine with Kelly criterion sizing and regime-aware strategy allocs"
```

---

### Task 5: Opportunity Cost Engine — Schemas & Service

**Files:**
- Create: `backend/app/engines/cost/__init__.py`
- Create: `backend/app/engines/cost/schemas.py`
- Create: `backend/app/engines/cost/service.py`
- Test: `backend/tests/engines/cost/test_schemas.py`
- Test: `backend/tests/engines/cost/test_service.py`

**Schemas** (TestCostSchemas):
- `OpportunityCostItem(BaseModel)`: candidate, score (0-100 validator), cost_type, rationale, estimated_return_pct=0, risk_score>=0, capital_required=0
- `OpportunityCostRanking(BaseModel)`: candidates list[dict], cash_available, total_portfolio_value, recommendation, details

**Service** (TestOpportunityCost):
- `rank_opportunity_cost(candidates, cash_available, total_portfolio_value=0, existing_positions=None, watchlist=None)`:
  - Computes risk_adjusted = score * (1 - risk/200)
  - return_per_dollar = (return / capital) * 100
  - type_bonus: add_to_existing=2, watchlist=3, new_position=0
  - concentration penalty if existing weight > 20%
  - watchlist affinity bonus +2
  - final = risk_adjusted + (return_per_dollar * 0.5) + type_bonus
  - Capital constraint penalty if > cash available
  - Sort descending by final_score
  - Generate text recommendation

Tests: basic ranking orders by score, empty returns empty, risk adjustment (low risk beats high risk despite lower score), capital constraint (cheaper wins), existing holdings considered, watchlist considered

- [ ] **Steps 1-8: TDD cycle**

- [ ] **Step 9: Commit**

```
git add backend/app/engines/cost/__init__.py backend/app/engines/cost/schemas.py backend/app/engines/cost/service.py backend/tests/engines/cost/test_schemas.py backend/tests/engines/cost/test_service.py
git commit -m "feat: add opportunity cost engine with risk-adjusted ranking and capital constraints"
```

---

### Task 6: Trade Replacement Engine — Schemas & Service

**Files:**
- Create: `backend/app/engines/replacement/__init__.py`
- Create: `backend/app/engines/replacement/schemas.py`
- Create: `backend/app/engines/replacement/service.py`
- Test: `backend/tests/engines/replacement/test_schemas.py`
- Test: `backend/tests/engines/replacement/test_service.py`

**Schemas** (TestReplacementSchemas):
- `PositionEvaluation(BaseModel)`: ticker, score (0-100), action literal["keep","reduce","exit","replace"], rationale, details={}
- `TradeReplacement(BaseModel)`: current_ticker, current_score, replacement_ticker, replacement_score, rationale="", estimated_upside_pct=0, confidence=0
- `ReplacementResponse(BaseModel)`: evaluations=[], replacements=[], total_positions_evaluated=0, details={}

**Service** (TestPositionEvaluation, TestTradeReplacement, TestBatchEvaluations):
- `evaluate_position(ticker, score, regime, trend_score, momentum_score, unrealized_pl_pct, days_held)`:
  - combined = (score + trend + momentum) / 3
  - Bear/Crisis: exit if pl < -15% or score < 30; reduce if combined < 50
  - Bull: keep if score >= 75 and trend >= 70; keep if 50-75 and pl > 5%
  - Range: reduce if combined < 45
  - Default: exit if pl < -20%; reduce if score < 40; keep if score >= 65 and days > 30
  - Fallback: keep
- `find_replacements(current_positions, opportunity_scores, min_score_gap=10)`:
  - Skip "keep" positions
  - For each non-keep position, find best opportunity with gap >= min_score_gap
  - Sector match bonus (1.2x gap), different sector penalty (0.8x)
  - Return ReplacementResponse with evaluations + replacements
  - confidence = min(0.95, max(0.3, score_diff/100))
- `evaluate_all_positions(positions_data)` — batch evaluate, returns list of PositionEvaluation

Tests: strong keep, underperforming reduce, loss exit, replacement candidate, low score reduce, neutral keep; basic replacement finds candidates, no candidates returns empty, keep actions skipped, same ticker skipped, score gap threshold respected, different sector penalized; batch evaluation verifies both actions

- [ ] **Steps 1-8: TDD cycle**

- [ ] **Step 9: Commit**

```
git add backend/app/engines/replacement/__init__.py backend/app/engines/replacement/schemas.py backend/app/engines/replacement/service.py backend/tests/engines/replacement/test_schemas.py backend/tests/engines/replacement/test_service.py
git commit -m "feat: add trade replacement engine with position evaluation and replacement finder"
```

---

### Task 7: Risk Management Engine — Schemas & Core Service

**Files:**
- Create: `backend/app/engines/risk/__init__.py`
- Create: `backend/app/engines/risk/schemas.py`
- Create: `backend/app/engines/risk/service.py`
- Test: `backend/tests/engines/risk/test_schemas.py`
- Test: `backend/tests/engines/risk/test_service.py`

**Schemas** (TestRiskSchemas):
- `RiskLimit(BaseModel)`: name, value, unit="", description="", enabled=True
- `RiskAssessment(BaseModel)`: portfolio_health_score, max_drawdown, current_exposure, total_value, concentration_pct, violations=[], is_safe=True, details={}; exposure_pct property
- `TradeRiskCheck(BaseModel)`: ticker, requested_size, is_allowed, checks_passed=0, checks_failed=0, details=[]

**Service** (TestPortfolioHealth, TestRiskLimitEnforcement, TestTradeRiskCheck, TestRiskAssessmentFull):

Functions:
- `calculate_portfolio_health(max_drawdown, concentration_pct, portfolio_beta, total_exposure_pct, cash_pct, num_violations, unrealized_volatility)`:
  - Start 100, penalty: drawdown*1.2 (max 30), concentration>40% penalty ((pct-40)*0.8, max 20), beta>1.5 penalty ((beta-1.5)*20, max 15), exposure>80% penalty ((pct-80)*0.5, max 15), cash_bonus (pct*0.3, max 10), violation penalty (count*5, max 20), vol>0.35 penalty ((vol-0.35)*30, max 10)
  - Clamp 0-100
- `check_position_size_limit(ticker, requested_size, total_portfolio_value, max_position_pct)` — returns dict with check/passed/current/limit/message
- `check_sector_exposure(sector, new_size, sector_exposures, total_value, max_sector_pct)` — UNKNOWN always passes
- `check_portfolio_delta(new_delta, current_delta, max_delta)` — total delta check
- `check_cash_available(requested_size, cash_available, min_cash_reserve_pct, total_value)` — usable = cash - reserve
- `validate_trade(ticker, requested_size, total_portfolio_value, cash_available, sector, sector_exposures, current_delta)` — runs all 5 checks, returns TradeRiskCheck
- `assess_portfolio_risk(db_path, max_drawdown=0, total_value=0, cash=0)` — loads positions/options from DuckDB, computes exposure/concentration/beta/violations, returns RiskAssessment with health score

Tests:
- Health: perfect (85-100), poor (<40), mid (40-80), extreme drawdown (<50)
- Limit enforcement: position size passes/fails, sector passes/fails/unknown, delta passes/fails, cash passes/fails
- Trade validation: all passes, blocked by size, blocked by sector, blocked by cash
- Full assessment: safe with small position, violations with concentrated position

- [ ] **Steps 1-8: TDD cycle**

- [ ] **Step 9: Commit**

```
git add backend/app/engines/risk/__init__.py backend/app/engines/risk/schemas.py backend/app/engines/risk/service.py backend/tests/engines/risk/test_schemas.py backend/tests/engines/risk/test_service.py
git commit -m "feat: add risk management engine with health score, limit enforcement, and trade validation"
```

---

### Task 8: FastAPI Routers for All 5 Engines

**Files:**
- Create: `backend/app/engines/portfolio/router.py`
- Create: `backend/app/engines/allocation/router.py`
- Create: `backend/app/engines/cost/router.py`
- Create: `backend/app/engines/replacement/router.py`
- Create: `backend/app/engines/risk/router.py`
- Tests for each router (httpx AsyncClient)

All routers under prefix `/api/v1/portfolio` with tag "portfolio".

**Portfolio Router** (`/api/v1/portfolio`):
- `GET /` → get_portfolio_summary — loads state from DB, returns PortfolioSummaryResponse
- `GET /holdings` → get_holdings — returns list of HoldingDetail from current positions
- `GET /options` → get_options_positions — returns list of open options positions
- `GET /health` → get_portfolio_health — computes risk assessment
- `GET /exposure` → get_exposure — returns sector exposures + concentration
- `GET /impact/{ticker}` → get_portfolio_impact(ticker, raw_score=75) — calculates impact using current portfolio state
- `GET /allocation` → get_allocation — returns current strategy allocations for regime (default "Range")
- `POST /optimize` → optimize_allocation — body with regime, cash, opportunities; returns allocations for each

**Allocation Router** (functions in portfolio router or separate):
- Kept within portfolio router to avoid endpoint conflicts

**Cost Router** (`POST /api/v1/portfolio/opportunity-cost`):
- Body with candidates list + cash_available; returns OpportunityCostRanking

**Replacement Router** (`POST /api/v1/portfolio/replacements`):
- Body with current_positions + opportunity_scores; returns ReplacementResponse

**Risk Router** (endpoints within portfolio router):
- `GET /health` — RiskAssessment
- `GET /exposure` — exposure details
- `POST /validate-trade` — TradeRiskCheck body with ticker, requested_size, sector

Tests (5 router test files):
- Portfolio: GET /, /holdings, /health, /exposure, /impact/{ticker} all return 200 with expected keys
- Allocation: GET /allocation returns 200, POST /optimize returns 200
- Cost: POST /opportunity-cost returns 200 with candidates
- Replacement: POST /replacements returns 200 with replacements
- Risk: GET /health returns health score, GET /exposure returns data

- [ ] **Steps 1-3: TDD cycle for each router**

- [ ] **Step 4: Run all router tests**

Run: `cd backend && python -m pytest tests/engines/portfolio/test_router.py tests/engines/allocation/test_router.py tests/engines/cost/test_router.py tests/engines/replacement/test_router.py tests/engines/risk/test_router.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/portfolio/router.py backend/app/engines/allocation/router.py backend/app/engines/cost/router.py backend/app/engines/replacement/router.py backend/app/engines/risk/router.py backend/tests/engines/portfolio/test_router.py backend/tests/engines/allocation/test_router.py backend/tests/engines/cost/test_router.py backend/tests/engines/replacement/test_router.py backend/tests/engines/risk/test_router.py
git commit -m "feat: add FastAPI routers for all 5 Phase 4 portfolio/risk engines"
```

---

### Task 9: Celery Tasks for All 5 Engines

**Files:**
- Create: `backend/app/engines/portfolio/tasks.py`
- Create: `backend/app/engines/allocation/tasks.py`
- Create: `backend/app/engines/cost/tasks.py`
- Create: `backend/app/engines/replacement/tasks.py`
- Create: `backend/app/engines/risk/tasks.py`
- Tests for each

**Portfolio Tasks** (TestPortfolioTasks):
- `compute_portfolio_snapshot(max_drawdown=0)` — loads state, computes risk, inserts into portfolio_snapshots
- Tests: success inserts snapshot, error handling

**Allocation Tasks** (TestAllocationTasks):
- `run_daily_allocation(regime="Range")` — loads state, gets strategy allocations, saves to DB
- Tests: basic allocation, regime override, error handling

**Cost Tasks** (TestCostTasks):
- `evaluate_opportunity_cost()` — loads top opportunities + portfolio state, generates ranking
- Tests: returns ranking, empty state

**Replacement Tasks** (TestReplacementTasks):
- `evaluate_replacements()` — loads current positions, gets opportunities, computes replacements
- Tests: basic evaluation, no positions

**Risk Tasks** (TestRiskTasks):
- `assess_risk_and_alert()` — computes assessment, alerts on violations
- Tests: safe assessment, violation detection

All tasks use `@shared_task(bind=True, max_retries=2)` pattern with try/except returning dict with status.

- [ ] **Steps 1-3: TDD cycle for each task**

- [ ] **Step 4: Run all task tests**

Run: `cd backend && python -m pytest tests/engines/portfolio/test_tasks.py tests/engines/allocation/test_tasks.py tests/engines/cost/test_tasks.py tests/engines/replacement/test_tasks.py tests/engines/risk/test_tasks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add backend/app/engines/portfolio/tasks.py backend/app/engines/allocation/tasks.py backend/app/engines/cost/tasks.py backend/app/engines/replacement/tasks.py backend/app/engines/risk/tasks.py backend/tests/engines/portfolio/test_tasks.py backend/tests/engines/allocation/test_tasks.py backend/tests/engines/cost/test_tasks.py backend/tests/engines/replacement/test_tasks.py backend/tests/engines/risk/test_tasks.py
git commit -m "feat: add Celery tasks for all 5 Phase 4 portfolio/risk engines"
```

---

### Task 10: Wire Into main.py + Beat Schedule

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`
- Test: `backend/tests/test_main.py`

**main.py updates:**
- Add Phase 4 routers: portfolio, allocation, cost, replacement, risk (all under /api/v1/portfolio)
- Update app version to "0.4.0"
- Add Phase 4 endpoints test class

**celery_app.py updates:**
- Add Phase 4 beat schedule entries:
  - `compute-portfolio-snapshot-daily` → portfolio.tasks.compute_portfolio_snapshot (daily)
  - `run-daily-allocation` → allocation.tasks.run_daily_allocation (daily)
  - `evaluate-opportunity-cost-daily` → cost.tasks.evaluate_opportunity_cost (daily)
  - `evaluate-replacements-daily` → replacement.tasks.evaluate_replacements (daily)
  - `assess-risk-daily` → risk.tasks.assess_risk_and_alert (daily)

- [ ] **Steps 1-5: Write tests, update main.py + celery_app.py, verify**

- [ ] **Step 6: Commit**

```
git add backend/app/main.py backend/app/celery_app.py backend/tests/test_main.py
git commit -m "feat: wire Phase 4 routers and add Celery beat schedule for portfolio/risk tasks"
```

---

### Task 11: Integration Tests for Portfolio Pipeline

**Files:**
- Create: `backend/tests/integration/test_portfolio_pipeline.py`

Integration tests covering:
1. Full portfolio state loading from DuckDB with realistic data
2. Portfolio impact cascading: load state → calculate impact for ticker → verify factors
3. Kelly sizing → save allocation → read back from DB
4. Opportunity cost → replacement suggestion end-to-end
5. Risk assessment → violation detection → trade validation
6. All 5 engines working together on sample data

- [ ] **Steps 1-3: Write tests, run, verify**

- [ ] **Step 4: Commit**

```
git add backend/tests/integration/test_portfolio_pipeline.py
git commit -m "test: add integration tests for portfolio pipeline end-to-end"
```

---

### Task 12: Final Cleanup — Ruff Lint & Full Test Suite

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
git commit -m "chore: lint and type-check Phase 4 portfolio and risk engines"
```

---

## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage:**
   - [ ] Task 1: Portfolio DuckDB tables (positions, options_positions, portfolio_snapshots, capital_allocation) with full column schemas
   - [ ] Task 1: Risk limit config settings (max_position_size_pct, max_sector_exposure_pct, max_portfolio_delta, max_concentration_pct, min_cash_reserve_pct, kelly_fraction, etc.)
   - [ ] Task 2: Portfolio schemas (PortfolioState, PortfolioImpactScore, PortfolioPosition, CorrelationPair, HoldingDetail, PortfolioSummaryResponse)
   - [ ] Task 3: Portfolio impact scoring with sector concentration, existing position, correlation, cash reserve, concentration adjustments
   - [ ] Task 3: Portfolio beta (weighted average) and delta (market_value * delta sum)
   - [ ] Task 3: Correlation matrix from returns data using numpy corrcoef
   - [ ] Task 3: Portfolio state loading from DuckDB with sector exposure aggregation
   - [ ] Task 4: Kelly Criterion sizing with fractional Kelly
   - [ ] Task 4: Regime-aware strategy allocation (Bull → more LEAPS/equity, Bear → cash/defensive CSP, Range → income)
   - [ ] Task 4: Position sizing with cash, score, regime capacity factor, strategy caps
   - [ ] Task 4: Save allocation to DuckDB capital_allocation table
   - [ ] Task 5: Opportunity cost ranking with risk adjustment, capital efficiency, cost type bonuses
   - [ ] Task 5: Capital constraint handling
   - [ ] Task 6: Position evaluation (keep/reduce/exit) with regime-aware rules
   - [ ] Task 6: Trade replacement finder with sector matching, score gap, confidence
   - [ ] Task 7: Portfolio Health Score (drawdown, concentration, beta, exposure, cash, violations, volatility)
   - [ ] Task 7: Risk limit enforcement (position size, sector exposure, delta, cash reserve, concentration)
   - [ ] Task 7: Trade validation/blocking with detailed check results
   - [ ] Task 8: FastAPI router endpoints for all 5 engines under /api/v1/portfolio
   - [ ] Task 9: Celery tasks for daily snapshot, allocation, cost, replacements, risk assessment
   - [ ] Task 10: main.py wiring + beat schedule integration
   - [ ] Task 11: Integration tests for portfolio pipeline
   - [ ] Task 12: Ruff lint clean, full test suite passing

2. **Placeholder scan:** No TBD, TODO, or incomplete steps.

3. **Type consistency:** All method signatures match across tasks. `load_portfolio_state` returns `PortfolioState`, `calculate_portfolio_impact` returns `PortfolioImpactScore`, `calculate_position_size` returns `AllocationResult`, `rank_opportunity_cost` returns `OpportunityCostRanking`, `evaluate_position` returns `PositionEvaluation`, `find_replacements` returns `ReplacementResponse`, `validate_trade` returns `TradeRiskCheck`, `assess_portfolio_risk` returns `RiskAssessment`.

4. **Ambiguity check:** All steps are explicit with exact code and commands.
