import pytest
from pydantic import ValidationError


class TestMonteCarloRequest:
    def test_valid_request(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        req = MonteCarloRequest(
            ticker="SPY",
            days=252,
            simulations=10000,
            method="historical",
        )
        assert req.ticker == "SPY"
        assert req.simulations == 10000

    def test_default_values(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        req = MonteCarloRequest(ticker="AAPL")
        assert req.days == 252
        assert req.simulations == 10000
        assert req.method == "historical"

    def test_invalid_method(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", method="bayesian")

    def test_invalid_simulations_count(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", simulations=50)

    def test_negative_days(self):
        from app.engines.monte_carlo.schemas import MonteCarloRequest
        with pytest.raises(ValidationError):
            MonteCarloRequest(ticker="AAPL", days=-1)


class TestMonteCarloResult:
    def test_valid_result(self):
        from app.engines.monte_carlo.schemas import MonteCarloResult
        import numpy as np
        result = MonteCarloResult(
            ticker="SPY",
            simulations=1000,
            days=252,
            method="historical",
            final_prices=np.array([100.0, 110.0, 95.0]),
            returns=np.array([0.01, 0.10, -0.05]),
            var_95=-0.05,
            var_99=-0.08,
            cvar_95=-0.07,
            max_drawdowns=np.array([-0.10, -0.15, -0.08]),
            median_final=105.0,
            mean_final=106.0,
            std_final=15.0,
        )
        assert result.var_95 == -0.05
        assert result.ticker == "SPY"

    def test_var_99_more_negative_than_var_95(self):
        from app.engines.monte_carlo.schemas import MonteCarloResult
        import numpy as np
        with pytest.raises(ValidationError):
            MonteCarloResult(
                ticker="SPY",
                simulations=1000,
                days=252,
                method="historical",
                final_prices=np.array([100.0]),
                returns=np.array([0.01]),
                var_95=-0.05,
                var_99=-0.03,
                cvar_95=-0.07,
                max_drawdowns=np.array([-0.10]),
                median_final=105.0,
                mean_final=106.0,
                std_final=15.0,
            )


class TestPortfolioMonteCarloRequest:
    def test_valid_request(self):
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        req = PortfolioMonteCarloRequest(
            positions=[{"ticker": "AAPL", "weight": 0.6}, {"ticker": "MSFT", "weight": 0.4}],
            days=252,
            simulations=10000,
        )
        assert len(req.positions) == 2

    def test_weights_must_sum_to_one(self):
        from app.engines.monte_carlo.schemas import PortfolioMonteCarloRequest
        with pytest.raises(ValidationError):
            PortfolioMonteCarloRequest(
                positions=[{"ticker": "AAPL", "weight": 0.8}, {"ticker": "MSFT", "weight": 0.3}],
                days=252,
                simulations=10000,
            )