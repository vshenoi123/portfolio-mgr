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
        model = ScoringRefinementModel()
        with pytest.raises(RuntimeError, match="trained"):
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
