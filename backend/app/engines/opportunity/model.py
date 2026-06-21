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
