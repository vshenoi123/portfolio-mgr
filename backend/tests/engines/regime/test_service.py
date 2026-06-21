import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def spy_returns():
    np.random.seed(42)
    n = 500
    returns = np.random.normal(0.0005, 0.01, n)
    return pd.Series(returns, name="close")


@pytest.fixture
def spy_returns_bull():
    np.random.seed(99)
    n = 500
    returns = np.random.normal(0.001, 0.005, n)
    return pd.Series(returns, name="close")


@pytest.fixture
def spy_returns_bear():
    np.random.seed(7)
    n = 500
    returns = np.random.normal(-0.003, 0.02, n)
    return pd.Series(returns, name="close")


class TestRegimeService:
    def test_fit_and_predict_hmm(self, spy_returns):
        from app.engines.regime.service import fit_hmm
        model, _ = fit_hmm(spy_returns, n_states=4)
        assert model is not None
        assert model.n_components == 4

    def test_predict_regime_returns_valid_output(self, spy_returns):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns, n_states=4)
        pred = predict_regime(model, spy_returns)
        assert pred.regime in ["Bull", "Bull High Vol", "Bear", "Bear High Vol", "Range", "Crisis"]
        assert 0 <= pred.probability <= 1
        assert 0 <= pred.confidence <= 1
        assert isinstance(pred.explanation, str)

    def test_predict_with_bull_returns(self, spy_returns_bull):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns_bull, n_states=4)
        pred = predict_regime(model, spy_returns_bull)
        assert "Bull" in pred.regime

    def test_predict_with_bear_returns(self, spy_returns_bear):
        from app.engines.regime.service import fit_hmm, predict_regime
        model, _ = fit_hmm(spy_returns_bear, n_states=4)
        pred = predict_regime(model, spy_returns_bear)
        assert "Bear" in pred.regime or "Bear High Vol" in pred.regime

    def test_full_regime_analysis(self, spy_returns):
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(spy_returns, n_states=4)
        assert "overall_regime" in result
        assert "state_probabilities" in result
        assert "trained_on_bars" in result

    def test_regime_analysis_insufficient_data(self):
        from app.engines.regime.service import full_regime_analysis
        short = pd.Series(np.random.randn(5))
        result = full_regime_analysis(short, n_states=4)
        assert result["overall_regime"].regime == "Range"
        assert result["trained_on_bars"] == 0

    def test_regime_analysis_with_state_assignment(self, spy_returns):
        from app.engines.regime.service import full_regime_analysis
        result = full_regime_analysis(spy_returns, n_states=5)
        assert len(result["state_probabilities"]) == 5

    def test_map_state_to_regime(self):
        from app.engines.regime.service import _map_state_to_regime
        regime1 = _map_state_to_regime(0.002, 0.005, 0.8)
        assert "Bull" in regime1
        regime2 = _map_state_to_regime(-0.001, 0.02, 0.6)
        assert "Bear High Vol" in regime2 or "Bear" in regime2 or "Crisis" in regime2
        regime3 = _map_state_to_regime(0.0001, 0.008, 0.3)
        assert regime3 == "Range"
