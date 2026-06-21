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
