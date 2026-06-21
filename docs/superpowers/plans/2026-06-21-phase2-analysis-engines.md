# Phase 2: Analysis Engines — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 4 analysis engines (Feature Engineering, Market Regime/HMM, Change Point/CUSUM, Breakout Detection) that consume market data from Phase 1 and produce signals stored as Parquet files, with full TDD coverage and FastAPI/Celery wiring.

**Architecture:** Each engine lives under `backend/app/engines/<name>/` with `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py`. Services are pure functions/computation classes with no I/O side effects except save/load. Celery tasks orchestrate per-ticker computation at scale. Signals are stored as daily Parquet files under `signals/<type>/<date>.parquet`. The Phase 1 `PolygonDataService.load_ohlcv()` loads input data.

**Tech Stack:** Python 3.12, numpy, pandas, scipy, scikit-learn, hmmlearn, FastAPI, Celery, pytest, unittest.mock

---

### Prerequisite: Update requirements.txt for Phase 2 libraries

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new dependencies**

Append to `backend/requirements.txt`:

```
# ML / Analysis
hmmlearn==0.3.2
scikit-learn==1.5.2
scipy==1.14.1
```

- [ ] **Step 2: Verify**

Run: `cd backend && pip install -r requirements-dev.txt 2>&1 | tail -5`
Expected: All packages install cleanly

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add hmmlearn, scikit-learn, scipy for Phase 2 analysis engines"
```

---


### Task 1: Feature Engineering Engine — Shared Schemas

**Files:**
- Create: `backend/app/engines/__init__.py`
- Create: `backend/app/engines/features/__init__.py`
- Create: `backend/app/engines/features/schemas.py`
- Test: `backend/tests/engines/features/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/features/test_schemas.py`:

```python
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestFeatureSchemas:
    def test_indicator_request_valid(self):
        from app.engines.features.schemas import IndicatorRequest
        req = IndicatorRequest(ticker="AAPL")
        assert req.ticker == "AAPL"
        assert req.days == 365

    def test_indicator_request_uppercases_ticker(self):
        from app.engines.features.schemas import IndicatorRequest
        req = IndicatorRequest(ticker="aapl")
        assert req.ticker == "AAPL"

    def test_indicator_request_rejects_empty_ticker(self):
        from app.engines.features.schemas import IndicatorRequest
        with pytest.raises(ValidationError):
            IndicatorRequest(ticker="")

    def test_indicator_response_valid(self):
        from app.engines.features.schemas import IndicatorResponse
        resp = IndicatorResponse(
            ticker="AAPL",
            indicators={"ema_20": 155.0, "rsi_14": 62.5},
            bars_analyzed=252,
        )
        assert resp.ticker == "AAPL"
        assert resp.indicators["ema_20"] == 155.0
        assert resp.bars_analyzed == 252

    def test_engine_health_response(self):
        from app.engines.features.schemas import EngineHealthResponse
        health = EngineHealthResponse(engine="features")
        assert health.engine == "features"
        assert health.status == "healthy"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/__init__.py` (empty).
Create `backend/app/engines/features/__init__.py` (empty).
Create `backend/app/engines/features/schemas.py`:

```python
from datetime import datetime, timezone
from pydantic import BaseModel, field_validator


class IndicatorRequest(BaseModel):
    ticker: str
    days: int = 365

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("ticker cannot be empty")
        return stripped.upper()


class IndicatorResponse(BaseModel):
    ticker: str
    indicators: dict[str, float]
    bars_analyzed: int
    generated_at: datetime = datetime.now(timezone.utc)
    engine_version: str = "0.1.0"


class EngineHealthResponse(BaseModel):
    engine: str
    status: str = "healthy"
    uptime_hours: float = 0.0
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/__init__.py backend/app/engines/features/__init__.py backend/app/engines/features/schemas.py backend/tests/engines/features/test_schemas.py
git commit -m "feat: add feature engineering schemas with validation"
```

---


### Task 2: Feature Engineering Service — Trend Indicators

**Files:**
- Create: `backend/app/engines/features/service.py`
- Test: `backend/tests/engines/features/test_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/features/test_service.py`:

```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    np.random.seed(42)
    price = 150.0 + np.cumsum(np.random.normal(0, 1, 300))
    return pd.DataFrame({
        "timestamp": dates,
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(500000, 2000000, 300),
    })


class TestTrendIndicators:
    def test_compute_ema(self, sample_ohlcv):
        from app.engines.features.service import compute_ema
        ema = compute_ema(sample_ohlcv["close"], period=20)
        assert len(ema) == 300
        assert not ema.isnull().all()
        assert isinstance(ema.iloc[-1], float)

    def test_ema_short_window(self, sample_ohlcv):
        from app.engines.features.service import compute_ema
        ema = compute_ema(sample_ohlcv["close"], period=3)
        assert len(ema) == 300

    def test_ema_returns_nan_for_insufficient_data(self):
        from app.engines.features.service import compute_ema
        values = pd.Series([100.0, 101.0, 102.0])
        ema = compute_ema(values, period=10)
        assert pd.isna(ema.iloc[-1])

    def test_compute_sma(self, sample_ohlcv):
        from app.engines.features.service import compute_sma
        sma = compute_sma(sample_ohlcv["close"], period=50)
        assert len(sma) == 300
        assert not sma.isnull().all()

    def test_sma_returns_nan_for_insufficient_data(self):
        from app.engines.features.service import compute_sma
        values = pd.Series([100.0, 101.0])
        sma = compute_sma(values, period=10)
        assert pd.isna(sma.iloc[-1])

    def test_compute_all_trend(self, sample_ohlcv):
        from app.engines.features.service import compute_all_trend
        result = compute_all_trend(sample_ohlcv["close"])
        assert "ema_20" in result
        assert "ema_50" in result
        assert "ema_200" in result
        assert "sma_50" in result
        assert "sma_200" in result
        assert all(isinstance(v, float) for v in result.values())
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestTrendIndicators -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/features/service.py`:

```python
import pandas as pd
import numpy as np


def compute_ema(values: pd.Series, period: int) -> pd.Series:
    return values.ewm(span=period, adjust=False).mean()


def compute_sma(values: pd.Series, period: int) -> pd.Series:
    return values.rolling(window=period).mean()


def compute_all_trend(close: pd.Series) -> dict[str, float]:
    return {
        "ema_20": _safe_last(compute_ema(close, 20)),
        "ema_50": _safe_last(compute_ema(close, 50)),
        "ema_200": _safe_last(compute_ema(close, 200)),
        "sma_50": _safe_last(compute_sma(close, 50)),
        "sma_200": _safe_last(compute_sma(close, 200)),
    }


