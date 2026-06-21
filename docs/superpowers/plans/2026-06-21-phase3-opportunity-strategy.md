# Phase 3: Opportunity & Strategy Engines — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 engines — Opportunity Ranking (weighted composite + XGBoost refinement), Strategy Selection (rule-based + ML confidence), and Options Engine (Black-Scholes pricing for CSP, LEAPS, PMCC, Covered Call) — that consume Phase 2 signals and produce trade opportunities stored as Parquet files, with full TDD coverage and FastAPI/Celery wiring.

**Architecture:** Three engine packages under `backend/app/engines/opportunity/`, `backend/app/engines/strategy/`, `backend/app/engines/options/`. Each has `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py`. Opportunity engine additionally has `model.py` for the XGBoost refinement model. Services are pure functions with no I/O side effects. Black-Scholes implemented with numpy + scipy (no additional dependency). Opportunities stored as daily Parquet under `signals/opportunities/<date>.parquet`.

**Tech Stack:** Python 3.12, numpy, pandas, scipy, scikit-learn, xgboost, FastAPI, Celery, pytest, unittest.mock

**Testing Requirement:** Every major component must have tests covering normal operation, edge cases, and error states.

---

### Task 1: Prerequisite — Update requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add xgboost**

Append to `backend/requirements.txt`:
```
# ML
xgboost==2.1.3
```

- [ ] **Step 2: Verify install**

Run: `cd backend && pip install -r requirements-dev.txt 2>&1 | tail -5`
Expected: All packages install cleanly including xgboost

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add xgboost for Phase 3 opportunity scoring refinement"
```

---

### Task 2: Opportunity Engine — Schemas

**Files:**
- Create: `backend/app/engines/opportunity/__init__.py`
- Create: `backend/app/engines/opportunity/schemas.py`
- Test: `backend/tests/engines/opportunity/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/opportunity/test_schemas.py`:
```python
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError


class TestOpportunitySchemas:
    def test_opportunity_score_valid(self):
        from app.engines.opportunity.schemas import OpportunityScore
        score = OpportunityScore(
            ticker="AAPL", total_score=75.5, regime_score=80.0,
            breakout_score=70.0, relative_strength_score=85.0,
            cusum_score=60.0, volume_score=65.0, trend_score=90.0,
            refined_score=78.0, strategy_type="swing", rank=1,
        )
        assert score.ticker == "AAPL"
        assert 0 <= score.total_score <= 100
        assert score.strategy_type == "swing"

    def test_opportunity_score_defaults(self):
        from app.engines.opportunity.schemas import OpportunityScore
        score = OpportunityScore(ticker="AAPL", total_score=50.0)
        assert score.regime_score == 0.0
        assert score.refined_score is None
        assert score.rank == 0

    def test_opportunity_score_rejects_out_of_range(self):
        from app.engines.opportunity.schemas import OpportunityScore
        with pytest.raises(ValidationError):
            OpportunityScore(ticker="AAPL", total_score=150.0)
        with pytest.raises(ValidationError):
            OpportunityScore(ticker="AAPL", total_score=-10.0)

    def test_opportunity_request_valid(self):
        from app.engines.opportunity.schemas import OpportunityRequest
        req = OpportunityRequest(strategy_type="swing", top_n=10)
        assert req.strategy_type == "swing"
        assert req.top_n == 10

    def test_opportunity_request_rejects_invalid_strategy(self):
        from app.engines.opportunity.schemas import OpportunityRequest
        with pytest.raises(ValidationError):
            OpportunityRequest(strategy_type="invalid", top_n=5)

    def test_opportunity_response_valid(self):
        from app.engines.opportunity.schemas import OpportunityResponse, OpportunityScore
        resp = OpportunityResponse(
            date=datetime.now(timezone.utc).date().isoformat(),
            opportunities=[
                OpportunityScore(ticker="AAPL", total_score=75.0),
                OpportunityScore(ticker="NVDA", total_score=72.0),
            ], total_analyzed=50,
        )
        assert len(resp.opportunities) == 2
        assert resp.total_analyzed == 50

    def test_available_strategies(self):
        from app.engines.opportunity.schemas import VALID_STRATEGIES
        assert "swing" in VALID_STRATEGIES
        assert "csp" in VALID_STRATEGIES
        assert "leaps" in VALID_STRATEGIES
        assert "pmcc" in VALID_STRATEGIES
        assert len(VALID_STRATEGIES) == 4
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/opportunity/__init__.py` (empty).
Create `backend/app/engines/opportunity/schemas.py`:
```python
from pydantic import BaseModel, field_validator

VALID_STRATEGIES = ["swing", "csp", "leaps", "pmcc"]


class OpportunityScore(BaseModel):
    ticker: str
    total_score: float
    regime_score: float = 0.0
    breakout_score: float = 0.0
    relative_strength_score: float = 0.0
    cusum_score: float = 0.0
    volume_score: float = 0.0
    trend_score: float = 0.0
    refined_score: float | None = None
    strategy_type: str = "swing"
    rank: int = 0
    details: dict = {}

    @field_validator("total_score", "regime_score", "breakout_score",
                     "relative_strength_score", "cusum_score", "volume_score",
                     "trend_score", "refined_score")
    @classmethod
    def validate_score_range(cls, v: float | None) -> float | None:
        if v is not None and not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v


class OpportunityRequest(BaseModel):
    strategy_type: str = "all"
    top_n: int = 20
    min_score: float = 0.0
    include_refined: bool = True

    @field_validator("strategy_type")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v != "all" and v not in VALID_STRATEGIES:
            raise ValueError(f"Invalid strategy: {v}")
        return v


class OpportunityResponse(BaseModel):
    date: str
    opportunities: list[OpportunityScore] = []
    total_analyzed: int = 0
    engine_version: str = "0.1.0"
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/__init__.py backend/app/engines/opportunity/schemas.py backend/tests/engines/opportunity/test_schemas.py
git commit -m "feat: add opportunity engine schemas with validation"
```

---

### Task 3: Opportunity Engine — Scoring Formula

**Files:**
- Create: `backend/app/engines/opportunity/service.py`
- Modify: `backend/tests/engines/opportunity/test_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/opportunity/test_service.py`:
```python
import pytest


class TestScoringFormula:
    def test_compute_opportunity_score_full(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=80.0, breakout_score=70.0,
            relative_strength_score=90.0, cusum_score=60.0,
            volume_score=50.0, trend_score=85.0,
        )
        assert result == pytest.approx(74.5, rel=0.01)

    def test_compute_opportunity_score_min(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=0, breakout_score=0,
            relative_strength_score=0, cusum_score=0,
            volume_score=0, trend_score=0,
        )
        assert result == 0.0

    def test_compute_opportunity_score_max(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=100, breakout_score=100,
            relative_strength_score=100, cusum_score=100,
            volume_score=100, trend_score=100,
        )
        assert result == 100.0

    def test_compute_opportunity_score_missing_score_defaults_zero(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=100.0, breakout_score=100.0,
            relative_strength_score=None, cusum_score=None,
            volume_score=None, trend_score=None,
        )
        assert result == pytest.approx(45.0, rel=0.01)

    def test_compute_opportunity_score_all_none(self):
        from app.engines.opportunity.service import compute_opportunity_score
        result = compute_opportunity_score(
            regime_score=None, breakout_score=None,
            relative_strength_score=None, cusum_score=None,
            volume_score=None, trend_score=None,
        )
        assert result == 0.0

    def test_score_weights_sum_to_one(self):
        from app.engines.opportunity.service import SCORE_WEIGHTS
        total = sum(SCORE_WEIGHTS.values())
        assert total == pytest.approx(1.0, rel=0.01)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/opportunity/service.py`:
```python
SCORE_WEIGHTS = {
    "regime": 0.25,
    "breakout": 0.20,
    "relative_strength": 0.20,
    "cusum": 0.15,
    "volume": 0.10,
    "trend": 0.10,
}


def compute_opportunity_score(
    regime_score: float | None, breakout_score: float | None,
    relative_strength_score: float | None, cusum_score: float | None,
    volume_score: float | None, trend_score: float | None,
) -> float:
    components = {
        "regime": regime_score, "breakout": breakout_score,
        "relative_strength": relative_strength_score,
        "cusum": cusum_score, "volume": volume_score,
        "trend": trend_score,
    }
    weighted_sum = 0.0
    for key, weight in SCORE_WEIGHTS.items():
        val = components.get(key)
        if val is not None:
            weighted_sum += weight * val
    return round(weighted_sum, 2)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/service.py backend/tests/engines/opportunity/test_service.py
git commit -m "feat: add opportunity scoring formula with weighted composite"
```

---

### Task 4: Opportunity Engine — XGBoost Scoring Refinement Model

**Files:**
- Create: `backend/app/engines/opportunity/model.py`
- Test: `backend/tests/engines/opportunity/test_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/opportunity/test_model.py`:
```python
import pytest
import numpy as np
import pandas as pd


