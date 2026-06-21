import pytest
from pydantic import ValidationError


class TestRegimeSchemas:
    def test_regime_prediction_valid(self):
        from app.engines.regime.schemas import RegimePrediction
        pred = RegimePrediction(
            regime="Bull", probability=0.85, confidence=0.75,
            explanation="Strong uptrend with low volatility",
        )
        assert pred.regime == "Bull"
        assert 0 <= pred.probability <= 1
        assert 0 <= pred.confidence <= 1

    def test_regime_prediction_rejects_invalid_regime(self):
        from app.engines.regime.schemas import RegimePrediction
        with pytest.raises(ValidationError):
            RegimePrediction(regime="Invalid", probability=0.5, confidence=0.5, explanation="")

    def test_regime_prediction_rejects_probability_out_of_range(self):
        from app.engines.regime.schemas import RegimePrediction
        with pytest.raises(ValidationError):
            RegimePrediction(regime="Bull", probability=1.5, confidence=0.5, explanation="")

    def test_regime_request_valid(self):
        from app.engines.regime.schemas import RegimeRequest
        req = RegimeRequest(ticker="SPY")
        assert req.ticker == "SPY"
        assert req.n_states == 4

    def test_regime_request_rejects_invalid_n_states(self):
        from app.engines.regime.schemas import RegimeRequest
        with pytest.raises(ValidationError):
            RegimeRequest(ticker="SPY", n_states=1)
        with pytest.raises(ValidationError):
            RegimeRequest(ticker="SPY", n_states=7)

    def test_available_regimes_list(self):
        from app.engines.regime.schemas import AVAILABLE_REGIMES
        assert len(AVAILABLE_REGIMES) == 6
        assert "Bull" in AVAILABLE_REGIMES
        assert "Bear" in AVAILABLE_REGIMES
        assert "Crisis" in AVAILABLE_REGIMES