def _safe_last(series: pd.Series) -> float:
    val = series.iloc[-1]
    return float(val) if pd.notna(val) else 0.0
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestTrendIndicators -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/features/service.py backend/tests/engines/features/test_service.py
git commit -m "feat: add trend indicators (EMA20/50/200, SMA50/200) to feature engineering"
```

---


### Task 3: Feature Engineering Service — Momentum Indicators

**Files:**
- Modify: `backend/app/engines/features/service.py`
- Modify: `backend/tests/engines/features/test_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/engines/features/test_service.py`:

```python
class TestMomentumIndicators:
    def test_compute_rsi(self, sample_ohlcv):
        from app.engines.features.service import compute_rsi
        rsi = compute_rsi(sample_ohlcv["close"], period=14)
        assert len(rsi) == 300
        last = rsi.iloc[-1]
        assert 0 <= last <= 100

    def test_rsi_constant_price(self):
        from app.engines.features.service import compute_rsi
        values = pd.Series([100.0] * 50)
        rsi = compute_rsi(values, period=14)
        assert rsi.iloc[-1] == 50.0

    def test_rsi_uptrend(self):
        from app.engines.features.service import compute_rsi
        values = pd.Series(np.linspace(100, 200, 100))
        rsi = compute_rsi(values, period=14)
        assert rsi.iloc[-1] > 50

    def test_compute_macd(self, sample_ohlcv):
        from app.engines.features.service import compute_macd
        macd, signal, hist = compute_macd(sample_ohlcv["close"])
        assert len(macd) == 300
        assert len(signal) == 300
        assert len(hist) == 300
        assert isinstance(macd.iloc[-1], float)

    def test_compute_roc(self, sample_ohlcv):
        from app.engines.features.service import compute_roc
        roc = compute_roc(sample_ohlcv["close"], period=10)
        assert len(roc) == 300
        assert isinstance(roc.iloc[-1], float)

    def test_compute_ppo(self, sample_ohlcv):
        from app.engines.features.service import compute_ppo
        ppo = compute_ppo(sample_ohlcv["close"])
        assert len(ppo) == 300
        assert isinstance(ppo.iloc[-1], float)

    def test_compute_stochastic(self, sample_ohlcv):
        from app.engines.features.service import compute_stochastic
        k, d = compute_stochastic(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        assert len(k) == 300
        assert len(d) == 300
        assert 0 <= k.iloc[-1] <= 100
        assert 0 <= d.iloc[-1] <= 100

    def test_compute_all_momentum(self, sample_ohlcv):
        from app.engines.features.service import compute_all_momentum
        result = compute_all_momentum(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        assert "rsi_14" in result
        assert "macd" in result
        assert "macd_signal" in result
        assert "macd_hist" in result
        assert "roc_10" in result
        assert "ppo" in result
        assert "stoch_k" in result
        assert "stoch_d" in result
        assert all(isinstance(v, float) for v in result.values())
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestMomentumIndicators -v`
Expected: FAIL (function not found)

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/engines/features/service.py`:

```python
def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd = ema_fast - ema_slow
    signal = compute_ema(macd, signal_period)
    hist = macd - signal
    return macd, signal, hist


def compute_roc(close: pd.Series, period: int = 10) -> pd.Series:
    return close.pct_change(periods=period) * 100.0


def compute_ppo(close: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    return ((ema_fast - ema_slow) / ema_slow) * 100.0


def compute_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    k = 100.0 * ((close - low_min) / (high_max - low_min).replace(0, np.nan))
    d = k.rolling(window=d_period).mean()
    return k, d


def compute_all_momentum(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, float]:
    macd, macd_signal, macd_hist = compute_macd(close)
    stoch_k, stoch_d = compute_stochastic(high, low, close)
    return {
        "rsi_14": _safe_last(compute_rsi(close, 14)),
        "macd": _safe_last(macd),
        "macd_signal": _safe_last(macd_signal),
        "macd_hist": _safe_last(macd_hist),
        "roc_10": _safe_last(compute_roc(close, 10)),
        "ppo": _safe_last(compute_ppo(close)),
        "stoch_k": _safe_last(stoch_k),
        "stoch_d": _safe_last(stoch_d),
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestMomentumIndicators -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/features/service.py backend/tests/engines/features/test_service.py
git commit -m "feat: add momentum indicators (RSI, MACD, ROC, PPO, Stochastic)"
```

---


### Task 4: Feature Engineering Service — Volatility & Volume Indicators

**Files:**
- Modify: `backend/app/engines/features/service.py`
- Modify: `backend/tests/engines/features/test_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/engines/features/test_service.py`:

```python
class TestVolatilityIndicators:
    def test_compute_atr(self, sample_ohlcv):
        from app.engines.features.service import compute_atr
        atr = compute_atr(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], period=14)
        assert len(atr) == 300
        assert atr.iloc[-1] > 0

    def test_compute_historical_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_historical_volatility
        hv = compute_historical_volatility(sample_ohlcv["close"], window=21)
        assert len(hv) == 300
        assert hv.iloc[-1] >= 0

    def test_compute_realized_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_realized_volatility
        rv = compute_realized_volatility(sample_ohlcv["close"], window=21)
        assert len(rv) == 300
        assert rv.iloc[-1] >= 0

    def test_compute_bollinger_width(self, sample_ohlcv):
        from app.engines.features.service import compute_bollinger_width
        width = compute_bollinger_width(sample_ohlcv["close"], period=20)
        assert len(width) == 300
        assert width.iloc[-1] >= 0

    def test_compute_all_volatility(self, sample_ohlcv):
        from app.engines.features.service import compute_all_volatility
        result = compute_all_volatility(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        assert "atr_14" in result
        assert "historical_vol_21" in result
        assert "realized_vol_21" in result
        assert "bollinger_width" in result
        assert all(isinstance(v, float) for v in result.values())


class TestVolumeIndicators:
    def test_compute_relative_volume(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_volume
        rvol = compute_relative_volume(sample_ohlcv["volume"], window=21)
        assert len(rvol) == 300
        assert rvol.iloc[-1] >= 0

    def test_compute_obv(self, sample_ohlcv):
        from app.engines.features.service import compute_obv
        obv = compute_obv(sample_ohlcv["close"], sample_ohlcv["volume"])
        assert len(obv) == 300
        assert isinstance(obv.iloc[-1], (int, float))

    def test_compute_accumulation_distribution(self, sample_ohlcv):
        from app.engines.features.service import compute_accumulation_distribution
        ad = compute_accumulation_distribution(
            sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], sample_ohlcv["volume"]
        )
        assert len(ad) == 300
        assert isinstance(ad.iloc[-1], (int, float))

    def test_compute_all_volume(self, sample_ohlcv):
        from app.engines.features.service import compute_all_volume
        result = compute_all_volume(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], sample_ohlcv["volume"])
        assert "relative_volume_21" in result
        assert "obv" in result
        assert "acc_dist" in result
        assert all(isinstance(v, float) for v in result.values())
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestVolatilityIndicators tests/engines/features/test_service.py::TestVolumeIndicators -v`
Expected: FAIL (functions not found)

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/engines/features/service.py`:

```python
# --- Volatility Indicators ---

def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def compute_historical_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    log_returns = np.log(close / close.shift())
    return log_returns.rolling(window=window).std() * np.sqrt(252)


def compute_realized_volatility(close: pd.Series, window: int = 21) -> pd.Series:
    returns = close.pct_change()
    return returns.rolling(window=window).std() * np.sqrt(252)


def compute_bollinger_width(close: pd.Series, period: int = 20) -> pd.Series:
    sma = compute_sma(close, period)
    std = close.rolling(window=period).std()
    return 2.0 * std / sma.replace(0, np.nan)


def compute_all_volatility(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, float]:
    return {
        "atr_14": _safe_last(compute_atr(high, low, close, 14)),
        "historical_vol_21": _safe_last(compute_historical_volatility(close, 21)),
        "realized_vol_21": _safe_last(compute_realized_volatility(close, 21)),
        "bollinger_width": _safe_last(compute_bollinger_width(close, 20)),
    }


# --- Volume Indicators ---

def compute_relative_volume(volume: pd.Series, window: int = 21) -> pd.Series:
    avg_volume = volume.rolling(window=window).mean()
    return volume / avg_volume.replace(0, np.nan)


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()


def compute_accumulation_distribution(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    return (clv * volume).cumsum()


def compute_all_volume(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> dict[str, float]:
    return {
        "relative_volume_21": _safe_last(compute_relative_volume(volume, 21)),
        "obv": float(compute_obv(close, volume).iloc[-1]),
        "acc_dist": float(compute_accumulation_distribution(high, low, close, volume).iloc[-1]),
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestVolatilityIndicators tests/engines/features/test_service.py::TestVolumeIndicators -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/features/service.py backend/tests/engines/features/test_service.py
git commit -m "feat: add volatility (ATR, HV, RV, Bollinger width) and volume indicators"
```

---


### Task 5: Feature Engineering Service — Market Relative & Full Pipeline

**Files:**
- Modify: `backend/app/engines/features/service.py`
- Modify: `backend/tests/engines/features/test_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/engines/features/test_service.py`:

```python
class TestMarketRelativeIndicators:
    def test_compute_relative_strength(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        spy = sample_ohlcv["close"] * 1.0
        rs = compute_relative_strength(sample_ohlcv["close"], spy)
        assert len(rs) == 300
        assert isinstance(rs.iloc[-1], float)

    def test_rs_diverging_up(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        ticker = sample_ohlcv["close"] * 1.0
        spy = sample_ohlcv["close"] * 0.5
        rs = compute_relative_strength(ticker, spy)
        assert rs.iloc[-1] > 1.0

    def test_rs_diverging_down(self, sample_ohlcv):
        from app.engines.features.service import compute_relative_strength
        ticker = sample_ohlcv["close"] * 0.5
        spy = sample_ohlcv["close"] * 1.0
        rs = compute_relative_strength(ticker, spy)
        assert rs.iloc[-1] < 1.0

    def test_compute_all_market_relative(self, sample_ohlcv):
        from app.engines.features.service import compute_all_market_relative
        spy = sample_ohlcv["close"] * 1.02
        result = compute_all_market_relative(sample_ohlcv["close"], spy, spy)
        assert "rs_vs_spy" in result
        assert "rs_vs_sector" in result
        assert all(isinstance(v, float) for v in result.values())


class TestFullFeaturePipeline:
    def test_compute_all_indicators(self, sample_ohlcv):
        from app.engines.features.service import compute_all_indicators
        spy = sample_ohlcv["close"] * 1.02
        result = compute_all_indicators(sample_ohlcv, spy_close=spy, sector_close=spy)
        expected_keys = [
            "ema_20", "ema_50", "ema_200", "sma_50", "sma_200",
            "rsi_14", "macd", "macd_signal", "macd_hist", "roc_10", "ppo", "stoch_k", "stoch_d",
            "atr_14", "historical_vol_21", "realized_vol_21", "bollinger_width",
            "relative_volume_21", "obv", "acc_dist",
            "rs_vs_spy", "rs_vs_sector",
        ]
        for key in expected_keys:
            assert key in result, f"Missing indicator: {key}"
            assert isinstance(result[key], float), f"{key} is not float"

    def test_compute_all_indicators_empty_data(self):
        from app.engines.features.service import compute_all_indicators
        empty = pd.DataFrame()
        result = compute_all_indicators(empty, spy_close=pd.Series(), sector_close=pd.Series())
        assert result == {}

    def test_compute_all_indicators_single_bar(self):
        from app.engines.features.service import compute_all_indicators
        df = pd.DataFrame({
            "close": [150.0],
            "high": [155.0],
            "low": [149.0],
            "volume": [1000000],
        })
        result = compute_all_indicators(df, spy_close=pd.Series([150.0]), sector_close=pd.Series([150.0]))
        assert isinstance(result, dict)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py::TestMarketRelativeIndicators tests/engines/features/test_service.py::TestFullFeaturePipeline -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/engines/features/service.py`:

```python
# --- Market Relative Indicators ---

def compute_relative_strength(ticker_close: pd.Series, benchmark_close: pd.Series) -> pd.Series:
    ticker_norm = ticker_close / ticker_close.iloc[0]
    bench_norm = benchmark_close / benchmark_close.iloc[0]
    return ticker_norm / bench_norm.replace(0, np.nan)


def compute_all_market_relative(
    close: pd.Series,
    spy_close: pd.Series,
    sector_close: pd.Series,
) -> dict[str, float]:
    if close.empty or spy_close.empty:
        return {"rs_vs_spy": 0.0, "rs_vs_sector": 0.0}
    return {
        "rs_vs_spy": _safe_last(compute_relative_strength(close, spy_close)),
        "rs_vs_sector": _safe_last(compute_relative_strength(close, sector_close))
        if not sector_close.empty else 0.0,
    }


# --- Full Pipeline ---

def compute_all_indicators(
    ohlcv: pd.DataFrame,
    spy_close: pd.Series | None = None,
    sector_close: pd.Series | None = None,
) -> dict[str, float]:
    if ohlcv.empty:
        return {}
    close = ohlcv["close"]
    high = ohlcv["high"]
    low = ohlcv["low"]
    volume = ohlcv["volume"]

    result = {}
    result.update(compute_all_trend(close))
    result.update(compute_all_momentum(high, low, close))
    result.update(compute_all_volatility(high, low, close))
    result.update(compute_all_volume(high, low, close, volume))

    spy = spy_close if spy_close is not None else pd.Series()
    sector = sector_close if sector_close is not None else pd.Series()
    result.update(compute_all_market_relative(close, spy, sector))

    return {k: float(v) for k, v in result.items()}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_service.py -v`
Expected: All test classes PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/features/service.py backend/tests/engines/features/test_service.py
git commit -m "feat: add market relative indicators and full feature pipeline"
```

---


### Task 6: Feature Engineering Engine — Celery Tasks & FastAPI Router

**Files:**
- Create: `backend/app/engines/features/tasks.py`
- Create: `backend/app/engines/features/router.py`
- Test: `backend/tests/engines/features/test_tasks.py`
- Test: `backend/tests/engines/features/test_router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/features/test_tasks.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestFeatureTasks:
    @patch("app.engines.features.tasks.PolygonDataService")
    @patch("app.engines.features.tasks.compute_all_indicators")
    def test_compute_features_task(self, mock_compute, mock_ds):
        from app.engines.features.tasks import compute_features
        import pandas as pd
        df = pd.DataFrame({"close": [150.0, 151.0], "high": [155.0, 156.0], "low": [149.0, 150.0], "volume": [1000, 2000]})
        mock_ds.return_value.load_ohlcv.return_value = df
        mock_compute.return_value = {"ema_20": 150.5, "rsi_14": 55.0}
        result = compute_features("AAPL", days=365)
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["indicators_count"] == 2

    @patch("app.engines.features.tasks.PolygonDataService")
    def test_compute_features_no_data(self, mock_ds):
        from app.engines.features.tasks import compute_features
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_features("UNKNOWN")
        assert result["status"] == "error"
        assert "no data" in result["message"]

    @patch("app.engines.features.tasks.PolygonDataService")
    def test_compute_features_fetch_error(self, mock_ds):
        from app.engines.features.tasks import compute_features
        mock_ds.return_value.load_ohlcv.side_effect = Exception("DB error")
        result = compute_features("AAPL")
        assert result["status"] == "error"

    @patch("app.engines.features.tasks.compute_features")
    def test_compute_all_features_task(self, mock_compute):
        from app.engines.features.tasks import compute_all_features
        from app.models.universe import DEFAULT_UNIVERSE
        mock_compute.return_value = {"ticker": "TEST", "status": "success", "indicators_count": 1}
        results = compute_all_features()
        assert len(results) == len(DEFAULT_UNIVERSE)
```

Create `backend/tests/engines/features/test_router.py`:

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


class TestFeaturesRouter:
    async def test_get_indicators(self, client):
        resp = await client.get("/api/v1/analysis/indicators/AAPL?days=365")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticker" in data
        assert data["ticker"] == "AAPL"

    async def test_get_indicators_no_data(self, client):
        resp = await client.get("/api/v1/analysis/indicators/UNKNOWN?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["bars_analyzed"] == 0

    @patch("app.engines.features.router.compute_features")
    async def test_post_compute_features(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-456")
        resp = await client.post("/api/v1/analysis/indicators/compute/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-456"

    async def test_features_health(self, client):
        resp = await client.get("/api/v1/analysis/features/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine"] == "features"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/features/test_tasks.py tests/engines/features/test_router.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/features/tasks.py`:

```python
import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.features.service import compute_all_indicators
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_features(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        spy_df = service.load_ohlcv("SPY", days=days)
        spy_close = spy_df["close"] if not spy_df.empty else pd.Series()

        result = compute_all_indicators(df, spy_close=spy_close)
        _save_indicators(ticker, result)

        logger.info("Computed %d features for %s", len(result), ticker)
        return {
            "ticker": ticker,
            "status": "success",
            "indicators_count": len(result),
            "message": f"Computed {len(result)} features for {ticker}",
        }
    except Exception as e:
        logger.exception("Failed to compute features for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_features(days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_features.delay(ticker, days=days)
        results.append(result)
    return results


def _save_indicators(ticker: str, indicators: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "indicators")
    os.makedirs(signals_dir, exist_ok=True)
    path = os.path.join(signals_dir, f"{ticker.lower()}_{date_str}.parquet")
    df = pd.DataFrame([{"ticker": ticker, "date": date_str, **indicators}])
    df.to_parquet(path, index=False)
    return path
```

Create `backend/app/engines/features/router.py`:

```python
import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.features.schemas import IndicatorResponse, EngineHealthResponse
from app.engines.features.service import compute_all_indicators
from app.engines.features.tasks import compute_features as compute_features_task
from app.engines.data.service import PolygonDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/indicators/{ticker}")
def get_indicators(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return IndicatorResponse(ticker=ticker.upper(), indicators={}, bars_analyzed=0)
    spy_df = service.load_ohlcv("SPY", days=days)
    spy_close = spy_df["close"] if not spy_df.empty else None
    indicators = compute_all_indicators(df, spy_close=spy_close)
    return IndicatorResponse(
        ticker=ticker.upper(),
        indicators=indicators,
        bars_analyzed=len(df),
    )


@router.post("/indicators/compute/{ticker}", status_code=202)
def compute_indicators(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_features_task.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/indicators/compute-all", status_code=202)
def compute_all_indicators_endpoint(_=Depends(verify_api_key)):
    from app.engines.features.tasks import compute_all_features
    task = compute_all_features.delay()
    return {"task_id": task.id, "status": "queued", "message": "Computing features for all tickers"}


@router.get("/features/health")
def features_health():
    return EngineHealthResponse(engine="features")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/features/test_tasks.py tests/engines/features/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/features/router.py backend/app/engines/features/tasks.py backend/tests/engines/features/test_tasks.py backend/tests/engines/features/test_router.py
git commit -m "feat: add Celery tasks and FastAPI router for feature engineering"
```

---


### Task 7: Market Regime Engine — HMM Service

**Files:**
- Create: `backend/app/engines/regime/__init__.py`
- Create: `backend/app/engines/regime/schemas.py`
- Create: `backend/app/engines/regime/service.py`
- Test: `backend/tests/engines/regime/test_schemas.py`
- Test: `backend/tests/engines/regime/test_service.py`

- [ ] **Step 1: Write the failing tests for schemas**

Create `backend/tests/engines/regime/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError


class TestRegimeSchemas:
    def test_regime_prediction_valid(self):
        from app.engines.regime.schemas import RegimePrediction
        pred = RegimePrediction(
            regime="Bull", probability=0.85, confidence=0.75,
            explanation="Strong uptrend with low volatility",
        )
        assert pred.regime == "Bull"
        assert 0 <= pred.probability <= 1
        assert 0 <= pred.confidence <= 1

    def test_regime_prediction_rejects_invalid_regime(self):
        from app.engines.regime.schemas import RegimePrediction
        with pytest.raises(ValidationError):
            RegimePrediction(regime="Invalid", probability=0.5, confidence=0.5, explanation="")

    def test_regime_prediction_rejects_probability_out_of_range(self):
        from app.engines.regime.schemas import RegimePrediction
        with pytest.raises(ValidationError):
            RegimePrediction(regime="Bull", probability=1.5, confidence=0.5, explanation="")

    def test_regime_prediction_rejects_negative_probability(self):
        from app.engines.regime.schemas import RegimePrediction
        with pytest.raises(ValidationError):
            RegimePrediction(regime="Bull", probability=-0.1, confidence=0.5, explanation="")

    def test_regime_request_valid(self):
        from app.engines.regime.schemas import RegimeRequest
        req = RegimeRequest(ticker="SPY")
        assert req.ticker == "SPY"
        assert req.n_states == 4
        assert req.lookback_days == 756

    def test_regime_request_rejects_invalid_n_states(self):
        from app.engines.regime.schemas import RegimeRequest
        with pytest.raises(ValidationError):
            RegimeRequest(ticker="SPY", n_states=1)
        with pytest.raises(ValidationError):
            RegimeRequest(ticker="SPY", n_states=7)

    def test_available_regimes_list(self):
        from app.engines.regime.schemas import AVAILABLE_REGIMES
        assert len(AVAILABLE_REGIMES) == 6
        assert "Bull" in AVAILABLE_REGIMES
        assert "Bear" in AVAILABLE_REGIMES
        assert "Crisis" in AVAILABLE_REGIMES
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/regime/test_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Create schemas.py**

Create `backend/app/engines/regime/schemas.py`:

```python
from pydantic import BaseModel, field_validator

AVAILABLE_REGIMES = ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]


class RegimePrediction(BaseModel):
    regime: str
    probability: float
    confidence: float
    explanation: str = ""

    @field_validator("regime")
    @classmethod
    def validate_regime(cls, v: str) -> str:
        if v not in AVAILABLE_REGIMES:
            raise ValueError(f"Invalid regime: {v}. Must be one of {AVAILABLE_REGIMES}")
        return v

    @field_validator("probability", "confidence")
    @classmethod
    def validate_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        return v


class RegimeRequest(BaseModel):
    ticker: str = "SPY"
    n_states: int = 4
    lookback_days: int = 756

    @field_validator("n_states")
    @classmethod
    def validate_n_states(cls, v: int) -> int:
        if not 2 <= v <= 6:
            raise ValueError("n_states must be between 2 and 6")
        return v


class RegimeResponse(BaseModel):
    ticker: str
    overall_regime: RegimePrediction
    state_probabilities: dict[str, float]
    trained_on_bars: int
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/regime/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for regime service**

Create `backend/tests/engines/regime/test_service.py`:

```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def spy_returns():
    np.random.seed(42)
    n = 500
    returns = np.random.normal(0.0005, 0.01, n)
    return pd.Series(returns, name="close")


@pytest.fixture
def spy_returns_bull():
    np.random.seed(99)
    n = 500
    returns = np.random.normal(0.001, 0.005, n)
    return pd.Series(returns, name="close")


@pytest.fixture
def spy_returns_bear():
    np.random.seed(99)
    n = 500
    returns = np.random.normal(-0.001, 0.015, n)
    return pd.Series(returns, name="close")


class TestRegimeService:
    def test_fit_and_predict_hmm(self, spy_returns):
        from app.engines.regime.service import fit_hmm
        model, _ = fit_hmm(spy_returns, n_states=4)
        assert model is not None
        assert model.n_components == 4

    def test_predict_regime_returns_valid_output(self, spy_returns):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns, n_states=4)
        pred = predict_regime(model, spy_returns)
        assert pred.regime in ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]
        assert 0 <= pred.probability <= 1
        assert 0 <= pred.confidence <= 1
        assert isinstance(pred.explanation, str)

    def test_predict_with_bull_returns(self, spy_returns_bull):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns_bull, n_states=4)
        pred = predict_regime(model, spy_returns_bull)
        assert "Bull" in pred.regime

    def test_predict_with_bear_returns(self, spy_returns_bear):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns_bear, n_states=4)
        pred = predict_regime(model, spy_returns_bear)
        assert "Bear" in pred.regime or "Bear High Vol" in pred.regime

    def test_full_regime_analysis(self, spy_returns):
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(spy_returns, n_states=4)
        assert "overall_regime" in result
        assert "state_probabilities" in result
        assert "trained_on_bars" in result

    def test_regime_analysis_insufficient_data(self):
        from app.engines.regime.service import full_regime_analysis
        short = pd.Series(np.random.randn(5))
        result = full_regime_analysis(short, n_states=4)
        assert result["overall_regime"].regime == "Range"
        assert result["trained_on_bars"] == 0

    def test_regime_analysis_with_state_assignment(self, spy_returns):
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(spy_returns, n_states=5)
        assert len(result["state_probabilities"]) == 5

    def test_map_state_to_regime(self):
        from app.engines.regime.service import _map_state_to_regime
        regime1 = _map_state_to_regime(0.002, 0.005, 0.8)
        assert "Bull" in regime1
        regime2 = _map_state_to_regime(-0.001, 0.02, 0.6)
        assert "Bear High Vol" in regime2 or "Bear" in regime2 or "Crisis" in regime2
        regime3 = _map_state_to_regime(0.0001, 0.008, 0.3)
        assert regime3 == "Range"
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/regime/test_service.py -v`
Expected: FAIL

- [ ] **Step 7: Write minimal implementation**

Create `backend/app/engines/regime/service.py`:

```python
import numpy as np
import pandas as pd
from hmmlearn import hmm
from app.engines.regime.schemas import RegimePrediction

REGIME_TEMPLATES = {
    "Bull": {"mean_range": (0.0005, np.inf), "vol_range": (0, 0.012), "prob_threshold": 0.3},
    "Bull High Vol": {"mean_range": (0.0005, np.inf), "vol_range": (0.012, np.inf), "prob_threshold": 0.3},
    "Bear": {"mean_range": (-np.inf, -0.0003), "vol_range": (0, 0.015), "prob_threshold": 0.3},
    "Bear High Vol": {"mean_range": (-np.inf, -0.0003), "vol_range": (0.015, np.inf), "prob_threshold": 0.3},
    "Range": {"mean_range": (-0.0003, 0.0005), "vol_range": (0, 0.01), "prob_threshold": 0.2},
    "Crisis": {"mean_range": (-np.inf, -0.002), "vol_range": (0.025, np.inf), "prob_threshold": 0.2},
}


def fit_hmm(returns: pd.Series, n_states: int = 4) -> tuple[hmm.GaussianHMM, np.ndarray]:
    X = returns.values.reshape(-1, 1)
    model = hmm.GaussianHMM(
        n_components=n_states, covariance_type="full", random_state=42, n_iter=100,
    )
    model.fit(X)
    hidden_states = model.predict(X)
    return model, hidden_states


def predict_regime(model: hmm.GaussianHMM, returns: pd.Series) -> RegimePrediction:
    X = returns.values.reshape(-1, 1)
    state_probs = model.predict_proba(X)
    current_probs = state_probs[-1]
    current_state = int(np.argmax(current_probs))
    confidence = float(current_probs[current_state])

    mean = float(model.means_[current_state][0])
    cov = float(model.covars_[current_state][0][0])
    vol = float(np.sqrt(cov))

    regime_name = _map_state_to_regime(mean, vol, confidence)
    explanation = _generate_explanation(regime_name, mean, vol, confidence)

    return RegimePrediction(
        regime=regime_name, probability=confidence, confidence=confidence, explanation=explanation,
    )


def full_regime_analysis(returns: pd.Series, n_states: int = 4) -> dict:
    if len(returns) < n_states * 10:
        return {
            "overall_regime": RegimePrediction(
                regime="Range", probability=0.5, confidence=0.5,
                explanation="Insufficient data for regime detection",
            ),
            "state_probabilities": {f"state_{i}": 0.0 for i in range(n_states)},
            "trained_on_bars": 0,
        }

    model, hidden_states = fit_hmm(returns, n_states=n_states)
    pred = predict_regime(model, returns)

    X = returns.values.reshape(-1, 1)
    state_probs = model.predict_proba(X)
    state_probabilities = {f"state_{i}": float(state_probs[-1][i]) for i in range(n_states)}

    return {
        "overall_regime": pred,
        "state_probabilities": state_probabilities,
        "trained_on_bars": len(returns),
    }


def _map_state_to_regime(mean: float, vol: float, confidence: float) -> str:
    best_match = "Range"
    best_score = -np.inf
    for regime_name, template in REGIME_TEMPLATES.items():
        mean_lo, mean_hi = template["mean_range"]
        vol_lo, vol_hi = template["vol_range"]
        if mean_lo <= mean <= mean_hi and vol_lo <= vol <= vol_hi:
            if confidence > best_score:
                best_score = confidence
                best_match = regime_name
    return best_match


def _generate_explanation(regime: str, mean: float, vol: float, confidence: float) -> str:
    base = f"Detected {regime} regime. "
    base += f"Mean daily return: {mean:.4f}, Volatility: {vol:.4f}, Confidence: {confidence:.1%}."
    if confidence < 0.4:
        base += " Low confidence - regime may be transitioning."
    elif confidence > 0.7:
        base += " High conviction signal."
    if regime in ("Crisis", "Bear High Vol"):
        base += " Elevated risk levels detected."
    return base
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/regime/test_service.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/engines/regime/ backend/tests/engines/regime/
git commit -m "feat: add market regime engine with HMM (2-6 states) and regime classification"
```

---


### Task 8: Market Regime Engine — Router & Tasks

**Files:**
- Create: `backend/app/engines/regime/router.py`
- Create: `backend/app/engines/regime/tasks.py`
- Test: `backend/tests/engines/regime/test_router.py`
- Test: `backend/tests/engines/regime/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/regime/test_tasks.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestRegimeTasks:
    @patch("app.engines.regime.tasks.PolygonDataService")
    @patch("app.engines.regime.tasks.full_regime_analysis")
    def test_compute_regime_task(self, mock_analysis, mock_ds):
        from app.engines.regime.tasks import compute_regime
        import pandas as pd
        from app.engines.regime.schemas import RegimePrediction
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame({
            "close": [100.0 + i * 0.5 for i in range(100)],
        })
        mock_analysis.return_value = {
            "overall_regime": RegimePrediction(regime="Bull", probability=0.8, confidence=0.75, explanation="Test"),
            "state_probabilities": {"state_0": 0.8, "state_1": 0.2},
            "trained_on_bars": 100,
        }
        result = compute_regime()
        assert result["status"] == "success"
        assert result["regime"] == "Bull"

    @patch("app.engines.regime.tasks.PolygonDataService")
    def test_compute_regime_no_data(self, mock_ds):
        from app.engines.regime.tasks import compute_regime
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_regime()
        assert result["status"] == "error"

    @patch("app.engines.regime.tasks.compute_regime")
    def test_compute_all_regimes_task(self, mock_compute):
        from app.engines.regime.tasks import compute_all_regimes
        mock_compute.return_value = {"status": "success", "regime": "Bull"}
        results = compute_all_regimes()
        assert len(results) > 0
```

Create `backend/tests/engines/regime/test_router.py`:

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


class TestRegimeRouter:
    async def test_get_global_regime(self, client):
        resp = await client.get("/api/v1/analysis/regime")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_regime" in data
        assert "ticker" in data

    async def test_get_regime_for_ticker(self, client):
        resp = await client.get("/api/v1/analysis/regime/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "overall_regime" in data

    @patch("app.engines.regime.router.compute_regime")
    async def test_post_compute_regime(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-789")
        resp = await client.post("/api/v1/analysis/regime/compute", json={"ticker": "SPY", "n_states": 4})
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-789"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/regime/test_tasks.py tests/engines/regime/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/regime/tasks.py`:

```python
import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.regime.service import full_regime_analysis
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_regime(self, ticker: str = "SPY", n_states: int = 4, lookback_days: int = 756) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=lookback_days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        returns = df["close"].pct_change().dropna()
        analysis = full_regime_analysis(returns, n_states=n_states)
        _save_regime(ticker, analysis)

        logger.info("Regime for %s: %s", ticker, analysis["overall_regime"].regime)
        return {
            "ticker": ticker,
            "status": "success",
            "regime": analysis["overall_regime"].regime,
            "probability": analysis["overall_regime"].probability,
            "confidence": analysis["overall_regime"].confidence,
            "message": analysis["overall_regime"].explanation,
        }
    except Exception as e:
        logger.exception("Failed to compute regime for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_regimes(n_states: int = 4, lookback_days: int = 756) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_regime.delay(ticker, n_states=n_states, lookback_days=lookback_days)
        results.append(result)
    return results


def _save_regime(ticker: str, analysis: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "regime")
    os.makedirs(signals_dir, exist_ok=True)
    pred = analysis["overall_regime"]
    row = {
        "ticker": ticker, "date": date_str,
        "regime": pred.regime, "probability": pred.probability,
        "confidence": pred.confidence, "explanation": pred.explanation,
        **analysis["state_probabilities"],
        "trained_on_bars": analysis["trained_on_bars"],
    }
    path = os.path.join(signals_dir, f"{date_str}.parquet")
    pd.DataFrame([row]).to_parquet(path, index=False)
    return path
```

Create `backend/app/engines/regime/router.py`:

```python
import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.regime.schemas import RegimeRequest
from app.engines.regime.tasks import compute_regime as compute_regime_task
from app.engines.data.service import PolygonDataService
from app.engines.regime.service import full_regime_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/regime")
def get_global_regime(lookback_days: int = 756):
    service = PolygonDataService()
    df = service.load_ohlcv("SPY", days=lookback_days)
    if df.empty:
        return {"ticker": "SPY", "overall_regime": None, "state_probabilities": {}, "trained_on_bars": 0}
    returns = df["close"].pct_change().dropna()
    analysis = full_regime_analysis(returns)
    return {"ticker": "SPY", **analysis}


@router.get("/regime/{ticker}")
def get_regime_for_ticker(ticker: str, lookback_days: int = 756):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=lookback_days)
    if df.empty:
        return {"ticker": ticker.upper(), "overall_regime": None, "state_probabilities": {}, "trained_on_bars": 0}
    returns = df["close"].pct_change().dropna()
    analysis = full_regime_analysis(returns)
    return {"ticker": ticker.upper(), **analysis}


@router.post("/regime/compute", status_code=202)
def compute_regime_endpoint(req: RegimeRequest, _=Depends(verify_api_key)):
    task = compute_regime_task.delay(ticker=req.ticker, n_states=req.n_states, lookback_days=req.lookback_days)
    return {"task_id": task.id, "ticker": req.ticker, "status": "queued"}


@router.post("/regime/compute-all", status_code=202)
def compute_all_regimes_endpoint(n_states: int = 4, _=Depends(verify_api_key)):
    from app.engines.regime.tasks import compute_all_regimes
    task = compute_all_regimes.delay(n_states=n_states)
    return {"task_id": task.id, "status": "queued", "message": "Computing regimes for all tickers"}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/regime/test_tasks.py tests/engines/regime/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/regime/router.py backend/app/engines/regime/tasks.py backend/tests/engines/regime/test_tasks.py backend/tests/engines/regime/test_router.py
git commit -m "feat: add Celery tasks and FastAPI router for market regime engine"
```

---


### Task 9: Change Point Engine — CUSUM Service (Pure NumPy)

**Files:**
- Create: `backend/app/engines/cusum/__init__.py`
- Create: `backend/app/engines/cusum/schemas.py`
- Create: `backend/app/engines/cusum/service.py`
- Test: `backend/tests/engines/cusum/test_schemas.py`
- Test: `backend/tests/engines/cusum/test_service.py`

- [ ] **Step 1: Write the failing tests for schemas**

Create `backend/tests/engines/cusum/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError


class TestCUSUMSchemas:
    def test_change_point_result_valid(self):
        from app.engines.cusum.schemas import ChangePointResult
        cp = ChangePointResult(
            detected=True, direction="positive", change_probability=0.85,
            days_since_change=5, cumulative_deviation=2.3,
        )
        assert cp.detected is True
        assert cp.direction == "positive"
        assert 0 <= cp.change_probability <= 1

    def test_change_point_result_no_change(self):
        from app.engines.cusum.schemas import ChangePointResult
        cp = ChangePointResult(
            detected=False, direction="none", change_probability=0.05,
            days_since_change=None, cumulative_deviation=0.1,
        )
        assert cp.detected is False

    def test_change_point_result_rejects_invalid_direction(self):
        from app.engines.cusum.schemas import ChangePointResult
        with pytest.raises(ValidationError):
            ChangePointResult(
                detected=True, direction="sideways", change_probability=0.5,
                days_since_change=1, cumulative_deviation=1.0,
            )

    def test_cusum_response(self):
        from app.engines.cusum.schemas import CUSUMResponse
        resp = CUSUMResponse(ticker="AAPL")
        assert resp.ticker == "AAPL"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/cusum/test_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Create schemas.py**

Create `backend/app/engines/cusum/schemas.py`:

```python
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, field_validator


class ChangePointResult(BaseModel):
    detected: bool
    direction: Literal["positive", "negative", "none"]
    change_probability: float
    days_since_change: int | None = None
    cumulative_deviation: float = 0.0

    @field_validator("change_probability")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("change_probability must be between 0 and 1")
        return v


class CUSUMResponse(BaseModel):
    ticker: str
    cusum_result: ChangePointResult | None = None
    analyzed_bars: int = 0
    generated_at: datetime = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/cusum/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for CUSUM service**

Create `backend/tests/engines/cusum/test_service.py`:

```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def stable_returns():
    np.random.seed(42)
    return pd.Series(np.random.normal(0, 0.01, 300))


@pytest.fixture
def shift_up_returns():
    np.random.seed(42)
    before = np.random.normal(0, 0.01, 200)
    after = np.random.normal(0.02, 0.01, 100)
    return pd.Series(np.concatenate([before, after]))


@pytest.fixture
def shift_down_returns():
    np.random.seed(42)
    before = np.random.normal(0, 0.01, 200)
    after = np.random.normal(-0.02, 0.01, 100)
    return pd.Series(np.concatenate([before, after]))


class TestCUSUMService:
    def test_cusum_no_drift_stable(self, stable_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(stable_returns, threshold=3.0, drift=0.005)
        assert result["detected"] is False
        assert result["direction"] == "none"
        assert result["cumulative_deviation"] >= 0

    def test_cusum_detects_positive_shift(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold=3.0, drift=0.005)
        assert result["detected"] is True
        assert result["direction"] == "positive"
        assert result["change_probability"] > 0.5

    def test_cusum_detects_negative_shift(self, shift_down_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_down_returns, threshold=3.0, drift=0.005)
        assert result["detected"] is True
        assert result["direction"] == "negative"
        assert result["change_probability"] > 0.5

    def test_cusum_calculates_days_since_change(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold=3.0, drift=0.005)
        assert result["days_since_change"] is not None
        assert result["days_since_change"] >= 0

    def test_cusum_higher_threshold_less_detection(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        low_thresh = cusum_detect(shift_up_returns, threshold=2.0, drift=0.005)
        high_thresh = cusum_detect(shift_up_returns, threshold=10.0, drift=0.005)
        assert low_thresh["detected"] is True
        assert high_thresh["detected"] is False

    def test_cusum_insufficient_data(self):
        from app.engines.cusum.service import cusum_detect
        short = pd.Series([0.01, -0.02, 0.01])
        result = cusum_detect(short, threshold=3.0, drift=0.005)
        assert result["detected"] is False
        assert result["cumulative_deviation"] == 0.0

    def test_cusum_dynamic_threshold(self, shift_up_returns):
        from app.engines.cusum.service import cusum_detect
        result = cusum_detect(shift_up_returns, threshold="dynamic", drift=0.005)
        assert "detected" in result
        assert "change_probability" in result

    def test_cusum_all_numpy_no_pandas_dependency(self):
        from app.engines.cusum.service import _cusum_algorithm
        arr = np.random.randn(300)
        arr[200:] += 0.03
        result = _cusum_algorithm(arr, threshold=3.0, drift=0.005)
        assert result["detected"] is True
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/cusum/test_service.py -v`
Expected: FAIL

- [ ] **Step 7: Write minimal implementation**

Create `backend/app/engines/cusum/service.py`:

```python
import numpy as np
import pandas as pd


def cusum_detect(
    returns: pd.Series,
    threshold: float | str = "dynamic",
    drift: float = 0.005,
    min_samples: int = 20,
) -> dict:
    if len(returns) < min_samples:
        return {
            "detected": False, "direction": "none",
            "change_probability": 0.0, "days_since_change": None,
            "cumulative_deviation": 0.0,
        }

    values = returns.values
    actual_threshold = _compute_threshold(values, threshold)
    return _cusum_algorithm(values, threshold=actual_threshold, drift=drift)


def _cusum_algorithm(values: np.ndarray, threshold: float, drift: float) -> dict:
    n = len(values)
    mean = np.mean(values)
    deviation = values - mean - drift

    cumsum_pos = np.zeros(n)
    cumsum_neg = np.zeros(n)

    for i in range(1, n):
        cumsum_pos[i] = max(0, cumsum_pos[i - 1] + deviation[i])
        cumsum_neg[i] = min(0, cumsum_neg[i - 1] + deviation[i])

    max_pos = float(np.max(cumsum_pos))
    max_neg = float(np.min(cumsum_neg))
    max_dev = max(max_pos, -max_neg)

    detected = max_pos > threshold or -max_neg > threshold

    if detected:
        if max_pos > -max_neg:
            direction = "positive"
            change_point = int(np.argmax(cumsum_pos))
            change_prob = min(1.0, max_pos / (threshold * 2))
        else:
            direction = "negative"
            change_point = int(np.argmin(cumsum_neg))
            change_prob = min(1.0, -max_neg / (threshold * 2))
        days_since = n - change_point - 1
    else:
        direction = "none"; change_point = None; days_since = None; change_prob = 0.0

    return {
        "detected": detected,
        "direction": direction,
        "change_probability": round(change_prob, 4),
        "days_since_change": days_since if days_since is not None and days_since >= 0 else None,
        "cumulative_deviation": round(max_dev, 4),
    }


def _compute_threshold(values: np.ndarray, threshold_spec: float | str) -> float:
    if isinstance(threshold_spec, (int, float)):
        return float(threshold_spec)
    if threshold_spec == "dynamic":
        return 4.0 * float(np.std(values))
    return float(threshold_spec)
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/cusum/test_service.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/engines/cusum/ backend/tests/engines/cusum/test_schemas.py backend/tests/engines/cusum/test_service.py
git commit -m "feat: add change point engine with pure numpy CUSUM detection"
```

---


### Task 10: Change Point Engine — Router & Tasks

**Files:**
- Create: `backend/app/engines/cusum/router.py`
- Create: `backend/app/engines/cusum/tasks.py`
- Test: `backend/tests/engines/cusum/test_router.py`
- Test: `backend/tests/engines/cusum/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/cusum/test_tasks.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestCUSUMTasks:
    @patch("app.engines.cusum.tasks.PolygonDataService")
    @patch("app.engines.cusum.tasks.cusum_detect")
    def test_compute_cusum_task(self, mock_cusum, mock_ds):
        from app.engines.cusum.tasks import compute_cusum
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame({
            "close": [100.0 + i for i in range(100)],
        })
        mock_cusum.return_value = {
            "detected": True, "direction": "positive",
            "change_probability": 0.85, "days_since_change": 3, "cumulative_deviation": 2.5,
        }
        result = compute_cusum("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["detected"] is True

    @patch("app.engines.cusum.tasks.PolygonDataService")
    def test_compute_cusum_no_data(self, mock_ds):
        from app.engines.cusum.tasks import compute_cusum
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_cusum("UNKNOWN")
        assert result["status"] == "error"

    @patch("app.engines.cusum.tasks.compute_cusum")
    def test_compute_all_cusum(self, mock_compute):
        from app.engines.cusum.tasks import compute_all_cusum
        from app.models.universe import DEFAULT_UNIVERSE
        mock_compute.return_value = {"status": "success", "detected": False}
        results = compute_all_cusum()
        assert len(results) == len(DEFAULT_UNIVERSE)
```

Create `backend/tests/engines/cusum/test_router.py`:

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


class TestCUSUMRouter:
    async def test_get_cusum_for_ticker(self, client):
        resp = await client.get("/api/v1/analysis/cusum/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"

    async def test_get_cusum_no_data(self, client):
        resp = await client.get("/api/v1/analysis/cusum/UNKNOWN")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analyzed_bars"] == 0

    @patch("app.engines.cusum.router.compute_cusum")
    async def test_post_compute_cusum(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-101")
        resp = await client.post("/api/v1/analysis/cusum/compute/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-101"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/cusum/test_tasks.py tests/engines/cusum/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/cusum/tasks.py`:

```python
import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.cusum.service import cusum_detect
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_cusum(self, ticker: str, days: int = 365, threshold: float | str = "dynamic") -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        returns = df["close"].pct_change().dropna()
        result = cusum_detect(returns, threshold=threshold)
        _save_cusum(ticker, result)

        logger.info("CUSUM for %s: detected=%s direction=%s", ticker, result["detected"], result["direction"])
        return {"ticker": ticker, "status": "success", **result}
    except Exception as e:
        logger.exception("Failed to compute CUSUM for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_cusum(days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_cusum.delay(ticker, days=days)
        results.append(result)
    return results


def _save_cusum(ticker: str, result: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "cusum")
    os.makedirs(signals_dir, exist_ok=True)
    path = os.path.join(signals_dir, f"{date_str}.parquet")
    row = {"ticker": ticker, "date": date_str, **result}
    pd.DataFrame([row]).to_parquet(path, index=False)
    return path
```

Create `backend/app/engines/cusum/router.py`:

```python
import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.cusum.schemas import CUSUMResponse, ChangePointResult
from app.engines.cusum.tasks import compute_cusum as compute_cusum_task
from app.engines.data.service import PolygonDataService
from app.engines.cusum.service import cusum_detect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/cusum/{ticker}")
def get_cusum(ticker: str, days: int = 365, threshold: str = "dynamic"):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return CUSUMResponse(ticker=ticker.upper(), cusum_result=None, analyzed_bars=0)
    returns = df["close"].pct_change().dropna()
    result = cusum_detect(returns, threshold=threshold)
    return CUSUMResponse(
        ticker=ticker.upper(),
        cusum_result=ChangePointResult(**result),
        analyzed_bars=len(returns),
    )


@router.post("/cusum/compute/{ticker}", status_code=202)
def compute_cusum_endpoint(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_cusum_task.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/cusum/compute-all", status_code=202)
def compute_all_cusum_endpoint(_=Depends(verify_api_key)):
    from app.engines.cusum.tasks import compute_all_cusum
    task = compute_all_cusum.delay()
    return {"task_id": task.id, "status": "queued", "message": "Computing CUSUM for all tickers"}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/cusum/test_tasks.py tests/engines/cusum/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/cusum/router.py backend/app/engines/cusum/tasks.py backend/tests/engines/cusum/test_tasks.py backend/tests/engines/cusum/test_router.py
git commit -m "feat: add Celery tasks and FastAPI router for CUSUM change point engine"
```

---


### Task 11: Breakout Detection Engine — Schemas & Service

**Files:**
- Create: `backend/app/engines/breakout/__init__.py`
- Create: `backend/app/engines/breakout/schemas.py`
- Create: `backend/app/engines/breakout/service.py`
- Test: `backend/tests/engines/breakout/test_schemas.py`
- Test: `backend/tests/engines/breakout/test_service.py`

- [ ] **Step 1: Write the failing tests for schemas**

Create `backend/tests/engines/breakout/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError


class TestBreakoutSchemas:
    def test_breakout_signal_valid(self):
        from app.engines.breakout.schemas import BreakoutSignal
        sig = BreakoutSignal(
            ticker="AAPL", breakout_type="volatility_compression",
            direction="bullish", strength=0.75, confirmed=True,
        )
        assert sig.ticker == "AAPL"
        assert sig.direction == "bullish"
        assert 0 <= sig.strength <= 1

    def test_breakout_signal_invalid_direction(self):
        from app.engines.breakout.schemas import BreakoutSignal
        with pytest.raises(ValidationError):
            BreakoutSignal(ticker="AAPL", breakout_type="channel", direction="sideways", strength=0.5, confirmed=True)

    def test_breakout_signal_invalid_strength(self):
        from app.engines.breakout.schemas import BreakoutSignal
        with pytest.raises(ValidationError):
            BreakoutSignal(ticker="AAPL", breakout_type="channel", direction="bullish", strength=1.5, confirmed=False)

    def test_breakout_signal_negative_strength(self):
        from app.engines.breakout.schemas import BreakoutSignal
        with pytest.raises(ValidationError):
            BreakoutSignal(ticker="AAPL", breakout_type="channel", direction="bullish", strength=-0.1, confirmed=False)

    def test_breakout_response(self):
        from app.engines.breakout.schemas import BreakoutResponse
        resp = BreakoutResponse(ticker="AAPL")
        assert resp.ticker == "AAPL"
        assert resp.signals == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/breakout/test_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Create schemas.py**

Create `backend/app/engines/breakout/schemas.py`:

```python
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, field_validator


class BreakoutSignal(BaseModel):
    ticker: str
    breakout_type: Literal["channel", "volatility_compression", "market_structure", "volume_confirmation"]
    direction: Literal["bullish", "bearish"]
    strength: float
    confirmed: bool = False
    details: dict = {}

    @field_validator("strength")
    @classmethod
    def validate_strength(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("strength must be between 0 and 1")
        return v


class BreakoutResponse(BaseModel):
    ticker: str
    signals: list[BreakoutSignal] = []
    analyzed_bars: int = 0
    generated_at: datetime = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/breakout/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for breakout service**

Create `backend/tests/engines/breakout/test_service.py`:

```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    price = 150.0 + np.cumsum(np.random.normal(0, 1.0, n))
    return pd.DataFrame({
        "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
        "low": price * 0.98, "close": price,
        "volume": np.random.randint(500000, 2000000, n),
    })


@pytest.fixture
def strong_uptrend():
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    price = 100.0 + np.linspace(0, 50, n) + np.random.normal(0, 1.0, n)
    return pd.DataFrame({
        "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
        "low": price * 0.98, "close": price,
        "volume": np.random.randint(800000, 3000000, n),
    })


class TestBreakoutService:
    def test_gaussian_channel(self, sample_ohlcv):
        from app.engines.breakout.service import compute_gaussian_channel
        upper, middle, lower = compute_gaussian_channel(sample_ohlcv["close"], sigma=2.0)
        assert len(upper) == 200 and len(middle) == 200 and len(lower) == 200
        assert (upper >= middle).all() and (middle >= lower).all()

    def test_detect_breakout_above_channel(self, strong_uptrend):
        from app.engines.breakout.service import detect_gaussian_breakout
        signals = detect_gaussian_breakout(strong_uptrend["close"], sigma=2.0, lookback=10)
        for sig in signals:
            assert sig.breakout_type == "channel"

    def test_volatility_compression(self, sample_ohlcv):
        from app.engines.breakout.service import detect_volatility_compression
        signals = detect_volatility_compression(sample_ohlcv["close"], sample_ohlcv["high"], sample_ohlcv["low"])
        for sig in signals:
            assert sig.breakout_type == "volatility_compression"

    def test_market_structure_breakout(self, sample_ohlcv):
        from app.engines.breakout.service import detect_market_structure
        signals = detect_market_structure(sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"])
        for sig in signals:
            assert sig.breakout_type == "market_structure"

    def test_volume_confirmation(self, sample_ohlcv):
        from app.engines.breakout.service import detect_volume_confirmation
        signals = detect_volume_confirmation(sample_ohlcv["close"], sample_ohlcv["volume"])
        for sig in signals:
            assert sig.breakout_type == "volume_confirmation"

    def test_full_breakout_analysis(self, sample_ohlcv):
        from app.engines.breakout.service import full_breakout_analysis
        result = full_breakout_analysis(sample_ohlcv)
        for sig in result:
            assert sig.breakout_type in ["channel", "volatility_compression", "market_structure", "volume_confirmation"]

    def test_no_breakout_in_flat_market(self):
        from app.engines.breakout.service import full_breakout_analysis
        flat = pd.DataFrame({
            "close": [100.0] * 100, "high": [101.0] * 100,
            "low": [99.0] * 100, "volume": [1000000] * 100,
        })
        assert full_breakout_analysis(flat) == []

    def test_empty_data_returns_empty(self):
        from app.engines.breakout.service import full_breakout_analysis
        assert full_breakout_analysis(pd.DataFrame()) == []
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/breakout/test_service.py -v`
Expected: FAIL

- [ ] **Step 7: Write minimal implementation**

Create `backend/app/engines/breakout/service.py`:

```python
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from app.engines.breakout.schemas import BreakoutSignal


def compute_gaussian_channel(close: pd.Series, sigma: float = 2.0):
    values = close.values.astype(float)
    smoothed = gaussian_filter1d(values, sigma=sigma, mode="nearest")
    residuals = values - smoothed
    std = float(np.std(residuals))
    return (
        pd.Series(smoothed + 2.0 * std, index=close.index),
        pd.Series(smoothed, index=close.index),
        pd.Series(smoothed - 2.0 * std, index=close.index),
    )


def detect_gaussian_breakout(close: pd.Series, sigma: float = 2.0, lookback: int = 3):
    upper, middle, lower = compute_gaussian_channel(close, sigma=sigma)
    signals = []
    if (close.iloc[-lookback:] > upper.iloc[-lookback:]).any():
        strength = min(1.0, float((close.iloc[-1] - upper.iloc[-1]) / upper.iloc[-1] * 100))
        signals.append(BreakoutSignal(
            ticker="", breakout_type="channel", direction="bullish",
            strength=round(strength, 4), confirmed=(close.iloc[-1] > upper.iloc[-1]),
            details={"sigma": sigma, "distance_pct": round(strength * 100, 2)},
        ))
    if (close.iloc[-lookback:] < lower.iloc[-lookback:]).any():
        strength = min(1.0, float((lower.iloc[-1] - close.iloc[-1]) / lower.iloc[-1] * 100))
        signals.append(BreakoutSignal(
            ticker="", breakout_type="channel", direction="bearish",
            strength=round(strength, 4), confirmed=(close.iloc[-1] < lower.iloc[-1]),
            details={"sigma": sigma, "distance_pct": round(strength * 100, 2)},
        ))
    return signals


def detect_volatility_compression(close, high, low, bb_period=20, kc_period=20, kc_atr_mult=1.5):
    sma = close.rolling(window=bb_period).mean()
    bb_std = close.rolling(window=bb_period).std()
    bb_upper, bb_lower = sma + 2.0 * bb_std, sma - 2.0 * bb_std
    bb_width = bb_upper - bb_lower

    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    kc_atr = tr.rolling(window=kc_period).mean()
    squeeze_on = (bb_lower > sma - kc_atr_mult * kc_atr) & (bb_upper < sma + kc_atr_mult * kc_atr)

    signals = []
    if squeeze_on.iloc[-1]:
        recent_bb = bb_width.iloc[-kc_period:]
        if len(recent_bb) > 1:
            compression = 1.0 - (bb_width.iloc[-1] / recent_bb.max())
            signals.append(BreakoutSignal(
                ticker="", breakout_type="volatility_compression",
                direction="bullish" if close.iloc[-1] > sma.iloc[-1] else "bearish",
                strength=round(min(1.0, max(0.0, compression)), 4), confirmed=False,
                details={"squeeze_active": True, "bb_width": float(bb_width.iloc[-1]), "compression_pct": round(compression * 100, 2)},
            ))
    return signals


def detect_market_structure(high, low, close, lookback=20, tolerance=0.005):
    signals = []
    hh_level = float(high.iloc[-lookback:].max())
    ll_level = float(low.iloc[-lookback:].min())
    prev_hh = float(high.iloc[-lookback * 2:-lookback].max()) if len(high) > lookback * 2 else hh_level
    prev_ll = float(low.iloc[-lookback * 2:-lookback].min()) if len(low) > lookback * 2 else ll_level

    if hh_level > prev_hh * (1.0 + tolerance):
        strength = min(1.0, (hh_level - prev_hh) / prev_hh * 10)
        signals.append(BreakoutSignal(
            ticker="", breakout_type="market_structure", direction="bullish",
            strength=round(strength, 4), confirmed=True,
            details={"new_high": hh_level, "previous_high": prev_hh, "breakout_pct": round((hh_level - prev_hh) / prev_hh * 100, 2)},
        ))
    if ll_level < prev_ll * (1.0 - tolerance):
        strength = min(1.0, (prev_ll - ll_level) / prev_ll * 10)
        signals.append(BreakoutSignal(
            ticker="", breakout_type="market_structure", direction="bearish",
            strength=round(strength, 4), confirmed=True,
            details={"new_low": ll_level, "previous_low": prev_ll, "breakout_pct": round((prev_ll - ll_level) / prev_ll * 100, 2)},
        ))
    return signals


def detect_volume_confirmation(close, volume, lookback=21, vol_mult=1.5):
    signals = []
    avg_volume = volume.rolling(window=lookback).mean()
    vol_ratio = volume / avg_volume.replace(0, np.nan)
    if vol_ratio.iloc[-1] > vol_mult and pd.notna(vol_ratio.shift(1).iloc[-1]):
        direction = "bullish" if close.iloc[-1] > close.iloc[-2] else "bearish"
        strength = min(1.0, (vol_ratio.iloc[-1] - 1.0) / (vol_mult * 2))
        signals.append(BreakoutSignal(
            ticker="", breakout_type="volume_confirmation", direction=direction,
            strength=round(float(strength), 4), confirmed=vol_ratio.iloc[-1] > vol_mult * 1.5,
            details={"volume_ratio": float(vol_ratio.iloc[-1]), "avg_volume": float(avg_volume.iloc[-1]), "current_volume": float(volume.iloc[-1])},
        ))
    return signals


def full_breakout_analysis(ohlcv: pd.DataFrame):
    if ohlcv.empty or len(ohlcv) < 50:
        return []
    c, h, l = ohlcv["close"], ohlcv["high"], ohlcv["low"]
    v = ohlcv["volume"] if "volume" in ohlcv.columns else pd.Series(dtype=float)
    signals = []
    signals.extend(detect_gaussian_breakout(c))
    signals.extend(detect_volatility_compression(c, h, l))
    signals.extend(detect_market_structure(h, l, c))
    if not v.empty:
        signals.extend(detect_volume_confirmation(c, v))
    return signals
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/breakout/test_service.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/engines/breakout/__init__.py backend/app/engines/breakout/schemas.py backend/app/engines/breakout/service.py backend/tests/engines/breakout/test_schemas.py backend/tests/engines/breakout/test_service.py
git commit -m "feat: add breakout detection engine with Gaussian channel, volatility compression, market structure, and volume confirmation"
```

---


### Task 12: Breakout Detection Engine — Router & Tasks

**Files:**
- Create: `backend/app/engines/breakout/router.py`
- Create: `backend/app/engines/breakout/tasks.py`
- Test: `backend/tests/engines/breakout/test_router.py`
- Test: `backend/tests/engines/breakout/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/breakout/test_tasks.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestBreakoutTasks:
    @patch("app.engines.breakout.tasks.PolygonDataService")
    @patch("app.engines.breakout.tasks.full_breakout_analysis")
    def test_compute_breakouts_task(self, mock_analysis, mock_ds):
        from app.engines.breakout.tasks import compute_breakouts
        import pandas as pd
        from app.engines.breakout.schemas import BreakoutSignal
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame({
            "close": [150.0 + i * 0.5 for i in range(100)],
            "high": [155.0 + i * 0.5 for i in range(100)],
            "low": [149.0 + i * 0.5 for i in range(100)],
            "volume": [1000000] * 100,
        })
        mock_analysis.return_value = [
            BreakoutSignal(ticker="AAPL", breakout_type="channel", direction="bullish", strength=0.8, confirmed=True),
        ]
        result = compute_breakouts("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["signals_count"] == 1

    @patch("app.engines.breakout.tasks.PolygonDataService")
    def test_compute_breakouts_no_data(self, mock_ds):
        from app.engines.breakout.tasks import compute_breakouts
        import pandas as pd
        mock_ds.return_value.load_ohlcv.return_value = pd.DataFrame()
        result = compute_breakouts("UNKNOWN")
        assert result["status"] == "error"

    @patch("app.engines.breakout.tasks.compute_breakouts")
    def test_compute_all_breakouts(self, mock_compute):
        from app.engines.breakout.tasks import compute_all_breakouts
        from app.models.universe import DEFAULT_UNIVERSE
        mock_compute.return_value = {"status": "success", "signals_count": 1}
        results = compute_all_breakouts()
        assert len(results) == len(DEFAULT_UNIVERSE)
```

Create `backend/tests/engines/breakout/test_router.py`:

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


class TestBreakoutRouter:
    async def test_get_breakouts_for_ticker(self, client):
        resp = await client.get("/api/v1/analysis/breakouts/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "signals" in data

    async def test_get_breakouts_no_data(self, client):
        resp = await client.get("/api/v1/analysis/breakouts/UNKNOWN")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analyzed_bars"] == 0

    async def test_get_global_breakouts(self, client):
        resp = await client.get("/api/v1/analysis/breakouts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @patch("app.engines.breakout.router.compute_breakouts")
    async def test_post_compute_breakouts(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-202")
        resp = await client.post("/api/v1/analysis/breakouts/compute/AAPL")
        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "task-202"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/breakout/test_tasks.py tests/engines/breakout/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/breakout/tasks.py`:

```python
import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.breakout.service import full_breakout_analysis
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_breakouts(self, ticker: str, days: int = 365) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        signals = full_breakout_analysis(df)
        for sig in signals:
            sig.ticker = ticker

        _save_breakouts(ticker, signals)

        logger.info("Breakouts for %s: %d signals", ticker, len(signals))
        return {
            "ticker": ticker, "status": "success",
            "signals_count": len(signals),
            "breakout_types": list(set(s.breakout_type for s in signals)),
        }
    except Exception as e:
        logger.exception("Failed to compute breakouts for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_breakouts(days: int = 365) -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        result = compute_breakouts.delay(ticker, days=days)
        results.append(result)
    return results


def _save_breakouts(ticker: str, signals: list) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "breakouts")
    os.makedirs(signals_dir, exist_ok=True)
    rows = [{
        "ticker": ticker, "date": date_str,
        "breakout_type": s.breakout_type, "direction": s.direction,
        "strength": s.strength, "confirmed": s.confirmed, "details": str(s.details),
    } for s in signals]
    path = os.path.join(signals_dir, f"{date_str}.parquet")
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path
```

Create `backend/app/engines/breakout/router.py`:

```python
import logging
from fastapi import APIRouter, Depends

from app.core.dependencies import verify_api_key
from app.engines.breakout.schemas import BreakoutResponse
from app.engines.breakout.tasks import compute_breakouts as compute_breakouts_task
from app.engines.data.service import PolygonDataService
from app.engines.breakout.service import full_breakout_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/breakouts")
def get_all_breakouts(days: int = 365):
    from app.models.universe import DEFAULT_UNIVERSE
    all_signals = []
    service = PolygonDataService()
    for ticker in DEFAULT_UNIVERSE[:10]:
        df = service.load_ohlcv(ticker, days=days)
        if df.empty:
            continue
        signals = full_breakout_analysis(df)
        for sig in signals:
            sig.ticker = ticker
        all_signals.extend(signals)
    return all_signals


@router.get("/breakouts/{ticker}")
def get_breakouts(ticker: str, days: int = 365):
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=days)
    if df.empty:
        return BreakoutResponse(ticker=ticker.upper(), signals=[], analyzed_bars=0)
    signals = full_breakout_analysis(df)
    for sig in signals:
        sig.ticker = ticker.upper()
    return BreakoutResponse(ticker=ticker.upper(), signals=signals, analyzed_bars=len(df))


@router.post("/breakouts/compute/{ticker}", status_code=202)
def compute_breakouts_endpoint(ticker: str, days: int = 365, _=Depends(verify_api_key)):
    task = compute_breakouts_task.delay(ticker, days=days)
    return {"task_id": task.id, "ticker": ticker.upper(), "status": "queued"}


@router.post("/breakouts/compute-all", status_code=202)
def compute_all_breakouts_endpoint(_=Depends(verify_api_key)):
    from app.engines.breakout.tasks import compute_all_breakouts
    task = compute_all_breakouts.delay()
    return {"task_id": task.id, "status": "queued", "message": "Computing breakouts for all tickers"}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/breakout/test_tasks.py tests/engines/breakout/test_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/breakout/router.py backend/app/engines/breakout/tasks.py backend/tests/engines/breakout/test_tasks.py backend/tests/engines/breakout/test_router.py
git commit -m "feat: add Celery tasks and FastAPI router for breakout detection engine"
```

---


### Task 13: Wire Up Analysis Routers in Main App

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestMainApp:
    async def test_health_endpoint(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_features_health(self, client):
        resp = await client.get("/api/v1/analysis/features/health")
        assert resp.status_code == 200
        assert resp.json()["engine"] == "features"

    async def test_regime_endpoint_exists(self, client):
        resp = await client.get("/api/v1/analysis/regime")
        assert resp.status_code == 200

    async def test_indicators_endpoint_exists(self, client):
        resp = await client.get("/api/v1/analysis/indicators/AAPL")
        assert resp.status_code == 200

    async def test_cusum_endpoint_exists(self, client):
        resp = await client.get("/api/v1/analysis/cusum/AAPL")
        assert resp.status_code == 200

    async def test_breakouts_endpoint_exists(self, client):
        resp = await client.get("/api/v1/analysis/breakouts/AAPL")
        assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_main.py -v`
Expected: FAIL (routers not registered yet)

- [ ] **Step 3: Update main.py**

Replace `create_app()` to include all 4 analysis routers:

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.engines.data.router import router as data_router
from app.engines.features.router import router as features_router
from app.engines.regime.router import router as regime_router
from app.engines.cusum.router import router as cusum_router
from app.engines.breakout.router import router as breakout_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend (Phase 2)")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="AI Portfolio Manager", version="0.2.0", lifespan=lifespan)

    app.include_router(data_router)
    app.include_router(features_router)
    app.include_router(regime_router)
    app.include_router(cusum_router)
    app.include_router(breakout_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0"}

    return app


app = create_app()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_main.py
git commit -m "feat: wire up all 4 analysis engine routers in main FastAPI app"
```

---


### Task 14: Wire Up Celery Beat Schedule for Analysis Tasks

**Files:**
- Modify: `backend/app/celery_app.py`

- [ ] **Step 1: Update celery_app.py with analysis beat schedule**

```python
from celery import Celery
from app.config import settings

celery_app = Celery("portfolio_mgr", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-all-data-daily": {
            "task": "app.engines.data.tasks.refresh_all_data",
            "schedule": 86400.0,
        },
        "compute-all-features-daily": {
            "task": "app.engines.features.tasks.compute_all_features",
            "schedule": 86400.0,
        },
        "compute-regime-daily": {
            "task": "app.engines.regime.tasks.compute_regime",
            "schedule": 86400.0,
            "kwargs": {"ticker": "SPY", "n_states": 4},
        },
        "compute-all-cusum-daily": {
            "task": "app.engines.cusum.tasks.compute_all_cusum",
            "schedule": 86400.0,
        },
        "compute-all-breakouts-daily": {
            "task": "app.engines.breakout.tasks.compute_all_breakouts",
            "schedule": 86400.0,
        },
    },
)
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.celery_app import celery_app; print(list(celery_app.conf.beat_schedule.keys()))"`
Expected: Prints all 5 task keys

- [ ] **Step 3: Commit**

```bash
git add backend/app/celery_app.py
git commit -m "feat: add Celery beat schedule for daily analysis pipeline tasks"
```

---


### Task 15: Integration Tests for Analysis Pipeline

**Files:**
- Create: `backend/tests/integration/test_analysis_pipeline.py`

- [ ] **Step 1: Write integration tests**

Create `backend/tests/integration/test_analysis_pipeline.py`:

```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def realistic_ohlcv():
    np.random.seed(42)
    n = 504
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    price = 150.0 + np.cumsum(np.random.normal(0, 1.0, n))
    return pd.DataFrame({
        "timestamp": dates, "open": price * 0.99, "high": price * 1.02,
        "low": price * 0.98, "close": price,
        "volume": np.random.randint(500000, 3000000, n),
    })


class TestFeatureEngineeringIntegration:
    def test_feature_pipeline_with_realistic_data(self, realistic_ohlcv):
        from app.engines.features.service import compute_all_indicators
        spy = realistic_ohlcv["close"] * 1.05
        result = compute_all_indicators(realistic_ohlcv, spy_close=spy)
        assert len(result) > 15
        for key, val in result.items():
            assert isinstance(val, float)
        assert "ema_20" in result and "rsi_14" in result and "atr_14" in result

    def test_feature_all_indicators_bounded(self, realistic_ohlcv):
        from app.engines.features.service import compute_all_indicators
        spy = realistic_ohlcv["close"] * 1.05
        result = compute_all_indicators(realistic_ohlcv, spy_close=spy)
        assert 0 <= result["rsi_14"] <= 100
        assert 0 <= result["stoch_k"] <= 100
        assert result["historical_vol_21"] >= 0
        assert result["relative_volume_21"] >= 0

    def test_feature_empty_price_series(self):
        from app.engines.features.service import compute_all_indicators
        assert compute_all_indicators(pd.DataFrame({"close": [], "high": [], "low": [], "volume": []})) == {}


class TestRegimeIntegration:
    def test_regime_analysis_with_realistic_data(self, realistic_ohlcv):
        from app.engines.regime.service import full_regime_analysis
        returns = realistic_ohlcv["close"].pct_change().dropna()
        result = full_regime_analysis(returns, n_states=4)
        assert result["trained_on_bars"] > 0
        assert result["overall_regime"].regime in ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]

    def test_regime_with_different_n_states(self, realistic_ohlcv):
        from app.engines.regime.service import full_regime_analysis
        returns = realistic_ohlcv["close"].pct_change().dropna()
        for n in [2, 3, 4, 5, 6]:
            assert len(full_regime_analysis(returns, n_states=n)["state_probabilities"]) == n

    def test_regime_insufficient_data_returns_default(self):
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(pd.Series([0.01, -0.02]), n_states=4)
        assert result["overall_regime"].regime == "Range"
        assert result["trained_on_bars"] == 0


class TestCUSUMIntegration:
    def test_cusum_with_realistic_data(self, realistic_ohlcv):
        from app.engines.cusum.service import cusum_detect
        returns = realistic_ohlcv["close"].pct_change().dropna()
        result = cusum_detect(returns, threshold="dynamic")
        assert result["direction"] in ("positive", "negative", "none")
        assert result["cumulative_deviation"] >= 0

    def test_cusum_with_high_threshold_no_detection(self, realistic_ohlcv):
        from app.engines.cusum.service import cusum_detect
        returns = realistic_ohlcv["close"].pct_change().dropna()
        assert cusum_detect(returns, threshold=100.0)["detected"] is False

    def test_cusum_edge_case_all_zeros(self):
        from app.engines.cusum.service import cusum_detect
        assert cusum_detect(pd.Series(np.zeros(200)), threshold=3.0)["detected"] is False


class TestBreakoutIntegration:
    def test_breakout_with_realistic_data(self, realistic_ohlcv):
        from app.engines.breakout.service import full_breakout_analysis
        signals = full_breakout_analysis(realistic_ohlcv)
        for sig in signals:
            assert sig.breakout_type in ["channel", "volatility_compression", "market_structure", "volume_confirmation"]
            assert 0 <= sig.strength <= 1

    def test_breakout_flat_market_no_signals(self):
        from app.engines.breakout.service import full_breakout_analysis
        flat = pd.DataFrame({
            "close": [100.0] * 100, "high": [101.0] * 100,
            "low": [99.0] * 100, "volume": [1000000] * 100,
        })
        assert full_breakout_analysis(flat) == []


class TestAnalysisPipelineEndToEnd:
    def test_full_pipeline_runs_without_error(self, realistic_ohlcv):
        ohlcv, spy = realistic_ohlcv, realistic_ohlcv["close"] * 1.02
        returns = ohlcv["close"].pct_change().dropna()

        from app.engines.features.service import compute_all_indicators
        from app.engines.regime.service import full_regime_analysis
        from app.engines.cusum.service import cusum_detect
        from app.engines.breakout.service import full_breakout_analysis

        assert len(compute_all_indicators(ohlcv, spy_close=spy)) > 0
        assert full_regime_analysis(returns, n_states=4)["overall_regime"].regime is not None
        assert cusum_detect(returns, threshold="dynamic")["direction"] is not None
        assert isinstance(full_breakout_analysis(ohlcv), list)

    def test_pipeline_with_empty_data_graceful(self):
        from app.engines.features.service import compute_all_indicators
        from app.engines.regime.service import full_regime_analysis
        from app.engines.cusum.service import cusum_detect
        from app.engines.breakout.service import full_breakout_analysis

        assert compute_all_indicators(pd.DataFrame()) == {}
        assert full_regime_analysis(pd.Series(dtype=float), n_states=4)["overall_regime"].regime == "Range"
        assert cusum_detect(pd.Series(dtype=float), threshold=3.0)["detected"] is False
        assert full_breakout_analysis(pd.DataFrame()) == []
```

- [ ] **Step 2: Run to verify it passes**

Run: `cd backend && python -m pytest tests/integration/test_analysis_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --cov=app`
Expected: All ~100+ tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_analysis_pipeline.py
git commit -m "test: add integration tests for analysis pipeline end-to-end"
```

---


### Task 16: Final Cleanup — Ruff Lint & Full Test Suite

- [ ] **Step 1: Run ruff**

Run: `cd backend && ruff check app/ tests/`
Expected: No errors

- [ ] **Step 2: Auto-fix any issues**

Run: `cd backend && ruff check --fix app/ tests/`
Expected: Clean exit

- [ ] **Step 3: Run full test suite with coverage**

Run: `cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing`
Expected: All tests pass, coverage report

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: lint and type-check Phase 2 analysis engines"
```

---


## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage:**
   - [ ] Feature Engineering Engine: Trend (EMA20/50/200, SMA50/200) - Task 2
   - [ ] Feature Engineering Engine: Momentum (RSI, MACD, ROC, PPO, Stochastic) - Task 3
   - [ ] Feature Engineering Engine: Volatility (ATR, HV, RV, Bollinger width) - Task 4
   - [ ] Feature Engineering Engine: Volume (RelVol, OBV, A/D) - Task 4
   - [ ] Feature Engineering Engine: Market Relative (RS vs SPY, RS vs Sector) - Task 5
   - [ ] Feature Engineering Engine: Full pipeline `compute_all_indicators()` - Task 5
   - [ ] Market Regime Engine: HMM with hmmlearn, 2-6 states - Task 7
   - [ ] Market Regime Engine: 6 regime labels + probability + confidence + explanation - Task 7
   - [ ] Change Point Engine: CUSUM with pure numpy - Task 9
   - [ ] Change Point Engine: Dynamic threshold, direction, probability, days since change - Task 9
   - [ ] Breakout Detection: Gaussian filtered channel - Task 11
   - [ ] Breakout Detection: Volatility compression (BB + KC squeeze) - Task 11
   - [ ] Breakout Detection: Market structure (HH/HL, support/resistance) - Task 11
   - [ ] Breakout Detection: Volume confirmation - Task 11
   - [ ] Each engine has `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py` - Tasks 1-12
   - [ ] Signals stored as Parquet in `signals/<type>/` - Tasks 6, 8, 10, 12
   - [ ] FastAPI endpoints for all engines - Tasks 6, 8, 10, 12, 13
   - [ ] Celery tasks with beat schedule - Tasks 6, 8, 10, 12, 14
   - [ ] Integration tests for pipeline - Task 15

2. **Placeholder scan:** No TBD, TODO, or incomplete steps.

3. **Type consistency:** All method signatures match across tasks. `full_breakout_analysis` returns `list[BreakoutSignal]`, `cusum_detect` returns `dict`, `full_regime_analysis` returns `dict` with `RegimePrediction`, `compute_all_indicators` returns `dict[str, float]`.

4. **Ambiguity check:** All steps are explicit with exact code and commands.