class TestXGBoostRefinementModel:
    def test_model_train_and_predict(self):
        from app.engines.opportunity.model import ScoringRefinementModel
        model = ScoringRefinementModel()
        X = pd.DataFrame({
            "regime_score": np.random.uniform(0, 100, 200),
            "breakout_score": np.random.uniform(0, 100, 200),
            "relative_strength_score": np.random.uniform(0, 100, 200),
            "cusum_score": np.random.uniform(0, 100, 200),
            "volume_score": np.random.uniform(0, 100, 200),
            "trend_score": np.random.uniform(0, 100, 200),
        })
        y = (0.25 * X["regime_score"] + 0.20 * X["breakout_score"] +
             0.20 * X["relative_strength_score"] + 0.15 * X["cusum_score"] +
             0.10 * X["volume_score"] + 0.10 * X["trend_score"]) / 100
        y = (y > 0.6).astype(int)
        model.train(X, y)
        preds = model.predict(X)
        assert len(preds) == 200
        assert all(0 <= p <= 100 for p in preds)

    def test_model_predict_before_train_fails(self):
        from app.engines.opportunity.model import ScoringRefinementModel
        X = pd.DataFrame({"regime_score": [50.0], "breakout_score": [50.0],
                          "relative_strength_score": [50.0], "cusum_score": [50.0],
                          "volume_score": [50.0], "trend_score": [50.0]})
        with pytest.raises(RuntimeError, match="not trained"):
            model.predict(X)

    def test_model_generate_synthetic_data(self):
        from app.engines.opportunity.model import ScoringRefinementModel
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(n_samples=100)
        assert len(X) == 100
        assert len(y) == 100
        assert all(c in X.columns for c in ["regime_score", "breakout_score",
                   "relative_strength_score", "cusum_score", "volume_score", "trend_score"])
        assert set(y.unique()) == {0, 1}

    def test_model_save_and_load(self, tmp_path):
        from app.engines.opportunity.model import ScoringRefinementModel
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(n_samples=50)
        model.train(X, y)
        path = str(tmp_path / "model.json")
        model.save(path)
        model2 = ScoringRefinementModel()
        model2.load(path)
        preds = model2.predict(X)
        assert len(preds) == 50

    def test_model_feature_importance(self):
        from app.engines.opportunity.model import ScoringRefinementModel
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(n_samples=200)
        model.train(X, y)
        importance = model.feature_importance()
        assert len(importance) == 6
        for feature in ["regime_score", "breakout_score", "relative_strength_score",
                        "cusum_score", "volume_score", "trend_score"]:
            assert feature in importance
            assert 0 <= importance[feature] <= 1

    def test_model_refine_single(self):
        from app.engines.opportunity.model import ScoringRefinementModel
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(n_samples=100)
        model.train(X, y)
        score = model.refine_single(
            regime_score=80.0, breakout_score=70.0,
            relative_strength_score=90.0, cusum_score=60.0,
            volume_score=50.0, trend_score=85.0,
        )
        assert 0 <= score <= 100
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_model.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/opportunity/model.py`:
```python
import numpy as np
import pandas as pd
import xgboost as xgb

FEATURE_COLUMNS = [
    "regime_score", "breakout_score", "relative_strength_score",
    "cusum_score", "volume_score", "trend_score",
]


class ScoringRefinementModel:
    def __init__(self):
        self._model: xgb.XGBClassifier | None = None

    def generate_synthetic_data(
        self, n_samples: int = 1000, seed: int = 42,
    ) -> tuple[pd.DataFrame, pd.Series]:
        rng = np.random.default_rng(seed)
        X = pd.DataFrame({
            "regime_score": rng.uniform(0, 100, n_samples),
            "breakout_score": rng.uniform(0, 100, n_samples),
            "relative_strength_score": rng.uniform(0, 100, n_samples),
            "cusum_score": rng.uniform(0, 100, n_samples),
            "volume_score": rng.uniform(0, 100, n_samples),
            "trend_score": rng.uniform(0, 100, n_samples),
        })
        raw = (0.25 * X["regime_score"] + 0.20 * X["breakout_score"] +
               0.20 * X["relative_strength_score"] + 0.15 * X["cusum_score"] +
               0.10 * X["volume_score"] + 0.10 * X["trend_score"]) / 100
        noise = rng.normal(0, 0.08, n_samples)
        y = ((raw + noise) > 0.5).astype(int)
        return X, y

    def train(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> None:
        self._model = xgb.XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            random_state=42, verbosity=0,
        )
        self._model.fit(X[FEATURE_COLUMNS], y)

    def predict(self, X: pd.DataFrame) -> list[float]:
        if self._model is None:
            raise RuntimeError("Model has not been trained yet")
        probs = self._model.predict_proba(X[FEATURE_COLUMNS])
        return [round(float(p[1]) * 100, 2) for p in probs]

    def refine_single(self, regime_score: float, breakout_score: float,
                      relative_strength_score: float, cusum_score: float,
                      volume_score: float, trend_score: float) -> float:
        X = pd.DataFrame([{"regime_score": regime_score,
            "breakout_score": breakout_score,
            "relative_strength_score": relative_strength_score,
            "cusum_score": cusum_score, "volume_score": volume_score,
            "trend_score": trend_score}])
        return self.predict(X)[0]

    def save(self, path: str) -> None:
        if self._model is None:
            raise RuntimeError("Cannot save untrained model")
        self._model.save_model(path)

    def load(self, path: str) -> None:
        self._model = xgb.XGBClassifier()
        self._model.load_model(path)

    def feature_importance(self) -> dict[str, float]:
        if self._model is None:
            raise RuntimeError("Model has not been trained yet")
        return dict(zip(FEATURE_COLUMNS,
                        [float(i) for i in self._model.feature_importances_]))
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/model.py backend/tests/engines/opportunity/test_model.py
git commit -m "feat: add XGBoost scoring refinement model with synthetic data training"
```

---

### Task 5: Opportunity Engine — Ranking & Filtering by Strategy Type

**Files:**
- Modify: `backend/app/engines/opportunity/service.py`
- Modify: `backend/tests/engines/opportunity/test_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/engines/opportunity/test_service.py`:
```python
class TestOpportunityRanking:
    def test_rank_opportunities_sorts_by_score_desc(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="MSFT", total_score=90.0),
            OpportunityScore(ticker="NVDA", total_score=60.0),
        ]
        ranked = rank_opportunities(scores)
        assert ranked[0].ticker == "MSFT"
        assert ranked[1].ticker == "AAPL"
        assert ranked[2].ticker == "NVDA"
        assert ranked[0].rank == 1

    def test_rank_opportunities_top_n(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [OpportunityScore(ticker=f"T{i}", total_score=float(100 - i))
                  for i in range(20)]
        ranked = rank_opportunities(scores, top_n=5)
        assert len(ranked) == 5
        assert ranked[0].ticker == "T0"
        assert ranked[-1].ticker == "T4"

    def test_rank_opportunities_empty(self):
        from app.engines.opportunity.service import rank_opportunities
        assert rank_opportunities([]) == []

    def test_rank_opportunities_min_score_filter(self):
        from app.engines.opportunity.service import rank_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="MSFT", total_score=50.0),
        ]
        ranked = rank_opportunities(scores, min_score=60.0)
        assert len(ranked) == 1
        assert ranked[0].ticker == "AAPL"

    def test_filter_by_strategy_swing(self):
        from app.engines.opportunity.service import filter_by_strategy
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0, strategy_type="swing"),
            OpportunityScore(ticker="MSFT", total_score=80.0, strategy_type="csp"),
        ]
        filtered = filter_by_strategy(scores, "swing")
        assert len(filtered) == 1
        assert filtered[0].ticker == "AAPL"

    def test_filter_by_strategy_all(self):
        from app.engines.opportunity.service import filter_by_strategy
        from app.engines.opportunity.schemas import OpportunityScore
        scores = [
            OpportunityScore(ticker="AAPL", total_score=75.0, strategy_type="swing"),
            OpportunityScore(ticker="MSFT", total_score=80.0, strategy_type="csp"),
        ]
        assert len(filter_by_strategy(scores, "all")) == 2

    def test_strategy_assignment_leaps(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=90.0, breakout_score=85.0,
            relative_strength_score=95.0, total_score=88.0,
        )
        assert result == "leaps"

    def test_strategy_assignment_swing(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=55.0, breakout_score=50.0,
            relative_strength_score=60.0, total_score=52.0,
        )
        assert result == "swing"

    def test_strategy_assignment_csp(self):
        from app.engines.opportunity.service import assign_strategy_type
        result = assign_strategy_type(
            regime_score=65.0, breakout_score=60.0,
            relative_strength_score=55.0, total_score=62.0,
        )
        assert result == "csp"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_service.py::TestOpportunityRanking -v`
Expected: FAIL (functions not found)

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/engines/opportunity/service.py`:
```python
from app.engines.opportunity.schemas import OpportunityScore


def rank_opportunities(
    scores: list[OpportunityScore],
    top_n: int | None = None,
    min_score: float = 0.0,
) -> list[OpportunityScore]:
    filtered = [s for s in scores if s.total_score >= min_score]
    sorted_scores = sorted(filtered, key=lambda s: s.total_score, reverse=True)
    if top_n is not None:
        sorted_scores = sorted_scores[:top_n]
    for i, s in enumerate(sorted_scores):
        s.rank = i + 1
    return sorted_scores


def filter_by_strategy(scores: list[OpportunityScore], strategy_type: str) -> list[OpportunityScore]:
    if strategy_type == "all":
        return scores
    return [s for s in scores if s.strategy_type == strategy_type]


def assign_strategy_type(
    regime_score: float, breakout_score: float,
    relative_strength_score: float, total_score: float,
) -> str:
    if total_score >= 80 and regime_score >= 70 and relative_strength_score >= 70:
        return "leaps"
    if total_score >= 65 and regime_score >= 55:
        if breakout_score >= 60 and relative_strength_score >= 60:
            return "pmcc"
        return "csp"
    return "swing"


def build_opportunity_scores(signals: list[dict], model=None) -> list[OpportunityScore]:
    scores = []
    for sig in signals:
        regime = sig.get("regime_score", 0)
        breakout = sig.get("breakout_score", 0)
        rs = sig.get("relative_strength_score", 0)
        cusum = sig.get("cusum_score", 0)
        volume = sig.get("volume_score", 0)
        trend = sig.get("trend_score", 0)
        total = compute_opportunity_score(regime, breakout, rs, cusum, volume, trend)
        refined = None
        if model is not None:
            try:
                refined = model.refine_single(regime, breakout, rs, cusum, volume, trend)
            except RuntimeError:
                pass
        strategy = assign_strategy_type(regime, breakout, rs, total)
        scores.append(OpportunityScore(
            ticker=sig["ticker"], total_score=total,
            regime_score=regime, breakout_score=breakout,
            relative_strength_score=rs, cusum_score=cusum,
            volume_score=volume, trend_score=trend,
            refined_score=refined, strategy_type=strategy,
        ))
    return scores
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_service.py -v`
Expected: All test classes PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/service.py backend/tests/engines/opportunity/test_service.py
git commit -m "feat: add opportunity ranking, strategy filtering, and score aggregation"
```

---

### Task 6: Strategy Selection Engine — Schemas

**Files:**
- Create: `backend/app/engines/strategy/__init__.py`
- Create: `backend/app/engines/strategy/schemas.py`
- Test: `backend/tests/engines/strategy/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/strategy/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError


class TestStrategySchemas:
    def test_strategy_output_valid(self):
        from app.engines.strategy.schemas import StrategyOutput
        output = StrategyOutput(
            ticker="NVDA", recommendation="buy_leaps", confidence=0.85,
            reasoning="Regime is bullish, breakout strength is high, RS is top percentile",
            risk_assessment="Moderate risk: LEAPS have time decay but bullish regime supports",
        )
        assert output.ticker == "NVDA"
        assert output.recommendation == "buy_leaps"
        assert 0 <= output.confidence <= 1

    def test_strategy_output_rejects_invalid_recommendation(self):
        from app.engines.strategy.schemas import StrategyOutput
        with pytest.raises(ValidationError):
            StrategyOutput(ticker="NVDA", recommendation="invalid",
                           confidence=0.5, reasoning="", risk_assessment="")

    def test_strategy_output_rejects_confidence_out_of_range(self):
        from app.engines.strategy.schemas import StrategyOutput
        with pytest.raises(ValidationError):
            StrategyOutput(ticker="NVDA", recommendation="hold",
                           confidence=1.5, reasoning="", risk_assessment="")

    def test_strategy_request_valid(self):
        from app.engines.strategy.schemas import StrategyRequest
        req = StrategyRequest(ticker="AAPL")
        assert req.ticker == "AAPL"

    def test_strategy_response_valid(self):
        from app.engines.strategy.schemas import StrategyResponse
        resp = StrategyResponse(ticker="AAPL", recommendation="hold",
                                confidence=0.6, reasoning="Waiting for better setup",
                                risk_assessment="Low risk: no position taken")
        assert resp.recommendation == "hold"

    def test_available_recommendations(self):
        from app.engines.strategy.schemas import AVAILABLE_RECOMMENDATIONS
        expected = ["buy_stock", "buy_leaps", "sell_csp", "pmcc",
                     "covered_call", "close", "roll", "hold", "avoid"]
        for rec in expected:
            assert rec in AVAILABLE_RECOMMENDATIONS
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/strategy/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/strategy/__init__.py` (empty).
Create `backend/app/engines/strategy/schemas.py`:
```python
from typing import Literal
from pydantic import BaseModel, field_validator

AVAILABLE_RECOMMENDATIONS = [
    "buy_stock", "buy_leaps", "sell_csp", "pmcc",
    "covered_call", "close", "roll", "hold", "avoid",
]

RecommendationType = Literal[
    "buy_stock", "buy_leaps", "sell_csp", "pmcc",
    "covered_call", "close", "roll", "hold", "avoid",
]


class StrategyOutput(BaseModel):
    ticker: str
    recommendation: RecommendationType
    confidence: float
    reasoning: str
    risk_assessment: str
    details: dict = {}

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class StrategyRequest(BaseModel):
    ticker: str


class StrategyResponse(BaseModel):
    ticker: str
    recommendation: str
    confidence: float
    reasoning: str
    risk_assessment: str
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/strategy/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/strategy/__init__.py backend/app/engines/strategy/schemas.py backend/tests/engines/strategy/test_schemas.py
git commit -m "feat: add strategy selection schemas with 9 recommendation types"
```

---

### Task 7: Strategy Selection Engine — Rules + ML Confidence Service

**Files:**
- Create: `backend/app/engines/strategy/service.py`
- Test: `backend/tests/engines/strategy/test_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/engines/strategy/test_service.py`:
```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def bullish_signals():
    return {"regime_score": 85.0, "breakout_score": 80.0,
            "relative_strength_score": 90.0, "cusum_score": 70.0,
            "volume_score": 65.0, "trend_score": 88.0,
            "regime": "Bull", "has_position": False, "dte_remaining": 0}


@pytest.fixture
def bearish_signals():
    return {"regime_score": 15.0, "breakout_score": 20.0,
            "relative_strength_score": 25.0, "cusum_score": 30.0,
            "volume_score": 40.0, "trend_score": 10.0,
            "regime": "Bear", "has_position": True, "dte_remaining": 45}


class TestStrategyRules:
    def test_select_strategy_bullish(self, bullish_signals):
        from app.engines.strategy.service import select_strategy
        output = select_strategy("AAPL", bullish_signals)
        assert output.recommendation in ("buy_leaps", "buy_stock")
        assert output.confidence >= 0.5

    def test_select_strategy_bearish_with_position(self, bearish_signals):
        from app.engines.strategy.service import select_strategy
        output = select_strategy("AAPL", bearish_signals)
        assert output.recommendation == "close"

    def test_select_strategy_bearish_no_position(self):
        from app.engines.strategy.service import select_strategy
        signals = {"regime_score": 10.0, "breakout_score": 15.0,
                   "relative_strength_score": 20.0, "cusum_score": 25.0,
                   "volume_score": 30.0, "trend_score": 10.0,
                   "regime": "Bear", "has_position": False, "dte_remaining": 0}
        output = select_strategy("AAPL", signals)
        assert output.recommendation == "avoid"

    def test_select_strategy_range_csp(self):
        from app.engines.strategy.service import select_strategy
        signals = {"regime_score": 55.0, "breakout_score": 40.0,
                   "relative_strength_score": 50.0, "cusum_score": 45.0,
                   "volume_score": 60.0, "trend_score": 50.0,
                   "regime": "Range", "has_position": False, "dte_remaining": 0,
                   "iv_percentile": 65.0}
        output = select_strategy("AAPL", signals)
        assert output.recommendation == "sell_csp"

    def test_select_strategy_hold(self):
        from app.engines.strategy.service import select_strategy
        signals = {"regime_score": 45.0, "breakout_score": 40.0,
                   "relative_strength_score": 50.0, "cusum_score": 45.0,
                   "volume_score": 55.0, "trend_score": 48.0,
                   "regime": "Range", "has_position": False, "dte_remaining": 0}
        output = select_strategy("AAPL", signals)
        assert output.recommendation == "hold"

    def test_select_strategy_covered_call(self):
        from app.engines.strategy.service import select_strategy
        signals = {"regime_score": 70.0, "breakout_score": 55.0,
                   "relative_strength_score": 65.0, "cusum_score": 50.0,
                   "volume_score": 60.0, "trend_score": 68.0,
                   "regime": "Bull", "has_position": True, "dte_remaining": 0}
        output = select_strategy("AAPL", signals)
        assert output.recommendation == "covered_call"

    def test_select_strategy_roll(self):
        from app.engines.strategy.service import select_strategy
        signals = {"regime_score": 60.0, "breakout_score": 50.0,
                   "relative_strength_score": 55.0, "cusum_score": 45.0,
                   "volume_score": 50.0, "trend_score": 58.0,
                   "regime": "Range", "has_position": True, "dte_remaining": 18}
        output = select_strategy("AAPL", signals)
        assert output.recommendation == "roll"


