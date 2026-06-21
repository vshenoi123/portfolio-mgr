import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import NotFittedError
from typing import cast
from app.engines.strategy.schemas import (
    RecommendationType,
    StrategyOutput,
)


def _score_buy_stock(regime: str, momentum: float, trend_strength: float, **kwargs) -> float:
    if regime in ("Bull", "Bull High Vol") and momentum > 0 and trend_strength > 0.3:
        return min(1.0, 0.5 + 0.3 * trend_strength + 0.2 * abs(momentum))
    return 0.1


def _score_buy_leaps(regime: str, iv_percentile: float, trend_strength: float, **kwargs) -> float:
    if regime in ("Bull", "Bull High Vol") and iv_percentile < 0.5 and trend_strength > 0.2:
        return min(1.0, 0.3 + 0.4 * (1 - iv_percentile) + 0.3 * trend_strength)
    return 0.05


def _score_sell_csp(regime: str, iv_percentile: float, put_skew: float, **kwargs) -> float:
    if regime in ("Bull", "Range") and iv_percentile > 0.5 and put_skew > 0:
        return min(1.0, 0.4 + 0.3 * iv_percentile + 0.3 * put_skew)
    return 0.1


def _score_pmcc(regime: str, iv_percentile: float, term_structure: float, **kwargs) -> float:
    if regime in ("Bull", "Bull High Vol", "Range") and iv_percentile > 0.4 and term_structure > 0:
        return min(1.0, 0.3 + 0.3 * iv_percentile + 0.4 * term_structure)
    return 0.05


def _score_covered_call(regime: str, momentum: float, iv_percentile: float, **kwargs) -> float:
    if regime in ("Bull", "Range") and abs(momentum) < 0.02 and iv_percentile > 0.3:
        return min(1.0, 0.4 + 0.3 * iv_percentile + 0.3 * (1 - abs(momentum) / 0.02))
    return 0.1


def _score_close(regime: str, momentum: float, drawdown: float, **kwargs) -> float:
    if regime == "Crisis" or (momentum < -0.05 and drawdown > 0.1):
        return min(1.0, 0.6 + 0.2 * abs(momentum) / 0.05 + 0.2 * drawdown / 0.1)
    return 0.05


def _score_roll(regime: str, days_to_expiry: int, momentum: float, **kwargs) -> float:
    if regime in ("Range", "Bull") and days_to_expiry < 14 and abs(momentum) < 0.03:
        return min(1.0, 0.5 + 0.3 * (1 - days_to_expiry / 14) + 0.2 * (1 - abs(momentum) / 0.03))
    return 0.05


def _score_hold(regime: str, momentum: float, trend_strength: float, **kwargs) -> float:
    if regime in ("Bull", "Range") and abs(momentum) < 0.01 and trend_strength > 0.2:
        return min(1.0, 0.5 + 0.5 * trend_strength)
    if regime == "Bear" and abs(momentum) < 0.02:
        return 0.3
    return 0.2


def _score_avoid(regime: str, momentum: float, drawdown: float, **kwargs) -> float:
    if regime == "Crisis" or (momentum < -0.03 and drawdown > 0.05):
        return min(1.0, 0.5 + 0.3 * abs(momentum) / 0.03 + 0.2 * drawdown / 0.05)
    return 0.1


_SCORE_FUNCTIONS = {
    "buy_stock": _score_buy_stock,
    "buy_leaps": _score_buy_leaps,
    "sell_csp": _score_sell_csp,
    "pmcc": _score_pmcc,
    "covered_call": _score_covered_call,
    "close": _score_close,
    "roll": _score_roll,
    "hold": _score_hold,
    "avoid": _score_avoid,
}


def rule_based_scores(context: dict) -> dict[str, float]:
    scores = {}
    for rec, scorer in _SCORE_FUNCTIONS.items():
        scores[rec] = scorer(
            regime=context.get("regime", "Range"),
            momentum=context.get("momentum", 0.0),
            trend_strength=context.get("trend_strength", 0.0),
            iv_percentile=context.get("iv_percentile", 0.5),
            put_skew=context.get("put_skew", 0.0),
            term_structure=context.get("term_structure", 0.0),
            drawdown=context.get("drawdown", 0.0),
            days_to_expiry=context.get("days_to_expiry", 30),
        )
    return scores


