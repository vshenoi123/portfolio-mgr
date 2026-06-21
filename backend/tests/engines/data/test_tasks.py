from unittest.mock import patch, MagicMock


class TestDataTasks:
    @patch("app.engines.data.tasks.PolygonDataService")
    def test_refresh_ticker_task(self, mock_service):
        from app.engines.data.tasks import refresh_ticker_data
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.fetch_ohlcv.return_value = [
            {"ticker": "AAPL", "close": 150.0}
        ]
        result = refresh_ticker_data("AAPL", days=365)
        assert result["ticker"] == "AAPL"
        assert result["status"] == "success"
        mock_instance.fetch_ohlcv.assert_called_once_with("AAPL", days=365)
        mock_instance.save_ohlcv.assert_called_once()

    @patch("app.engines.data.tasks.PolygonDataService")
    def test_refresh_ticker_error_handling(self, mock_service):
        from app.engines.data.tasks import refresh_ticker_data
        mock_service.return_value.fetch_ohlcv.side_effect = Exception("fail")
        result = refresh_ticker_data("INVALID")
        assert result["status"] == "error"
        assert "fail" in result["message"]