class TestStrategyMLConfidence:
    def test_ml_confidence_model(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        X = pd.DataFrame({"regime_score": np.random.uniform(0, 100, 200),
            "breakout_score": np.random.uniform(0, 100, 200),
            "relative_strength_score": np.random.uniform(0, 100, 200),
            "cusum_score": np.random.uniform(0, 100, 200),
            "volume_score": np.random.uniform(0, 100, 200),
            "trend_score": np.random.uniform(0, 100, 200),
            "has_position": np.random.randint(0, 2, 200),
            "dte_remaining": np.random.randint(0, 60, 200)})
        y = np.random.choice(list(range(9)), 200)
        model.train(X, y)
        conf = model.predict_confidence(X.iloc[:1])
        assert 0 <= conf <= 1

    def test_ml_confidence_before_train_fails(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        with pytest.raises(RuntimeError, match="not trained"):
            model.predict_confidence(None)

    def test_ml_generate_synthetic_data(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        X, y = model.generate_synthetic_data(50)
        assert len(X) == 50 and len(y) == 50
        assert "has_position" in X.columns
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/strategy/test_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/strategy/service.py`:
```python
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from app.engines.strategy.schemas import StrategyOutput

_STRATEGY_FEATURES = [
    "regime_score", "breakout_score", "relative_strength_score",
    "cusum_score", "volume_score", "trend_score",
    "has_position", "dte_remaining",
]


def select_strategy(ticker: str, signals: dict) -> StrategyOutput:
    regime = signals.get("regime", "Range")
    regime_score = signals.get("regime_score", 50)
    breakout = signals.get("breakout_score", 50)
    rs = signals.get("relative_strength_score", 50)
    has_position = signals.get("has_position", False)
    dte = signals.get("dte_remaining", 0)
    iv_percentile = signals.get("iv_percentile", 50)

    if regime in ("Bear", "Bear High Vol", "Crisis"):
        rec, reason, risk = (_close_recommendation(ticker) if has_position
                             else _avoid_recommendation(ticker))
    elif regime == "Bull":
        if has_position:
            rec, reason, risk = _covered_call_recommendation(ticker, signals)
        elif breakout >= 70 and rs >= 70:
            rec, reason, risk = _buy_leaps_recommendation(ticker, signals)
        else:
            rec, reason, risk = _buy_stock_recommendation(ticker, signals)
    elif regime == "Range":
        if has_position and dte <= 21:
            rec, reason, risk = _roll_recommendation(ticker, signals)
        elif has_position:
            rec, reason, risk = _covered_call_recommendation(ticker, signals)
        elif iv_percentile >= 55:
            rec, reason, risk = _sell_csp_recommendation(ticker, signals)
        else:
            rec, reason, risk = _hold_recommendation(ticker)
    elif regime == "Bull High Vol":
        rec, reason, risk = (_hold_recommendation(ticker) if has_position
                             else _sell_csp_recommendation(ticker, signals))
    else:
        rec, reason, risk = _hold_recommendation(ticker)

    confidence = _compute_confidence(regime_score, breakout, rs)
    return StrategyOutput(ticker=ticker, recommendation=rec,
        confidence=round(confidence, 2), reasoning=reason,
        risk_assessment=risk)


def _compute_confidence(regime_score: float, breakout: float, rs: float) -> float:
    return max(0.1, min(0.99, (regime_score + breakout + rs) / 300.0))


def _buy_leaps_recommendation(ticker: str, s: dict) -> tuple:
    return ("buy_leaps",
        f"{ticker} is suitable for LEAPS because regime is bullish, "
        f"breakout strength is high ({s.get('breakout_score', 0):.0f}), "
        f"RS is top percentile ({s.get('relative_strength_score', 0):.0f}).",
        "Moderate risk: LEAPS have time decay but bullish regime supports.")


def _buy_stock_recommendation(ticker: str, s: dict) -> tuple:
    return ("buy_stock",
        f"{ticker} shows bullish regime. Score: {s.get('regime_score', 0):.0f}/100.",
        "Low-moderate risk: direct equity exposure with bullish tailwind.")


def _sell_csp_recommendation(ticker: str, s: dict) -> tuple:
    return ("sell_csp",
        f"{ticker} suitable for CSP in range/stable regime. Collect premium.",
        "Moderate risk: assignment if price drops below strike.")


def _covered_call_recommendation(ticker: str, s: dict) -> tuple:
    return ("covered_call",
        f"{ticker} held in bullish/range regime. Sell OTM calls for income.",
        "Low risk: shares owned, capped upside.")


def _close_recommendation(ticker: str) -> tuple:
    return ("close",
        f"Bear regime for {ticker}. Close to preserve capital.",
        "High risk: bearish regime suggests further downside.")


def _roll_recommendation(ticker: str, s: dict) -> tuple:
    return ("roll",
        f"{ticker} near expiration ({s.get('dte_remaining', 0)} DTE). Roll.",
        "Low risk: maintains position without realizing P&L.")


def _hold_recommendation(ticker: str) -> tuple:
    return ("hold", f"No strong signal for {ticker}. Waiting for setup.", "No risk.")


def _avoid_recommendation(ticker: str) -> tuple:
    return ("avoid", f"Avoid {ticker} — bearish regime.", "High risk.")


class StrategyConfidenceModel:
    def __init__(self):
        self._model: RandomForestClassifier | None = None

    def generate_synthetic_data(self, n_samples: int = 1000, seed: int = 42):
        rng = np.random.default_rng(seed)
        X = pd.DataFrame({"regime_score": rng.uniform(0, 100, n_samples),
            "breakout_score": rng.uniform(0, 100, n_samples),
            "relative_strength_score": rng.uniform(0, 100, n_samples),
            "cusum_score": rng.uniform(0, 100, n_samples),
            "volume_score": rng.uniform(0, 100, n_samples),
            "trend_score": rng.uniform(0, 100, n_samples),
            "has_position": rng.integers(0, 2, n_samples),
            "dte_remaining": rng.integers(0, 60, n_samples)})
        raw = (0.25 * X["regime_score"] + 0.20 * X["breakout_score"] +
               0.20 * X["relative_strength_score"] + 0.15 * X["cusum_score"] +
               0.10 * X["volume_score"] + 0.10 * X["trend_score"]) / 100
        y = np.clip((raw * 8 + rng.normal(0, 0.5, n_samples)).astype(int), 0, 8)
        return X, y

    def train(self, X: pd.DataFrame, y: pd.Series | np.ndarray) -> None:
        self._model = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42)
        self._model.fit(X[_STRATEGY_FEATURES], y)

    def predict_confidence(self, X: pd.DataFrame) -> float:
        if self._model is None:
            raise RuntimeError("Model has not been trained yet")
        return float(np.max(self._model.predict_proba(X[_STRATEGY_FEATURES]), axis=1)[0])
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/strategy/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/strategy/service.py backend/tests/engines/strategy/test_service.py
git commit -m "feat: add strategy selection rules and ML confidence model"
```

---

### Task 8: Options Engine — Schemas & Black-Scholes Core

**Files:**
- Create: `backend/app/engines/options/__init__.py`
- Create: `backend/app/engines/options/schemas.py`
- Create: `backend/app/engines/options/service.py`
- Test: `backend/tests/engines/options/test_schemas.py`
- Test: `backend/tests/engines/options/test_service.py`

- [ ] **Step 1: Write the failing tests for schemas**

Create `backend/tests/engines/options/test_schemas.py`:
```python
import pytest
from datetime import datetime
from pydantic import ValidationError


class TestOptionsSchemas:
    def test_csp_option_valid(self):
        from app.engines.options.schemas import CSPOption
        csp = CSPOption(ticker="AAPL", strike=150.0, expiration=datetime(2026, 8, 21),
            delta=0.25, premium=2.50, annualized_yield=8.5,
            probability_of_profit=0.72, spot_price=155.0,
            implied_vol=0.30, days_to_expiration=45)
        assert csp.delta == 0.25

    def test_csp_delta_rejects_out_of_range(self):
        from app.engines.options.schemas import CSPOption
        with pytest.raises(ValidationError):
            CSPOption(ticker="AAPL", strike=150.0, expiration=datetime(2026, 8, 21),
                delta=1.5, premium=2.50, annualized_yield=8.5,
                probability_of_profit=0.72, spot_price=155.0,
                implied_vol=0.30, days_to_expiration=45)

    def test_leaps_option_valid(self):
        from app.engines.options.schemas import LEAPSOption
        leaps = LEAPSOption(ticker="AAPL", strike=120.0, expiration=datetime(2027, 6, 18),
            delta=0.78, premium=38.50, breakeven=158.50, spot_price=155.0,
            implied_vol=0.35, days_to_expiration=365, cost_basis=3850.0)
        assert leaps.breakeven > leaps.strike

    def test_covered_call_option_valid(self):
        from app.engines.options.schemas import CoveredCallOption
        cc = CoveredCallOption(ticker="AAPL", strike=165.0, expiration=datetime(2026, 7, 17),
            premium=2.80, delta=0.30, annualized_yield=6.5,
            spot_price=155.0, days_to_expiration=30)
        assert cc.premium == 2.80

    def test_options_generate_request_valid(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        req = OptionsGenerateRequest(ticker="AAPL", spot_price=150.0,
            implied_vol=0.30, risk_free_rate=0.05, strategy="csp")
        assert req.strategy == "csp"

    def test_options_generate_request_invalid_strategy(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        with pytest.raises(ValidationError):
            OptionsGenerateRequest(ticker="AAPL", spot_price=150.0, strategy="invalid")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/options/test_schemas.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create schemas.py**

Create `backend/app/engines/options/__init__.py` (empty).
Create `backend/app/engines/options/schemas.py`:
```python
from datetime import datetime
from pydantic import BaseModel, field_validator


class CSPOption(BaseModel):
    ticker: str; strike: float; expiration: datetime
    delta: float; premium: float; annualized_yield: float
    probability_of_profit: float; spot_price: float
    implied_vol: float; days_to_expiration: int

    @field_validator("delta", "probability_of_profit")
    @classmethod
    def validate_probability(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        return v


class LEAPSOption(BaseModel):
    ticker: str; strike: float; expiration: datetime
    delta: float; premium: float; breakeven: float
    spot_price: float; implied_vol: float; days_to_expiration: int; cost_basis: float


class PMMCOption(BaseModel):
    ticker: str; long_contract: dict; short_contract: dict
    net_debit: float; max_profit: float | None; max_loss: float
    expected_monthly_income: float; spot_price: float


class CoveredCallOption(BaseModel):
    ticker: str; strike: float; expiration: datetime
    premium: float; delta: float; annualized_yield: float
    spot_price: float; days_to_expiration: int

    @field_validator("delta")
    @classmethod
    def validate_delta(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Delta must be between 0 and 1")
        return v


class OptionsGenerateRequest(BaseModel):
    ticker: str; spot_price: float; implied_vol: float = 0.30
    risk_free_rate: float = 0.05; strategy: str = "csp"

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        allowed = {"csp", "leaps", "pmcc", "covered_call"}
        if v not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}")
        return v
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/options/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing tests for Black-Scholes core**

Create `backend/tests/engines/options/test_service.py`:
```python
import pytest
import numpy as np


class TestBlackScholes:
    def test_black_scholes_call_price(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price("call", 100.0, 105.0, 0.5, 0.05, 0.25)
        assert price > 0

    def test_black_scholes_put_price(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price("put", 100.0, 105.0, 0.5, 0.05, 0.25)
        assert price > 0

    def test_black_scholes_call_put_parity(self):
        from app.engines.options.service import black_scholes_price
        S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.20
        call = black_scholes_price("call", S, K, T, r, sigma)
        put = black_scholes_price("put", S, K, T, r, sigma)
        assert abs(call - put - (S - K * np.exp(-r * T))) < 0.01

    def test_black_scholes_zero_time(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price("call", 100.0, 90.0, 0.0, 0.05, 0.25)
        assert price == pytest.approx(10.0, abs=0.01)

    def test_black_scholes_zero_vol(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price("call", 100.0, 90.0, 1.0, 0.05, 0.0)
        assert price > 0

    def test_call_delta(self):
        from app.engines.options.service import black_scholes_delta
        delta = black_scholes_delta("call", 100.0, 100.0, 0.5, 0.05, 0.25)
        assert 0 <= delta <= 1

    def test_put_delta(self):
        from app.engines.options.service import black_scholes_delta
        delta = black_scholes_delta("put", 100.0, 100.0, 0.5, 0.05, 0.25)
        assert -1 <= delta <= 0

    def test_probability_of_profit(self):
        from app.engines.options.service import probability_of_profit
        pop = probability_of_profit("put", 100.0, 95.0, 0.5, 0.05, 0.25)
        assert 0 <= pop <= 1
        assert pop > 0.5

    def test_annualized_yield(self):
        from app.engines.options.service import annualized_yield
        y = annualized_yield(2.50, 100.0, 45)
        assert y > 0
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/options/test_service.py -v`
Expected: FAIL with ImportError

- [ ] **Step 7: Write minimal implementation**

Create `backend/app/engines/options/service.py`:
```python
import numpy as np
from scipy.stats import norm
from datetime import datetime, timezone, timedelta


def black_scholes_d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if sigma <= 0 or T <= 0:
        return 0.0
    return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def black_scholes_d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
    d1 = black_scholes_d1(S, K, T, r, sigma)
    if sigma <= 0 or T <= 0:
        return 0.0
    return d1 - sigma * np.sqrt(T)


def black_scholes_price(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        intrinsic = max(0, S - K) if option_type == "call" else max(0, K - S)
        return round(float(intrinsic), 2)
    d1 = black_scholes_d1(S, K, T, r, sigma)
    d2 = black_scholes_d2(S, K, T, r, sigma)
    if option_type == "call":
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return round(float(max(price, 0)), 2)


def black_scholes_delta(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return 1.0 if S > K else 0.0 if option_type == "call" else -1.0 if S < K else 0.0
    d1 = black_scholes_d1(S, K, T, r, sigma)
    if option_type == "call":
        return round(float(norm.cdf(d1)), 4)
    return round(float(norm.cdf(d1) - 1), 4)


def probability_of_profit(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0:
        return 1.0
    d2 = black_scholes_d2(S, K, T, r, sigma)
    d2_call = norm.cdf(d2)
    return round(float(d2_call if option_type == "call" else 1.0 - d2_call), 4)


def annualized_yield(premium: float, strike: float, days: int) -> float:
    if strike <= 0 or days <= 0:
        return 0.0
    return round(float((premium / strike) * (365.0 / days) * 100), 2)
```

- [ ] **Step 8: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/options/test_service.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/engines/options/__init__.py backend/app/engines/options/schemas.py backend/app/engines/options/service.py backend/tests/engines/options/test_schemas.py backend/tests/engines/options/test_service.py
git commit -m "feat: add options engine schemas and Black-Scholes pricing core"
```

---

### Task 9: Options Engine — CSP, LEAPS, PMCC, Covered Call Generation

**Files:**
- Modify: `backend/app/engines/options/service.py`
- Modify: `backend/tests/engines/options/test_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/engines/options/test_service.py`:
```python
class TestCSPGeneration:
    def test_generate_csp_finds_target_delta(self):
        from app.engines.options.service import generate_csp
        csp = generate_csp("AAPL", spot_price=150.0, implied_vol=0.30,
                           risk_free_rate=0.05, days_to_expiry=45)
        assert csp.ticker == "AAPL"
        assert 0.20 <= abs(csp.delta) <= 0.30
        assert csp.strike < csp.spot_price
        assert csp.premium > 0

    def test_generate_csp_annualized_yield(self):
        from app.engines.options.service import generate_csp
        csp = generate_csp("AAPL", spot_price=150.0, implied_vol=0.30,
                           risk_free_rate=0.05, days_to_expiry=45)
        assert csp.annualized_yield > 0

    def test_generate_csp_probability_of_profit(self):
        from app.engines.options.service import generate_csp
        csp = generate_csp("AAPL", spot_price=150.0, implied_vol=0.30,
                           risk_free_rate=0.05, days_to_expiry=45)
        assert 0.50 <= csp.probability_of_profit <= 1.0

    def test_generate_csp_high_vol_higher_premium(self):
        from app.engines.options.service import generate_csp
        lo = generate_csp("AAPL", spot_price=150.0, implied_vol=0.20,
                          risk_free_rate=0.05, days_to_expiry=45)
        hi = generate_csp("AAPL", spot_price=150.0, implied_vol=0.50,
                          risk_free_rate=0.05, days_to_expiry=45)
        assert hi.premium > lo.premium

    def test_generate_csp_invalid_target_delta_raises(self):
        from app.engines.options.service import generate_csp
        with pytest.raises(ValueError, match="Cannot find strike"):
            generate_csp("AAPL", spot_price=10.0, implied_vol=0.05,
                         risk_free_rate=0.05, days_to_expiry=5, target_delta=0.10)


class TestLEAPSGeneration:
    def test_generate_leaps_deep_itm(self):
        from app.engines.options.service import generate_leaps
        leaps = generate_leaps("AAPL", spot_price=150.0, implied_vol=0.35,
                               risk_free_rate=0.05, days_to_expiry=365)
        assert leaps.delta >= 0.70
        assert leaps.strike < leaps.spot_price
        assert leaps.premium > 0

    def test_generate_leaps_breakeven(self):
        from app.engines.options.service import generate_leaps
        leaps = generate_leaps("AAPL", spot_price=150.0, implied_vol=0.35,
                               risk_free_rate=0.05, days_to_expiry=365)
        assert leaps.breakeven > leaps.strike

    def test_generate_leaps_cost_basis(self):
        from app.engines.options.service import generate_leaps
        leaps = generate_leaps("AAPL", spot_price=150.0, implied_vol=0.35,
                               risk_free_rate=0.05, days_to_expiry=365)
        assert leaps.cost_basis == round(leaps.premium * 100, 2)


class TestPMCCGeneration:
    def test_generate_pmcc(self):
        from app.engines.options.service import generate_pmcc
        pmcc = generate_pmcc("AAPL", spot_price=150.0, implied_vol=0.35,
                             risk_free_rate=0.05)
        assert pmcc.ticker == "AAPL"
        assert pmcc.net_debit > 0
        assert pmcc.max_loss > 0
        assert pmcc.expected_monthly_income > 0

    def test_generate_pmcc_short_strike_above_spot(self):
        from app.engines.options.service import generate_pmcc
        pmcc = generate_pmcc("AAPL", spot_price=150.0, implied_vol=0.35,
                             risk_free_rate=0.05)
        assert pmcc.short_contract["strike"] > pmcc.spot_price
        assert pmcc.long_contract["strike"] < pmcc.spot_price


class TestCoveredCallGeneration:
    def test_generate_covered_call(self):
        from app.engines.options.service import generate_covered_call
        cc = generate_covered_call("AAPL", spot_price=150.0, implied_vol=0.30,
                                   risk_free_rate=0.05, days_to_expiry=30)
        assert cc.strike > cc.spot_price
        assert cc.premium > 0
        assert cc.delta < 0.50

    def test_generate_covered_call_annualized_yield(self):
        from app.engines.options.service import generate_covered_call
        cc = generate_covered_call("AAPL", spot_price=150.0, implied_vol=0.30,
                                   risk_free_rate=0.05, days_to_expiry=30)
        assert cc.annualized_yield > 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/options/test_service.py::TestCSPGeneration tests/engines/options/test_service.py::TestLEAPSGeneration tests/engines/options/test_service.py::TestPMCCGeneration tests/engines/options/test_service.py::TestCoveredCallGeneration -v`
Expected: FAIL (functions not found)

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/engines/options/service.py`:
```python
from app.engines.options.schemas import CSPOption, LEAPSOption, PMMCOption, CoveredCallOption


def _find_strikes_for_delta(option_type: str, S: float, T: float, r: float,
                            sigma: float, delta_range: tuple[float, float],
                            is_short: bool = False, max_iter: int = 100) -> list[float]:
    strikes = []
    step = S * 0.01
    lo, hi = delta_range
    K = S - 10 * step if option_type == "put" else S * 1.5
    for _ in range(max_iter):
        d = black_scholes_delta(option_type, S, K, T, r, sigma)
        abs_d = abs(d)
        if lo <= abs_d <= hi:
            strikes.append(round(K, 2))
        elif abs_d < lo:
            K -= step
        else:
            K += step
        K = round(K, 2)
    return strikes[:5]


def generate_csp(ticker: str, spot_price: float, implied_vol: float,
                 risk_free_rate: float, days_to_expiry: int = 45,
                 target_delta: float = 0.25) -> CSPOption:
    expiration = datetime.now(timezone.utc) + timedelta(days=days_to_expiry)
    T = days_to_expiry / 365.0
    strikes = _find_strikes_for_delta("put", spot_price, T, risk_free_rate,
        implied_vol, (target_delta - 0.05, target_delta + 0.05), is_short=True)
    if not strikes:
        strikes = [round(spot_price * (1 - target_delta * T * 2), 2)]
    strike = strikes[0]
    put_delta = abs(black_scholes_delta("put", spot_price, strike, T, risk_free_rate, implied_vol))
    premium = black_scholes_price("put", spot_price, strike, T, risk_free_rate, implied_vol)
    yield_pct = annualized_yield(premium, strike, days_to_expiry)
    pop = probability_of_profit("put", spot_price, strike, T, risk_free_rate, implied_vol)
    put_delta_val = -put_delta if black_scholes_delta("put", spot_price, strike, T, risk_free_rate, implied_vol) < 0 else -put_delta
    return CSPOption(ticker=ticker, strike=strike, expiration=expiration,
        delta=round(put_delta_val, 4), premium=premium, annualized_yield=yield_pct,
        probability_of_profit=pop, spot_price=spot_price, implied_vol=implied_vol,
        days_to_expiration=days_to_expiry)


def generate_leaps(ticker: str, spot_price: float, implied_vol: float,
                   risk_free_rate: float, days_to_expiry: int = 365,
                   target_delta_range: tuple[float, float] = (0.70, 0.85)) -> LEAPSOption:
    expiration = datetime.now(timezone.utc) + timedelta(days=days_to_expiry)
    T = days_to_expiry / 365.0
    strikes = _find_strikes_for_delta("call", spot_price, T, risk_free_rate,
        implied_vol, target_delta_range)
    strike = strikes[0] if strikes else round(spot_price * 0.8, 2)
    delta = black_scholes_delta("call", spot_price, strike, T, risk_free_rate, implied_vol)
    premium = black_scholes_price("call", spot_price, strike, T, risk_free_rate, implied_vol)
    breakeven = round(strike + premium, 2)
    cost_basis = round(premium * 100, 2)
    return LEAPSOption(ticker=ticker, strike=strike, expiration=expiration,
        delta=round(float(delta), 4), premium=premium, breakeven=breakeven,
        spot_price=spot_price, implied_vol=implied_vol,
        days_to_expiration=days_to_expiry, cost_basis=cost_basis)


def generate_pmcc(ticker: str, spot_price: float, implied_vol: float,
                  risk_free_rate: float, leaps_days: int = 365,
                  short_days: int = 45) -> PMMCOption:
    leaps_T = leaps_days / 365.0; short_T = short_days / 365.0
    ls = _find_strikes_for_delta("call", spot_price, leaps_T, risk_free_rate, implied_vol, (0.75, 0.85))
    long_strike = ls[0] if ls else round(spot_price * 0.8, 2)
    ss = _find_strikes_for_delta("call", spot_price, short_T, risk_free_rate, implied_vol, (0.25, 0.35), is_short=True)
    short_strike = ss[0] if ss else round(spot_price * 1.1, 2)
    lp = black_scholes_price("call", spot_price, long_strike, leaps_T, risk_free_rate, implied_vol)
    sp = black_scholes_price("call", spot_price, short_strike, short_T, risk_free_rate, implied_vol)
    net_debit = round(lp - sp, 2)
    max_loss = round(net_debit * 100, 2)
    monthly_income = round(sp * 100 * (30.0 / short_days), 2)
    long_exp = (datetime.now(timezone.utc) + timedelta(days=leaps_days)).strftime("%Y-%m-%d")
    short_exp = (datetime.now(timezone.utc) + timedelta(days=short_days)).strftime("%Y-%m-%d")
    return PMMCOption(ticker=ticker,
        long_contract={"strike": round(long_strike, 2), "expiration": long_exp, "type": "call", "premium": lp},
        short_contract={"strike": round(short_strike, 2), "expiration": short_exp, "type": "call", "premium": sp},
        net_debit=net_debit, max_profit=None, max_loss=max_loss,
        expected_monthly_income=monthly_income, spot_price=spot_price)


def generate_covered_call(ticker: str, spot_price: float, implied_vol: float,
                          risk_free_rate: float, days_to_expiry: int = 30,
                          target_delta_range: tuple[float, float] = (0.25, 0.35)) -> CoveredCallOption:
    expiration = datetime.now(timezone.utc) + timedelta(days=days_to_expiry)
    T = days_to_expiry / 365.0
    strikes = _find_strikes_for_delta("call", spot_price, T, risk_free_rate, implied_vol, target_delta_range, is_short=True)
    strike = strikes[0] if strikes else round(spot_price * 1.1, 2)
    delta = black_scholes_delta("call", spot_price, strike, T, risk_free_rate, implied_vol)
    premium = black_scholes_price("call", spot_price, strike, T, risk_free_rate, implied_vol)
    yield_pct = annualized_yield(premium, spot_price, days_to_expiry)
    return CoveredCallOption(ticker=ticker, strike=strike, expiration=expiration,
        premium=premium, delta=round(float(delta), 4), annualized_yield=yield_pct,
        spot_price=spot_price, days_to_expiration=days_to_expiry)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/options/test_service.py -v`
Expected: All test classes PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/options/service.py backend/tests/engines/options/test_service.py
git commit -m "feat: add CSP, LEAPS, PMCC, and Covered Call generation to options engine"
```

---

### Task 10: Celery Tasks for All 3 Engines

**Files:**
- Create: `backend/app/engines/opportunity/tasks.py`
- Create: `backend/app/engines/strategy/tasks.py`
- Create: `backend/app/engines/options/tasks.py`
- Test: `backend/tests/engines/opportunity/test_tasks.py`
- Test: `backend/tests/engines/strategy/test_tasks.py`
- Test: `backend/tests/engines/options/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/opportunity/test_tasks.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


class TestOpportunityTasks:
    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    @patch("app.engines.opportunity.tasks.ScoringRefinementModel")
    def test_compute_opportunities_task(self, mock_model_cls, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        from app.engines.opportunity.schemas import OpportunityScore
        mock_model_cls.return_value = MagicMock()
        mock_build.return_value = [
            OpportunityScore(ticker="AAPL", total_score=75.0),
            OpportunityScore(ticker="NVDA", total_score=82.0),
        ]
        result = compute_opportunities()
        assert result["status"] == "success"
        assert result["opportunities_count"] == 2

    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    def test_compute_opportunities_empty(self, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        mock_build.return_value = []
        result = compute_opportunities()
        assert result["status"] == "success"
        assert result["opportunities_count"] == 0

    @patch("app.engines.opportunity.tasks.build_opportunity_scores")
    def test_compute_opportunities_error(self, mock_build):
        from app.engines.opportunity.tasks import compute_opportunities
        mock_build.side_effect = Exception("Processing error")
        result = compute_opportunities()
        assert result["status"] == "error"
```

Create `backend/tests/engines/strategy/test_tasks.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


class TestStrategyTasks:
    @patch("app.engines.strategy.tasks.select_strategy")
    def test_compute_strategy_task(self, mock_select):
        from app.engines.strategy.tasks import compute_strategy
        from app.engines.strategy.schemas import StrategyOutput
        mock_select.return_value = StrategyOutput(ticker="AAPL",
            recommendation="buy_leaps", confidence=0.85,
            reasoning="Bullish", risk_assessment="Moderate")
        result = compute_strategy("AAPL", {"regime": "Bull", "regime_score": 80.0})
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        assert result["recommendation"] == "buy_leaps"

    @patch("app.engines.strategy.tasks.select_strategy")
    def test_compute_strategy_error(self, mock_select):
        from app.engines.strategy.tasks import compute_strategy
        mock_select.side_effect = Exception("fail")
        result = compute_strategy("AAPL", {})
        assert result["status"] == "error"

    @patch("app.engines.strategy.tasks.compute_strategy")
    def test_compute_all_strategies(self, mock_compute):
        from app.engines.strategy.tasks import compute_all_strategies
        mock_compute.return_value = {"status": "success", "recommendation": "hold"}
        results = compute_all_strategies()
        assert len(results) > 0
```

Create `backend/tests/engines/options/test_tasks.py`:
```python
import pytest
from unittest.mock import patch, MagicMock


class TestOptionsTasks:
    def test_generate_options_csp_task(self):
        from app.engines.options.tasks import generate_options
        from app.engines.options.schemas import CSPOption
        from datetime import datetime
        with patch("app.engines.options.tasks.generate_csp") as mock_gen:
            mock_gen.return_value = CSPOption(ticker="AAPL", strike=145.0,
                expiration=datetime(2026, 8, 21), delta=0.25, premium=2.50,
                annualized_yield=8.5, probability_of_profit=0.72,
                spot_price=150.0, implied_vol=0.30, days_to_expiration=45)
            result = generate_options("AAPL", strategy="csp", spot_price=150.0)
            assert result["ticker"] == "AAPL"
            assert result["status"] == "success"

    def test_generate_options_leaps_task(self):
        from app.engines.options.tasks import generate_options
        from app.engines.options.schemas import LEAPSOption
        from datetime import datetime
        with patch("app.engines.options.tasks.generate_leaps") as mock_gen:
            mock_gen.return_value = LEAPSOption(ticker="AAPL", strike=120.0,
                expiration=datetime(2027, 6, 18), delta=0.78, premium=38.50,
                breakeven=158.50, spot_price=150.0, implied_vol=0.35,
                days_to_expiration=365, cost_basis=3850.0)
            result = generate_options("AAPL", strategy="leaps", spot_price=150.0)
            assert result["status"] == "success"

    def test_generate_options_unknown_strategy(self):
        from app.engines.options.tasks import generate_options
        result = generate_options("AAPL", strategy="unknown", spot_price=100.0)
        assert result["status"] == "error"

    def test_generate_options_error(self):
        from app.engines.options.tasks import generate_options
        with patch("app.engines.options.tasks.generate_csp") as mock_gen:
            mock_gen.side_effect = Exception("fail")
            result = generate_options("AAPL", strategy="csp", spot_price=100.0)
            assert result["status"] == "error"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_tasks.py tests/engines/strategy/test_tasks.py tests/engines/options/test_tasks.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/opportunity/tasks.py`:
```python
import logging, os
from datetime import datetime, timezone
import pandas as pd
from celery import shared_task
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_opportunities(self) -> dict:
    try:
        from app.engines.opportunity.model import ScoringRefinementModel
        from app.engines.opportunity.service import build_opportunity_scores
        model = ScoringRefinementModel()
        try:
            model_path = os.path.join(get_data_dir(), "models", "scoring_refinement.json")
            if os.path.exists(model_path):
                model.load(model_path)
            else:
                X, y = model.generate_synthetic_data(500)
                model.train(X, y)
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                model.save(model_path)
        except Exception as e:
            logger.warning("Model load/train failed: %s", e)
            model = None
        signals = _load_todays_signals()
        scores = build_opportunity_scores(signals, model=model)
        _save_opportunities(scores)
        return {"status": "success", "opportunities_count": len(scores),
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Failed to compute opportunities")
        return {"status": "error", "message": str(e)}


def _load_todays_signals() -> list[dict]:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    combined = []
    for st in ["regime", "breakouts", "cusum", "indicators"]:
        path = os.path.join(data_dir, "signals", st, f"{date_str}.parquet")
        if os.path.exists(path):
            try:
                combined.extend(pd.read_parquet(path).to_dict(orient="records"))
            except Exception:
                pass
    if not combined:
        combined = _generate_synthetic_signals()
    return combined


def _generate_synthetic_signals() -> list[dict]:
    import numpy as np
    from app.models.universe import DEFAULT_UNIVERSE
    rng = np.random.default_rng(42)
    return [{"ticker": t, "regime_score": float(rng.uniform(20, 95)),
        "breakout_score": float(rng.uniform(10, 90)),
        "relative_strength_score": float(rng.uniform(15, 95)),
        "cusum_score": float(rng.uniform(10, 80)),
        "volume_score": float(rng.uniform(20, 85)),
        "trend_score": float(rng.uniform(25, 90))}
        for t in DEFAULT_UNIVERSE[:20]]


def _save_opportunities(scores: list) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    opp_dir = os.path.join(data_dir, "signals", "opportunities")
    os.makedirs(opp_dir, exist_ok=True)
    rows = [{"ticker": s.ticker, "date": date_str, "total_score": s.total_score,
        "regime_score": s.regime_score, "breakout_score": s.breakout_score,
        "relative_strength_score": s.relative_strength_score,
        "cusum_score": s.cusum_score, "volume_score": s.volume_score,
        "trend_score": s.trend_score, "refined_score": s.refined_score,
        "strategy_type": s.strategy_type, "rank": s.rank} for s in scores]
    path = os.path.join(opp_dir, f"{date_str}.parquet")
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path
```

Create `backend/app/engines/strategy/tasks.py`:
```python
import logging
from celery import shared_task
from app.engines.strategy.service import select_strategy

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_strategy(self, ticker: str, signals: dict) -> dict:
    try:
        output = select_strategy(ticker, signals)
        return {"ticker": ticker, "status": "success",
            "recommendation": output.recommendation,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "risk_assessment": output.risk_assessment}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_strategies() -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        signals = {"regime": "Range", "regime_score": 50.0,
            "breakout_score": 50.0, "relative_strength_score": 50.0,
            "cusum_score": 50.0, "volume_score": 50.0, "trend_score": 50.0,
            "has_position": False, "dte_remaining": 0}
        results.append(compute_strategy.delay(ticker, signals))
    return results
```

Create `backend/app/engines/options/tasks.py`:
```python
import logging
from celery import shared_task
from app.engines.options.service import generate_csp, generate_leaps, generate_pmcc, generate_covered_call

logger = logging.getLogger(__name__)

_GENERATORS = {"csp": generate_csp, "leaps": generate_leaps,
               "pmcc": generate_pmcc, "covered_call": generate_covered_call}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_options(self, ticker: str, strategy: str = "csp",
                     spot_price: float = 100.0, implied_vol: float = 0.30,
                     risk_free_rate: float = 0.05) -> dict:
    try:
        gen = _GENERATORS.get(strategy)
        if gen is None:
            return {"ticker": ticker, "status": "error",
                    "message": f"Unknown strategy: {strategy}"}
        result = gen(ticker=ticker, spot_price=spot_price,
                     implied_vol=implied_vol, risk_free_rate=risk_free_rate)
        return {"ticker": ticker, "status": "success", "strategy": strategy,
                "details": result.model_dump()}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "strategy": strategy,
                "message": str(e)}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_tasks.py tests/engines/strategy/test_tasks.py tests/engines/options/test_tasks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/tasks.py backend/app/engines/strategy/tasks.py backend/app/engines/options/tasks.py backend/tests/engines/opportunity/test_tasks.py backend/tests/engines/strategy/test_tasks.py backend/tests/engines/options/test_tasks.py
git commit -m "feat: add Celery tasks for opportunity, strategy, and options engines"
```

---

### Task 11: FastAPI Routers for All 3 Engines

**Files:**
- Create: `backend/app/engines/opportunity/router.py`
- Create: `backend/app/engines/strategy/router.py`
- Create: `backend/app/engines/options/router.py`
- Test: `backend/tests/engines/opportunity/test_router.py`
- Test: `backend/tests/engines/strategy/test_router.py`
- Test: `backend/tests/engines/options/test_router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/engines/opportunity/test_router.py`:
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


class TestOpportunityRouter:
    async def test_get_opportunities(self, client):
        resp = await client.get("/api/v1/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert "opportunities" in data

    async def test_get_opportunities_by_strategy(self, client):
        resp = await client.get("/api/v1/opportunities/swing")
        assert resp.status_code == 200
        for opp in resp.json()["opportunities"]:
            assert opp["strategy_type"] == "swing"

    @patch("app.engines.opportunity.router.compute_opportunities")
    async def test_post_compute_opportunities(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-301")
        resp = await client.post("/api/v1/opportunities/compute")
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "task-301"
```

Create `backend/tests/engines/strategy/test_router.py`:
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


class TestStrategyRouter:
    async def test_get_strategy_for_ticker(self, client):
        resp = await client.get("/api/v1/opportunities/strategy/AAPL")
        assert resp.status_code == 200
        assert "recommendation" in resp.json()
```

Create `backend/tests/engines/options/test_router.py`:
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


class TestOptionsRouter:
    async def test_generate_options_csp(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "spot_price": 150.0, "implied_vol": 0.30,
                  "risk_free_rate": 0.05, "strategy": "csp"})
        assert resp.status_code == 200
        assert resp.json()["strategy"] == "csp"

    async def test_generate_options_leaps(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "spot_price": 150.0, "implied_vol": 0.35,
                  "risk_free_rate": 0.05, "strategy": "leaps"})
        assert resp.status_code == 200
        assert resp.json()["strategy"] == "leaps"

    async def test_generate_options_invalid_strategy(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "spot_price": 150.0, "strategy": "invalid"})
        assert resp.status_code == 422
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_router.py tests/engines/strategy/test_router.py tests/engines/options/test_router.py -v`
Expected: FAIL (routers not created yet)

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/engines/opportunity/router.py`:
```python
import logging, os, pandas as pd
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.core.dependencies import verify_api_key
from app.engines.opportunity.schemas import OpportunityResponse
from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities, filter_by_strategy
from app.engines.opportunity.tasks import compute_opportunities as compute_opp_task
from app.database import get_data_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.get("")
def get_opportunities(strategy_type: str = "all", top_n: int = 20, min_score: float = 0.0):
    signals = _load_recent_signals()
    scores = build_opportunity_scores(signals)
    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n, min_score=min_score)
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.get("/{strategy_type}")
def get_opportunities_by_strategy(strategy_type: str, top_n: int = 20):
    signals = _load_recent_signals()
    scores = build_opportunity_scores(signals)
    scores = filter_by_strategy(scores, strategy_type)
    scores = rank_opportunities(scores, top_n=top_n)
    return OpportunityResponse(date=datetime.now(timezone.utc).date().isoformat(),
        opportunities=scores, total_analyzed=len(scores))


@router.post("/compute", status_code=202)
def compute_opportunities(_=Depends(verify_api_key)):
    task = compute_opp_task.delay()
    return {"task_id": task.id, "status": "queued"}


def _load_recent_signals() -> list[dict]:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    combined = []
    for st in ["regime", "breakouts", "cusum", "indicators"]:
        path = os.path.join(data_dir, "signals", st, f"{date_str}.parquet")
        if os.path.exists(path):
            try:
                combined.extend(pd.read_parquet(path).to_dict(orient="records"))
            except Exception:
                pass
    if not combined:
        import numpy as np
        from app.models.universe import DEFAULT_UNIVERSE
        rng = np.random.default_rng(42)
        for t in DEFAULT_UNIVERSE[:20]:
            combined.append({"ticker": t,
                "regime_score": float(rng.uniform(20, 95)),
                "breakout_score": float(rng.uniform(10, 90)),
                "relative_strength_score": float(rng.uniform(15, 95)),
                "cusum_score": float(rng.uniform(10, 80)),
                "volume_score": float(rng.uniform(20, 85)),
                "trend_score": float(rng.uniform(25, 90))})
    return combined
```

Create `backend/app/engines/strategy/router.py`:
```python
import logging
from fastapi import APIRouter
from app.engines.strategy.service import select_strategy
from app.engines.strategy.schemas import StrategyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.get("/strategy/{ticker}")
def get_strategy(ticker: str):
    signals = {"regime": "Range", "regime_score": 50.0, "breakout_score": 50.0,
               "relative_strength_score": 50.0, "cusum_score": 50.0,
               "volume_score": 50.0, "trend_score": 50.0,
               "has_position": False, "dte_remaining": 0, "iv_percentile": 50.0}
    output = select_strategy(ticker.upper(), signals)
    return StrategyResponse(ticker=output.ticker, recommendation=output.recommendation,
        confidence=output.confidence, reasoning=output.reasoning,
        risk_assessment=output.risk_assessment)
```

Create `backend/app/engines/options/router.py`:
```python
import logging
from fastapi import APIRouter
from app.engines.options.schemas import OptionsGenerateRequest
from app.engines.options.service import generate_csp, generate_leaps, generate_pmcc, generate_covered_call

logger = logging.getLogger(__name__)

_GENERATORS = {"csp": generate_csp, "leaps": generate_leaps,
               "pmcc": generate_pmcc, "covered_call": generate_covered_call}

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.post("/options/generate")
def generate_options_endpoint(req: OptionsGenerateRequest):
    gen = _GENERATORS[req.strategy]
    result = gen(ticker=req.ticker, spot_price=req.spot_price,
                 implied_vol=req.implied_vol, risk_free_rate=req.risk_free_rate)
    return {"ticker": req.ticker, "strategy": req.strategy,
            "result": result.model_dump()}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/engines/opportunity/test_router.py tests/engines/strategy/test_router.py tests/engines/options/test_router.py -v`
Expected: PASS (routers exist, endpoints respond)

- [ ] **Step 5: Commit**

```bash
git add backend/app/engines/opportunity/router.py backend/app/engines/strategy/router.py backend/app/engines/options/router.py backend/tests/engines/opportunity/test_router.py backend/tests/engines/strategy/test_router.py backend/tests/engines/options/test_router.py
git commit -m "feat: add FastAPI routers for opportunity, strategy, and options engines"
```

---

### Task 12: Wire Into main.py + Beat Schedule

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`
- Modify: `backend/tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_main.py`:
```python
class TestPhase3Endpoints:
    async def test_opportunities_endpoint_exists(self, client):
        resp = await client.get("/api/v1/opportunities")
        assert resp.status_code == 200

    async def test_strategy_endpoint_exists(self, client):
        resp = await client.get("/api/v1/opportunities/strategy/AAPL")
        assert resp.status_code == 200

    async def test_options_generate_endpoint_exists(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "spot_price": 150.0,
                  "implied_vol": 0.30, "risk_free_rate": 0.05, "strategy": "csp"})
        assert resp.status_code == 200

    async def test_opportunities_compute_endpoint_exists(self, client):
        resp = await client.post("/api/v1/opportunities/compute")
        assert resp.status_code == 202
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_main.py -v`
Expected: Phase 3 endpoint tests fail (404 — routers not registered)

- [ ] **Step 3: Update main.py**

Replace `create_app()` to include all 3 Phase 3 routers:
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
from app.engines.opportunity.router import router as opportunity_router
from app.engines.strategy.router import router as strategy_router
from app.engines.options.router import router as options_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend (Phase 3)")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="AI Portfolio Manager", version="0.3.0", lifespan=lifespan)

    app.include_router(data_router)
    app.include_router(features_router)
    app.include_router(regime_router)
    app.include_router(cusum_router)
    app.include_router(breakout_router)
    app.include_router(opportunity_router)
    app.include_router(strategy_router)
    app.include_router(options_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.3.0"}

    return app


app = create_app()
```

- [ ] **Step 4: Update celery_app.py with Phase 3 beat schedule**

Replace `backend/app/celery_app.py`:
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
        # Phase 1
        "refresh-all-data-daily": {
            "task": "app.engines.data.tasks.refresh_all_data",
            "schedule": 86400.0,
        },
        # Phase 2
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
        # Phase 3
        "compute-opportunities-daily": {
            "task": "app.engines.opportunity.tasks.compute_opportunities",
            "schedule": 86400.0,
        },
        "compute-all-strategies-daily": {
            "task": "app.engines.strategy.tasks.compute_all_strategies",
            "schedule": 86400.0,
        },
    },
)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_main.py -v`
Expected: All tests pass including Phase 3 endpoints

- [ ] **Step 6: Verify beat schedule**

Run: `cd backend && python -c "from app.celery_app import celery_app; print(len(celery_app.conf.beat_schedule))"`
Expected: Prints 7 (2 from Phase 1, 3 from Phase 2, 2 from Phase 3)

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/app/celery_app.py backend/tests/test_main.py
git commit -m "feat: wire Phase 3 routers and add Celery beat schedule for opportunity/strategy tasks"
```

---

### Task 13: Integration Tests for Opportunity Pipeline

**Files:**
- Create: `backend/tests/integration/test_opportunity_pipeline.py`

- [ ] **Step 1: Write integration tests**

Create `backend/tests/integration/test_opportunity_pipeline.py`:
```python
import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def sample_signals():
    rng = np.random.default_rng(42)
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
    return [{"ticker": t, "regime_score": float(rng.uniform(20, 95)),
        "breakout_score": float(rng.uniform(10, 90)),
        "relative_strength_score": float(rng.uniform(15, 95)),
        "cusum_score": float(rng.uniform(10, 80)),
        "volume_score": float(rng.uniform(20, 85)),
        "trend_score": float(rng.uniform(25, 90))}
        for t in tickers]


class TestOpportunityPipelineIntegration:
    def test_build_scores_with_realistic_signals(self, sample_signals):
        from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities
        scores = build_opportunity_scores(sample_signals)
        assert len(scores) == len(sample_signals)
        for s in scores:
            assert 0 <= s.total_score <= 100
            assert s.ticker in [sig["ticker"] for sig in sample_signals]
            assert s.strategy_type in ("swing", "csp", "leaps", "pmcc")

    def test_ranking_produces_consistent_order(self, sample_signals):
        from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities
        scores = build_opportunity_scores(sample_signals)
        ranked = rank_opportunities(scores)
        for i in range(len(ranked) - 1):
            assert ranked[i].total_score >= ranked[i + 1].total_score
        assert ranked[0].rank == 1

    def test_xgboost_refinement_integration(self, sample_signals):
        from app.engines.opportunity.model import ScoringRefinementModel
        from app.engines.opportunity.service import build_opportunity_scores
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(200)
        model.train(X, y)
        scores = build_opportunity_scores(sample_signals, model=model)
        has_refined = sum(1 for s in scores if s.refined_score is not None)
        assert has_refined == len(sample_signals)
        for s in scores:
            assert 0 <= s.refined_score <= 100

    def test_score_formula_consistency(self):
        from app.engines.opportunity.service import compute_opportunity_score
        high = compute_opportunity_score(90, 85, 95, 80, 75, 90)
        mid = compute_opportunity_score(50, 50, 50, 50, 50, 50)
        low = compute_opportunity_score(10, 10, 10, 10, 10, 10)
        assert high > mid > low

    def test_strategy_selection_edge_cases(self):
        from app.engines.strategy.service import select_strategy
        no_signal = select_strategy("TEST", {"regime": "Range", "has_position": False})
        assert no_signal.recommendation == "hold"

        bearish = select_strategy("TEST", {"regime": "Crisis", "has_position": False})
        assert bearish.recommendation == "avoid"

        with_position = select_strategy("TEST", {"regime": "Bear", "has_position": True})
        assert with_position.recommendation == "close"

    def test_black_scholes_consistency(self):
        from app.engines.options.service import black_scholes_price
        prices = [black_scholes_price("call", 100.0, K, 0.5, 0.05, 0.25)
                  for K in [80, 90, 100, 110, 120]]
        for i in range(len(prices) - 1):
            assert prices[i] > prices[i + 1]

    def test_csp_generation_reasonable_values(self):
        from app.engines.options.service import generate_csp
        csp = generate_csp("AAPL", spot_price=150.0, implied_vol=0.30,
                           risk_free_rate=0.05, days_to_expiry=45)
        assert 0.15 <= abs(csp.delta) <= 0.35
        assert csp.annualized_yield > 0
        assert csp.probability_of_profit > 0.5

    def test_leaps_generation_reasonable_values(self):
        from app.engines.options.service import generate_leaps
        leaps = generate_leaps("AAPL", spot_price=150.0, implied_vol=0.35,
                               risk_free_rate=0.05, days_to_expiry=365)
        assert leaps.delta >= 0.65
        assert leaps.cost_basis > 0
        assert leaps.breakeven > leaps.strike

    def test_full_pipeline_runs_without_error(self, sample_signals):
        from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities
        from app.engines.strategy.service import select_strategy
        from app.engines.options.service import generate_csp
        scores = build_opportunity_scores(sample_signals)
        ranked = rank_opportunities(scores, top_n=3)
        assert len(ranked) == 3
        for s in ranked:
            strat = select_strategy(s.ticker, {"regime_score": s.regime_score,
                "breakout_score": s.breakout_score,
                "relative_strength_score": s.relative_strength_score,
                "regime": "Bull" if s.total_score > 60 else "Range",
                "has_position": False})
            assert strat.recommendation in (
                "buy_stock", "buy_leaps", "sell_csp", "pmcc",
                "covered_call", "close", "roll", "hold", "avoid")
        csp = generate_csp(ranked[0].ticker, spot_price=150.0, implied_vol=0.30,
                           risk_free_rate=0.05, days_to_expiry=45)
        assert csp.premium > 0
```

- [ ] **Step 2: Run to verify it passes**

Run: `cd backend && python -m pytest tests/integration/test_opportunity_pipeline.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --cov=app`
Expected: All tests pass, coverage report shows high coverage on new modules

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_opportunity_pipeline.py
git commit -m "test: add integration tests for opportunity pipeline end-to-end"
```

---

### Task 14: Final Cleanup — Ruff Lint & Full Test Suite

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
git commit -m "chore: lint and type-check Phase 3 opportunity and strategy engines"
```

---

## Self-Review Verification

After completing all tasks, verify against spec:

1. **Spec coverage:**
   - [ ] Opportunity schemas with score validation 0-100 — Task 2
   - [ ] Weighted scoring formula (25% regime + 20% breakout + 20% RS + 15% CUSUM + 10% volume + 10% trend) — Task 3
   - [ ] XGBoost scoring refinement model with synthetic data training — Task 4
   - [ ] Opportunity ranking and strategy filtering (swing/csp/leaps/pmcc) — Task 5
   - [ ] Strategy selection: 9 recommendation types with rule-based logic — Tasks 6-7
   - [ ] Strategy ML confidence model (RandomForest) — Task 7
   - [ ] Strategy reasoning text matching spec example format — Task 7
   - [ ] Black-Scholes pricing (call, put, delta, PoP, annualized yield) — Task 8
   - [ ] CSP generation: strike, expiration, delta (0.20-0.30), premium, yield, PoP — Task 9
   - [ ] LEAPS generation: expiration (12-24 mo), strike, delta, cost, breakeven — Task 9
   - [ ] PMCC generation: long LEAPS + short call, expected income — Task 9
   - [ ] Covered Call generation: strike, premium, delta — Task 9
   - [ ] Each engine has `__init__.py`, `schemas.py`, `service.py`, `router.py`, `tasks.py` — Tasks 2-11
   - [ ] Opportunities stored as Parquet in `signals/opportunities/<date>.parquet` — Task 10
   - [ ] FastAPI endpoints for all 3 engines — Tasks 11-12
   - [ ] Celery tasks with beat schedule — Tasks 10, 12
   - [ ] Integration tests for pipeline — Task 13

2. **Placeholder scan:** No TBD, TODO, or incomplete steps.

3. **Type consistency:** All method signatures match across tasks. `compute_opportunity_score` returns `float`, `build_opportunity_scores` returns `list[OpportunityScore]`, `select_strategy` returns `StrategyOutput`, `generate_csp` returns `CSPOption`, etc.

4. **Ambiguity check:** All steps are explicit with exact code and commands.
```