def _build_feature_vector(context: dict) -> np.ndarray:
    regime_map = {"Bull": 0, "Bull High Vol": 1, "Range": 2, "Bear": 3, "Bear High Vol": 4, "Crisis": 5}
    regime_idx = regime_map.get(context.get("regime", "Range"), 2)
    return np.array([
        regime_idx,
        context.get("momentum", 0.0),
        context.get("trend_strength", 0.0),
        context.get("iv_percentile", 0.5),
        context.get("put_skew", 0.0),
        context.get("term_structure", 0.0),
        context.get("drawdown", 0.0),
        context.get("days_to_expiry", 30) / 365.0,
        context.get("rsi", 50.0) / 100.0,
    ])


class StrategyConfidenceModel:
    def __init__(self):
        self._model = RandomForestRegressor(n_estimators=50, max_depth=3, random_state=42)
        self._fitted = False

    def fit(self, contexts: list[dict], targets: list[float]) -> None:
        X = np.array([_build_feature_vector(c) for c in contexts])
        y = np.array(targets)
        self._model.fit(X, y)
        self._fitted = True

    def predict(self, context: dict) -> tuple[float, float]:
        X = _build_feature_vector(context).reshape(1, -1)
        try:
            pred = self._model.predict(X)[0]
            confidence = float(np.clip(pred, 0, 1))
            uncertainty = 0.0
            if self._fitted:
                trees = np.array([tree.predict(X)[0] for tree in self._model.estimators_])
                uncertainty = float(np.std(trees))
            return confidence, uncertainty
        except NotFittedError:
            return 0.5, 0.0

    @property
    def fitted(self) -> bool:
        return self._fitted


def select_strategy(context: dict, ml_model: StrategyConfidenceModel | None = None) -> StrategyOutput:
    rule_scores = rule_based_scores(context)

    best_rule_rec = max(rule_scores, key=lambda k: rule_scores[k])
    best_rule_score = rule_scores[best_rule_rec]

    if ml_model is not None and ml_model.fitted:
        ml_conf, ml_uncertainty = ml_model.predict(context)
        blended = 0.4 * best_rule_score + 0.6 * ml_conf
        confidence = float(np.clip(blended, 0, 1))
    else:
        ml_conf = best_rule_score
        confidence = best_rule_score

    recommendation = cast(RecommendationType, best_rule_rec)

    reasoning_map = {
        "buy_stock": "Bullish momentum and trend support long equity exposure",
        "buy_leaps": "Favorable IV environment for long-dated LEAPS",
        "sell_csp": "Elevated IV supports cash-secured put premium capture",
        "pmcc": "Favorable term structure for poor man's covered call",
        "covered_call": "Range-bound conditions support covered call income",
        "close": "Adverse conditions warrant position closure",
        "roll": "Near expiry with low momentum supports rolling positions",
        "hold": "No strong signal, maintaining current positions",
        "avoid": "Unfavorable risk/reward, avoiding new positions",
    }

    risk_map = {
        "buy_stock": "Market risk, no defined hedge",
        "buy_leaps": "Time decay risk, leverage risk",
        "sell_csp": "Assignment risk below strike",
        "pmcc": "Upside capped, time decay on short call",
        "covered_call": "Upside capped below short strike",
        "close": "Realizes P&L, eliminates exposure",
        "roll": "Extends duration, may increase margin",
        "hold": "Maintains current risk profile",
        "avoid": "No new market exposure",
    }

    return StrategyOutput(
        ticker=context.get("ticker", "UNKNOWN"),
        recommendation=recommendation,
        confidence=round(confidence, 4),
        reasoning=reasoning_map.get(recommendation, "Strategy selected by rules engine"),
        risk_assessment=risk_map.get(recommendation, "Standard market risks apply"),
        details={
            "rule_scores": {k: round(v, 4) for k, v in sorted(rule_scores.items(), key=lambda x: -x[1])},
            "ml_confidence": round(ml_conf, 4) if ml_model is not None else None,
            "regime": context.get("regime"),
            "momentum": context.get("momentum"),
        },
    )
