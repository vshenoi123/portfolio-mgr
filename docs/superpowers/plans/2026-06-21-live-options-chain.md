# Live Options Chain + Stocks Filter Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the stocks filter showing 0 matches and replace Black-Scholes-only trade generation with live Polygon options chain data (real strikes, bids, asks, IV, Greeks, OI, volume).

**Architecture:** Add a `polygon_chain.py` module that fetches live options contracts and snapshots from Polygon's API. Integrate it into `generate.py` with a fallback to Black-Scholes. Update the frontend TradeGenerationModal to show live data badges, bid/ask spread, OI, and volume.

**Tech Stack:** Python, FastAPI, polygon-api-client, pandas, Next.js, React

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/engines/options/polygon_chain.py` | **Create** | Live options chain fetcher from Polygon API |
| `backend/app/engines/options/service.py` | **Modify** | Add `generate_csp_live()`, `generate_leaps_live()`, etc. that use live data |
| `backend/app/engines/trading/generate.py` | **Modify** | Try live chain first, fallback to Black-Scholes |
| `backend/app/engines/data/ticker_details.py` | **Modify** | Auto-refresh cache if empty |
| `frontend/src/components/shared/TradeGenerationModal.js` | **Modify** | Show live data badge, bid/ask, OI, volume |
| `frontend/src/lib/api.js` | **Modify** | (no changes needed — existing `generateTrade` works) |
| `tests/engines/options/test_polygon_chain.py` | **Create** | Unit tests for live chain fetcher |

---

## Task 1: Create `polygon_chain.py` — Live Options Chain Fetcher

**Files:**
- Create: `backend/app/engines/options/polygon_chain.py`
- Test: `tests/engines/options/test_polygon_chain.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/engines/options/test_polygon_chain.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import date, timedelta


def test_fetch_option_chain_returns_contracts():
    """fetch_option_chain returns list of contracts for a ticker."""
    from app.engines.options.polygon_chain import fetch_option_chain

    mock_contract = MagicMock()
    mock_contract.ticker = "O:AAPL250718C00200000"
    mock_contract.strike_price = 200.0
    mock_contract.contract_type = "call"
    mock_contract.expiration_date = "2025-07-18"

    with patch("app.engines.options.polygon_chain.RESTClient") as MockClient:
        instance = MockClient.return_value
        instance.list_options_contracts.return_value = iter([mock_contract])
        result = fetch_option_chain("AAPL", contract_type="call", dte_min=20, dte_max=40)

    assert len(result) >= 1
    assert result[0]["ticker"] == "O:AAPL250718C00200000"
    assert result[0]["strike"] == 200.0
    assert result[0]["type"] == "call"


def test_fetch_chain_snapshot_returns_live_data():
    """fetch_chain_snapshot returns bid/ask/greeks/OI for a contract."""
    from app.engines.options.polygon_chain import fetch_chain_snapshot

    mock_snapshot = MagicMock()
    mock_snapshot.implied_volatility = 0.35
    mock_snapshot.greeks = MagicMock()
    mock_snapshot.greeks.delta = 0.32
    mock_snapshot.greeks.gamma = 0.02
    mock_snapshot.greeks.theta = -0.05
    mock_snapshot.greeks.vega = 0.15
    mock_snapshot.last_quote = MagicMock()
    mock_snapshot.last_quote.bid = 5.20
    mock_snapshot.last_quote.ask = 5.40
    mock_snapshot.last_quote.midpoint = 5.30
    mock_snapshot.open_interest = 1500
    mock_snapshot.last_trade = MagicMock()
    mock_snapshot.last_trade.price = 5.25
    mock_snapshot.last_trade.size = 10
    mock_snapshot.break_even_price = 205.30
    mock_snapshot.underlying_asset = MagicMock()
    mock_snapshot.underlying_asset.price = 200.0

    with patch("app.engines.options.polygon_chain.RESTClient") as MockClient:
        instance = MockClient.return_value
        instance.get_snapshot_option.return_value = mock_snapshot
        result = fetch_chain_snapshot("AAPL", "O:AAPL250718C00200000")

    assert result is not None
    assert result["iv"] == 0.35
    assert result["bid"] == 5.20
    assert result["ask"] == 5.40
    assert result["delta"] == 0.32
    assert result["open_interest"] == 1500


