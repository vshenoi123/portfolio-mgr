from unittest.mock import patch


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

    @patch("app.engines.features.tasks.PolygonDataService")
    def test_compute_features_fetch_error(self, mock_ds):
        from app.engines.features.tasks import compute_features
        mock_ds.return_value.load_ohlcv.side_effect = Exception("DB error")
        result = compute_features("AAPL")
        assert result["status"] == "error"

    @patch("app.engines.features.tasks.get_universe")
    @patch("app.engines.features.tasks.compute_features")
    def test_compute_all_features_task(self, mock_compute, mock_get_universe):
        from app.engines.features.tasks import compute_all_features
        mock_get_universe.return_value = ["AAPL", "MSFT", "GOOGL"]
        mock_compute.return_value = {"ticker": "TEST", "status": "success", "indicators_count": 1}
        results = compute_all_features()
        assert len(results) == 3
