import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError


class TestDataRefreshRequest:
    def test_valid_refresh_request(self):
        from app.engines.data.schemas import DataRefreshRequest
        req = DataRefreshRequest(ticker="AAPL")
        assert req.ticker == "AAPL"
        assert req.days == 365

    def test_refresh_request_invalid_days(self):
        from app.engines.data.schemas import DataRefreshRequest
        with pytest.raises(ValidationError):
            DataRefreshRequest(ticker="AAPL", days=0)

    def test_refresh_request_uppercases_ticker(self):
        from app.engines.data.schemas import DataRefreshRequest
        req = DataRefreshRequest(ticker="aapl")
        assert req.ticker == "AAPL"


class TestDataRefreshResponse:
    def test_valid_response(self):
        from app.engines.data.schemas import DataRefreshResponse
        resp = DataRefreshResponse(
            ticker="AAPL",
            status="success",
            bars_fetched=252,
            message="Data refreshed for AAPL",
        )
        assert resp.status == "success"


class TestDataQuery:
    def test_valid_query(self):
        from app.engines.data.schemas import DataQuery
        start = datetime.now(timezone.utc) - timedelta(days=30)
        end = datetime.now(timezone.utc)
        q = DataQuery(ticker="AAPL", start_date=start, end_date=end)
        assert q.ticker == "AAPL"
