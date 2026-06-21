import pytest
import numpy as np


class TestHistoricalBootstrap:
    def test_simulate_returns_array_of_correct_shape(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.array([0.01, -0.02, 0.005, -0.01, 0.02, 0.015, -0.005, 0.008])
        paths = service.historical_bootstrap(returns, days=252, simulations=1000)
        assert paths.shape == (1000, 252)

    def test_historical_bootstrap_uses_empirical_returns(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.array([0.01])
        paths = service.historical_bootstrap(returns, days=10, simulations=5)
        assert np.allclose(paths, 0.01)

    def test_historical_bootstrap_with_zero_returns(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        returns = np.zeros(10)
        paths = service.historical_bootstrap(returns, days=100, simulations=100)
        assert np.allclose(paths, 0.0)


class TestParametricMethod:
    def test_simulate_returns_array_of_correct_shape(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        mu = 0.0005
        sigma = 0.015
        paths = service.parametric_simulation(mu, sigma, days=252, simulations=1000)
        assert paths.shape == (1000, 252)

    def test_parametric_uses_log_normal_property(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        paths = service.parametric_simulation(0.0, 0.0, days=10, simulations=10)
        assert np.allclose(paths, 0.0)

    def test_parametric_positive_std(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        with pytest.raises(ValueError):
            service.parametric_simulation(0.0, -0.01, days=10, simulations=10)


class TestVaRCVaR:
    def test_var_95_is_negative_or_zero(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(10000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert metrics["var_95"] <= 0
        assert metrics["var_99"] <= metrics["var_95"]

    def test_cvar_95_is_below_var_95(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(10000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert metrics["cvar_95"] <= metrics["var_95"]

    def test_max_drawdown_is_negative_or_zero(self):
        from app.engines.monte_carlo.service import MonteCarloService
        service = MonteCarloService()
        np.random.seed(42)
        paths = np.random.randn(1000, 252) * 0.02
        metrics = service.compute_risk_metrics(paths)
        assert np.all(metrics["max_drawdowns"] <= 0)
        assert len(metrics["max_drawdowns"]) == 1000


class TestFullSimulation:
    def test_run_simulation_returns_monte_carlo_result(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = MonteCarloRequest(ticker="SPY", days=252, simulations=1000, method="historical")
        result = service.run_simulation(req, historical_returns=np.random.randn(500) * 0.01)
        assert result.ticker == "SPY"
        assert result.var_95 <= 0
        assert result.var_99 <= result.var_95
        assert result.cvar_95 <= result.var_95
        assert len(result.final_prices) == 1000
        assert result.method == "historical"

    def test_run_simulation_parametric(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = MonteCarloRequest(ticker="SPY", days=252, simulations=1000, method="parametric")
        result = service.run_simulation(req, historical_returns=np.random.randn(500) * 0.01)
        assert result.ticker == "SPY"
        assert result.method == "parametric"
        assert result.var_95 <= 0

    def test_run_portfolio_simulation(self):
        from app.engines.monte_carlo.service import MonteCarloService
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        service = MonteCarloService()
        np.random.seed(42)
        req = PortfolioMonteCarloRequest(
            positions=[{"ticker": "AAPL", "weight": 0.6}, {"ticker": "MSFT", "weight": 0.4}],
            days=252,
            simulations=1000,
        )
        returns_dict = {"AAPL": np.random.randn(500) * 0.015, "MSFT": np.random.randn(500) * 0.012}
        result = service.run_portfolio_simulation(req, returns_dict)
        assert result["var_95"] <= 0
        assert result["var_99"] <= result["var_95"]