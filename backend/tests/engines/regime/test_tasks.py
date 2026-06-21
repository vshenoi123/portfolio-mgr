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
