import pytest
from pydantic import ValidationError


class TestFeatureSchemas:
    def test_indicator_request_valid(self):
        from app.engines.features.schemas import IndicatorRequest
        req = IndicatorRequest(ticker="AAPL")
        assert req.ticker == "AAPL"
        assert req.days == 365

    def test_indicator_request_uppercases_ticker(self):
        from app.engines.features.schemas import IndicatorRequest
        req = IndicatorRequest(ticker="aapl")
        assert req.ticker == "AAPL"

    def test_indicator_request_rejects_empty_ticker(self):
        from app.engines.features.schemas import IndicatorRequest
        with pytest.raises(ValidationError):
            IndicatorRequest(ticker="")

    def test_indicator_response_valid(self):
        from app.engines.features.schemas import IndicatorResponse
        resp = IndicatorResponse(
            ticker="AAPL",
            indicators={"ema_20": 155.0, "rsi_14": 62.5},
            bars_analyzed=252,
        )
        assert resp.ticker == "AAPL"
        assert resp.indicators["ema_20"] == 155.0
        assert resp.bars_analyzed == 252

    def test_engine_health_response(self):
        from app.engines.features.schemas import EngineHealthResponse
        health = EngineHealthResponse(engine="features")
        assert health.engine == "features"
        assert health.status == "healthy"