def test_fetch_chain_snapshot_returns_none_on_error():
    """fetch_chain_snapshot returns None if API fails."""
    from app.engines.options.polygon_chain import fetch_chain_snapshot

    with patch("app.engines.options.polygon_chain.RESTClient") as MockClient:
        instance = MockClient.return_value
        instance.get_snapshot_option.side_effect = Exception("API error")
        result = fetch_chain_snapshot("AAPL", "O:AAPL250718C00200000")

    assert result is None


def test_find_nearest_contract_picks_closest_delta():
    """find_nearest_contract returns contract closest to target delta."""
    from app.engines.options.polygon_chain import find_nearest_contract

    contracts = [
        {"ticker": "A", "strike": 190, "delta": 0.15, "bid": 1.0, "ask": 1.2, "iv": 0.30, "open_interest": 100, "volume": 10},
        {"ticker": "B", "strike": 195, "delta": 0.28, "bid": 3.0, "ask": 3.2, "iv": 0.32, "open_interest": 500, "volume": 50},
        {"ticker": "C", "strike": 200, "delta": 0.50, "bid": 7.0, "ask": 7.2, "iv": 0.35, "open_interest": 1000, "volume": 100},
    ]
    result = find_nearest_contract(contracts, target_delta=0.30)
    assert result["ticker"] == "B"
    assert abs(result["delta"] - 0.30) < abs(contracts[0]["delta"] - 0.30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/options/test_polygon_chain.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.engines.options.polygon_chain'`

- [ ] **Step 3: Implement `polygon_chain.py`**

```python
# backend/app/engines/options/polygon_chain.py
"""Live options chain fetcher using Polygon API."""

import logging
from datetime import date, timedelta

from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> RESTClient:
    return RESTClient(settings.polygon_api_key)


def fetch_option_chain(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
    limit: int = 250,
) -> list[dict]:
    """Fetch available option contracts for a ticker within DTE range.

    Returns list of dicts: {ticker, strike, type, expiration_date, dte}
    """
    client = _get_client()
    today = date.today()
    exp_gte = today + timedelta(days=dte_min)
    exp_lte = today + timedelta(days=dte_max)

    try:
        contracts = client.list_options_contracts(
            underlying_ticker=ticker,
            contract_type=contract_type,
            expiration_date_gte=exp_gte.isoformat(),
            expiration_date_lte=exp_lte.isoformat(),
            limit=limit,
            sort="strike_price",
            order="asc",
        )
        result = []
        for c in contracts:
            exp_date = date.fromisoformat(c.expiration_date)
            dte = (exp_date - today).days
            result.append({
                "ticker": c.ticker,
                "strike": c.strike_price,
                "type": c.contract_type,
                "expiration_date": c.expiration_date,
                "dte": dte,
            })
        logger.info("Fetched %d %s contracts for %s (DTE %d-%d)", len(result), contract_type, ticker, dte_min, dte_max)
        return result
    except Exception as e:
        logger.warning("Failed to fetch option chain for %s: %s", ticker, e)
        return []


def fetch_chain_snapshot(
    ticker: str,
    option_ticker: str,
) -> dict | None:
    """Fetch live snapshot for a single option contract.

    Returns dict with: iv, delta, gamma, theta, vega, bid, ask, midpoint,
    last_price, open_interest, volume, break_even, underlying_price
    """
    client = _get_client()
    try:
        snap = client.get_snapshot_option(ticker, option_ticker)
        if snap is None:
            return None

        greeks = snap.greeks
        quote = snap.last_quote
        trade = snap.last_trade

        return {
            "iv": snap.implied_volatility,
            "delta": greeks.delta if greeks else None,
            "gamma": greeks.gamma if greeks else None,
            "theta": greeks.theta if greeks else None,
            "vega": greeks.vega if greeks else None,
            "bid": quote.bid if quote else None,
            "ask": quote.ask if quote else None,
            "midpoint": quote.midpoint if quote else None,
            "last_price": trade.price if trade else None,
            "volume": int(trade.size) if trade and trade.size else 0,
            "open_interest": int(snap.open_interest) if snap.open_interest else 0,
            "break_even": snap.break_even_price,
            "underlying_price": snap.underlying_asset.price if snap.underlying_asset else None,
        }
    except Exception as e:
        logger.warning("Failed to fetch snapshot for %s: %s", option_ticker, e)
        return None


def fetch_chain_with_snapshots(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
) -> list[dict]:
    """Fetch option contracts with live snapshots in batch.

    Returns list of dicts with contract info + live market data.
    Rate limit: 1 call to list_options_contracts + N calls to get_snapshot_option.
    """
    contracts = fetch_option_chain(ticker, contract_type, dte_min, dte_max)
    if not contracts:
        return []

    result = []
    for c in contracts:
        snap = fetch_chain_snapshot(ticker, c["ticker"])
        if snap:
            result.append({**c, **snap})
        else:
            result.append({**c, "iv": None, "bid": None, "ask": None})

    logger.info("Fetched snapshots for %d/%d contracts for %s", len(result), len(contracts), ticker)
    return result


def find_nearest_contract(
    contracts: list[dict],
    target_delta: float = 0.30,
) -> dict | None:
    """Find the contract with delta closest to target_delta.

    Contracts must have 'delta' key (from snapshot).
    """
    valid = [c for c in contracts if c.get("delta") is not None]
    if not valid:
        return None
    return min(valid, key=lambda c: abs(abs(c["delta"]) - abs(target_delta)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/options/test_polygon_chain.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/options/polygon_chain.py tests/engines/options/test_polygon_chain.py
git commit -m "feat: add live options chain fetcher from Polygon API"
```

---

## Task 2: Update `service.py` — Live Trade Generation Functions

**Files:**
- Modify: `backend/app/engines/options/service.py`
- Test: `tests/engines/options/test_service_live.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/engines/options/test_service_live.py
import pytest
from unittest.mock import patch, MagicMock


def test_generate_csp_live_uses_polygon_data():
    """generate_csp_live uses live bid/ask/IV from Polygon."""
    from app.engines.options.service import generate_csp_live

    live_data = {
        "strike": 195.0,
        "delta": -0.28,
        "iv": 0.32,
        "bid": 3.00,
        "ask": 3.20,
        "midpoint": 3.10,
        "open_interest": 500,
        "volume": 50,
        "gamma": 0.02,
        "theta": -0.05,
        "vega": 0.15,
        "underlying_price": 200.0,
        "dte": 30,
        "expiration_date": "2025-07-18",
    }

    result = generate_csp_live("AAPL", live_data)
    assert result is not None
    assert result.strike == 195.0
    assert result.bid == 3.00
    assert result.ask == 3.20
    assert result.open_interest == 500
    assert result.volume == 50
    assert result.implied_volatility == 0.32
    assert result.live_data is True


def test_generate_csp_live_returns_none_without_data():
    """generate_csp_live returns None if live_data is empty."""
    from app.engines.options.service import generate_csp_live
    result = generate_csp_live("AAPL", {})
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/engines/options/test_service_live.py -v`
Expected: FAIL with `ImportError: cannot import name 'generate_csp_live'`

- [ ] **Step 3: Add live generation functions to `service.py`**

Add these functions at the bottom of `backend/app/engines/options/service.py`:

```python
def generate_csp_live(ticker: str, live: dict) -> CSPOption | None:
    """Generate CSP trade using live Polygon data instead of Black-Scholes."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    T = live.get("dte", 30) / 365.0

    # Use live IV for probability calc, but use live delta directly
    iv = live.get("iv", 0.30)
    r = 0.05
    delta = live.get("delta", 0)
    if delta is not None and delta < 0:
        delta = abs(delta)  # CSP delta should be positive for display

    return CSPOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(delta, 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 30),
        annualized_yield=round(annualized_yield(premium, strike, live.get("dte", 30)), 4),
        probability_of_profit=round(
            probability_of_profit(underlying, strike, T, r, iv, "put", premium), 4
        ),
    )


def generate_leaps_live(ticker: str, live: dict) -> LEAPSOption | None:
    """Generate LEAPS trade using live Polygon data."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    iv = live.get("iv", 0.30)
    intrinsic = max(0.0, underlying - strike)
    time_val = premium - intrinsic
    leverage = (underlying / premium) if premium > 0 else 0.0

    return LEAPSOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(live.get("delta", 0.70) or 0.70, 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 180),
        leverage_factor=round(leverage, 2),
        intrinsic_value=round(intrinsic, 2),
        time_value=round(time_val, 2),
    )


def generate_covered_call_live(ticker: str, live: dict) -> CoveredCallOption | None:
    """Generate Covered Call trade using live Polygon data."""
    if not live or live.get("strike") is None or live.get("bid") is None:
        return None

    strike = live["strike"]
    underlying = live.get("underlying_price", 0)
    premium = live.get("midpoint") or ((live["bid"] + live["ask"]) / 2)
    iv = live.get("iv", 0.30)
    T = live.get("dte", 30) / 365.0

    return CoveredCallOption(
        ticker=ticker,
        strike=strike,
        expiration=live.get("expiration_date", ""),
        premium=round(premium, 2),
        implied_volatility=iv,
        delta=round(abs(live.get("delta", 0.30) or 0.30), 4),
        gamma=round(live.get("gamma", 0) or 0, 6),
        theta=round(live.get("theta", 0) or 0, 6),
        vega=round(live.get("vega", 0) or 0, 4),
        rho=0.0,
        bid=round(live["bid"], 2),
        ask=round(live["ask"], 2),
        last_price=round(live.get("last_price", premium) or premium, 2),
        open_interest=live.get("open_interest", 0) or 0,
        volume=live.get("volume", 0) or 0,
        underlying_price=underlying,
        days_to_expiration=live.get("dte", 30),
        annualized_yield=round(annualized_yield(premium, underlying, live.get("dte", 30)), 4),
        probability_of_profit=round(
            probability_of_profit(underlying, strike, T, 0.05, iv, "call", premium), 4
        ),
    )
```

Also add `live_data: bool = False` field to each schema in `schemas.py`:

```python
# In CSPOption, LEAPSOption, CoveredCallOption:
live_data: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/engines/options/test_service_live.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/options/service.py backend/app/engines/options/schemas.py tests/engines/options/test_service_live.py
git commit -m "feat: add live trade generation functions using Polygon data"
```

---

## Task 3: Update `generate.py` — Try Live Chain First, Fallback to Black-Scholes

**Files:**
- Modify: `backend/app/engines/trading/generate.py`

- [ ] **Step 1: Update `generate_trade()` to use live chain**

Replace the trade generation section in `generate_trade()` (lines 130-138) with:

```python
    # Try live Polygon options chain first
    live_trade = None
    live_data_used = False
    try:
        from app.engines.options.polygon_chain import fetch_chain_with_snapshots, find_nearest_contract

        contract_type = "put" if option_strategy in ("csp",) else "call"
        dte_min = max(7, dte - 10)
        dte_max = dte + 10

        live_contracts = fetch_chain_with_snapshots(ticker, contract_type, dte_min, dte_max)
        if live_contracts:
            nearest = find_nearest_contract(live_contracts, target_delta)
            if nearest and nearest.get("bid") is not None:
                nearest["underlying_price"] = underlying_price
                nearest["dte"] = dte
                if option_strategy == "csp":
                    live_trade = generate_csp_live(ticker, nearest)
                elif option_strategy == "leaps":
                    live_trade = generate_leaps_live(ticker, nearest)
                elif option_strategy == "covered_call":
                    live_trade = generate_covered_call_live(ticker, nearest)
                if live_trade:
                    live_trade.live_data = True
                    live_data_used = True
    except Exception as e:
        logger.warning("Live options chain failed for %s, falling back to Black-Scholes: %s", ticker, e)

    # Fallback to Black-Scholes if live chain didn't work
    if not live_trade:
        if option_strategy == "csp":
            live_trade = generate_csp(ticker, underlying_price, iv, dte, target_delta)
        elif option_strategy == "leaps":
            live_trade = generate_leaps(ticker, underlying_price, iv, max(dte, 180), 0.70)
        elif option_strategy == "pmcc":
            live_trade = generate_pmcc(ticker, underlying_price, iv, max(dte, 180), 0.70)
        elif option_strategy == "covered_call":
            live_trade = generate_covered_call(ticker, underlying_price, iv, dte, target_delta)

    trade = live_trade
```

Also add the new imports at the top:

```python
from app.engines.options.service import (
    generate_csp, generate_leaps, generate_pmcc, generate_covered_call,
    generate_csp_live, generate_leaps_live, generate_covered_call_live,
)
```

- [ ] **Step 2: Update the return dict to include `live_data` flag**

Change the return statement to:

```python
    return {
        "ticker": ticker,
        "strategy_output": strategy_output.model_dump(),
        "trade": trade.model_dump() if trade else None,
        "live_data": live_data_used,
        "context": {
            "regime": context["regime"],
            "momentum": context["momentum"],
            "rsi": context["rsi"],
            "iv_percentile": context["iv_percentile"],
            "drawdown": context["drawdown"],
        },
    }
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/engines/trading/generate.py
git commit -m "feat: try live Polygon options chain before Black-Scholes fallback"
```

---

## Task 4: Fix Ticker Details Cache — Auto-Refresh if Empty

**Files:**
- Modify: `backend/app/engines/data/ticker_details.py`

- [ ] **Step 1: Add auto-refresh logic to `get_ticker_details`**

Update the `get_ticker_details` function to auto-refresh if the cache is empty:

```python
def get_ticker_details(tickers: list[str] | None = None) -> dict[str, dict]:
    """Get ticker details with live prices from Polygon snapshots."""
    global _cache
    if _cache is None:
        _cache = _load_cache()

    # Auto-refresh if cache is empty
    if not _cache:
        logger.info("Ticker details cache is empty, refreshing from Polygon API")
        refresh_ticker_details()

    result = {}
    for t in (tickers or []):
        info = dict(_cache.get(t, {}))
        result[t] = info

    # Fetch live prices from Polygon snapshots
    if tickers:
        live_prices = _fetch_live_prices(tickers)
        for t in tickers:
            if t in live_prices:
                result[t]["last_price"] = live_prices[t]

    if not tickers:
        return _cache
    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/engines/data/ticker_details.py
git commit -m "fix: auto-refresh ticker details cache if empty"
```

---

## Task 5: Update Frontend — Show Live Data in TradeGenerationModal

**Files:**
- Modify: `frontend/src/components/shared/TradeGenerationModal.js`

- [ ] **Step 1: Add live data state and badge**

Add state for live data at the top of the component:

```javascript
const [liveData, setLiveData] = useState(false);
```

Update `fetchTrade` to capture the flag:

```javascript
const fetchTrade = async () => {
    setLoading(true);
    setError(null);
    setTrade(null);
    setStrategy(null);
    setContext(null);
    setLiveData(false);
    try {
      const data = await generateTrade(ticker, dte, targetDelta);
      setTrade(data.trade);
      setStrategy(data.strategy_output);
      setContext(data.context);
      setLiveData(data.live_data || false);
      if (!data.trade) {
        setError(data.message || 'No trade generated for this recommendation');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
```

- [ ] **Step 2: Add live data badge in the header**

After the strategy confidence display (around line 77), add:

```javascript
{liveData && (
  <span className="px-2 py-0.5 text-xs font-mono rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
    LIVE DATA
  </span>
)}
{!liveData && trade && (
  <span className="px-2 py-0.5 text-xs font-mono rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
    CALCULATED
  </span>
)}
```

- [ ] **Step 3: Add bid/ask spread, OI, and volume display**

After the existing trade details grid, add a new section:

```javascript
{/* Live Market Data */}
{trade && (trade.bid != null || trade.open_interest != null) && (
  <div className="mt-4 p-3 rounded-lg bg-terminal-bg-light">
    <p className="text-xs font-mono text-terminal-text-muted mb-2">Market Data</p>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
      {trade.bid != null && (
        <div>
          <p className="text-terminal-text-muted">Bid</p>
          <p className="text-terminal-text">{formatCurrency(trade.bid)}</p>
        </div>
      )}
      {trade.ask != null && (
        <div>
          <p className="text-terminal-text-muted">Ask</p>
          <p className="text-terminal-text">{formatCurrency(trade.ask)}</p>
        </div>
      )}
      {trade.bid != null && trade.ask != null && (
        <div>
          <p className="text-terminal-text-muted">Spread</p>
          <p className="text-terminal-text">{formatCurrency(trade.ask - trade.bid)}</p>
        </div>
      )}
      {trade.open_interest != null && trade.open_interest > 0 && (
        <div>
          <p className="text-terminal-text-muted">Open Interest</p>
          <p className="text-terminal-text">{trade.open_interest.toLocaleString()}</p>
        </div>
      )}
      {trade.volume != null && trade.volume > 0 && (
        <div>
          <p className="text-terminal-text-muted">Volume</p>
          <p className="text-terminal-text">{trade.volume.toLocaleString()}</p>
        </div>
      )}
      {trade.implied_volatility != null && (
        <div>
          <p className="text-terminal-text-muted">IV</p>
          <p className="text-terminal-text">{(trade.implied_volatility * 100).toFixed(1)}%</p>
        </div>
      )}
    </div>
  </div>
)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/shared/TradeGenerationModal.js
git commit -m "feat: show live data badge, bid/ask, OI, volume in trade modal"
```

---

## Task 6: Add `live_data` Field to Option Schemas

**Files:**
- Modify: `backend/app/engines/options/schemas.py`

- [ ] **Step 1: Add `live_data` field to all option schemas**

Add `live_data: bool = False` to CSPOption, LEAPSOption, PMMCOption, and CoveredCallOption:

```python
class CSPOption(BaseModel):
    # ... existing fields ...
    live_data: bool = False

class LEAPSOption(BaseModel):
    # ... existing fields ...
    live_data: bool = False

class PMMCOption(BaseModel):
    # ... existing fields ...
    live_data: bool = False

class CoveredCallOption(BaseModel):
    # ... existing fields ...
    live_data: bool = False
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/engines/options/schemas.py
git commit -m "feat: add live_data field to option schemas"
```

---

## Task 7: Verify End-to-End

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Check for lint/type errors**

Run: `cd backend && python -m ruff check app/engines/options/ app/engines/trading/`
Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 3: Deploy and test on Oracle Cloud**

1. Push changes to the repo
2. Pull on the Oracle Cloud instance
3. Restart the backend
4. Open the Opportunities page
5. Click "Stocks" filter — should now show stock opportunities
6. Click "Generate Trade" on any ticker
7. Verify the "LIVE DATA" badge appears (or "CALCULATED" if Polygon fails)
8. Verify bid/ask, OI, volume are displayed

---

## Summary

| Task | What It Does | Est. Time |
|------|-------------|-----------|
| 1 | Create `polygon_chain.py` with live fetcher | 10 min |
| 2 | Add `generate_csp_live()` etc. to service | 10 min |
| 3 | Update `generate.py` to try live chain first | 5 min |
| 4 | Fix ticker details cache auto-refresh | 5 min |
| 5 | Update frontend modal with live data UI | 10 min |
| 6 | Add `live_data` field to schemas | 2 min |
| 7 | Verify end-to-end | 10 min |

**Total: ~50 minutes**
