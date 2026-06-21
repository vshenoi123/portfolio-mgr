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
    cumsum_pos = np.zeros(n)
    cumsum_neg = np.zeros(n)

    for i in range(1, n):
        cumsum_pos[i] = max(0, cumsum_pos[i - 1] + values[i] - drift)
        cumsum_neg[i] = max(0, cumsum_neg[i - 1] - values[i] - drift)

    max_pos = float(np.max(cumsum_pos))
    max_neg = float(np.max(cumsum_neg))
    max_dev = max(max_pos, max_neg)

    detected = max_pos > threshold or max_neg > threshold

    if detected:
        if max_pos > max_neg:
            direction = "positive"
            change_point = int(np.argmax(cumsum_pos))
            change_prob = min(1.0, max_pos / (threshold * 2))
        else:
            direction = "negative"
            change_point = int(np.argmax(cumsum_neg))
            change_prob = min(1.0, max_neg / (threshold * 2))
        days_since = n - change_point - 1
    else:
        direction = "none"
        change_point = None
        days_since = None
        change_prob = 0.0

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
