import numpy as np
from app.engines.monte_carlo.schemas import (
    MonteCarloRequest,
    MonteCarloResult,
    PortfolioMonteCarloRequest,
)


class MonteCarloService:
    def historical_bootstrap(
        self, returns: np.ndarray, days: int, simulations: int
    ) -> np.ndarray:
        n = len(returns)
        indices = np.random.randint(0, n, size=(simulations, days))
        sampled = returns[indices]
        return sampled

    def parametric_simulation(
        self, mu: float, sigma: float, days: int, simulations: int
    ) -> np.ndarray:
        if sigma < 0:
            raise ValueError("sigma must be non-negative")
        daily_returns = np.random.normal(mu, sigma, size=(simulations, days))
        return daily_returns

    def compute_risk_metrics(self, price_paths: np.ndarray) -> dict:
        final_prices = price_paths[:, -1]
        returns = (price_paths[:, 1:] - price_paths[:, :-1]) / price_paths[:, :-1]

        var_95 = float(np.percentile(returns[:, -1], 5))
        var_99 = float(np.percentile(returns[:, -1], 1))

        tail_95 = returns[:, -1] <= var_95
        cvar_95 = float(returns[:, -1][tail_95].mean()) if tail_95.any() else var_95

        peak = np.maximum.accumulate(price_paths, axis=1)
        drawdowns = (price_paths - peak) / peak
        max_drawdowns = drawdowns.min(axis=1)

        return {
            "final_prices": final_prices,
            "returns": returns,
            "var_95": var_95,
            "var_99": var_99,
            "cvar_95": cvar_95,
            "max_drawdowns": max_drawdowns,
            "median_final": float(np.median(final_prices)),
            "mean_final": float(np.mean(final_prices)),
            "std_final": float(np.std(final_prices)),
        }

    def run_simulation(
        self, req: MonteCarloRequest, historical_returns: np.ndarray
    ) -> MonteCarloResult:
        if req.method == "historical":
            daily_returns = self.historical_bootstrap(
                historical_returns, req.days, req.simulations
            )
        else:
            mu = float(np.mean(historical_returns))
            sigma = float(np.std(historical_returns))
            daily_returns = self.parametric_simulation(
                mu, sigma, req.days, req.simulations
            )

        price_paths = 100.0 * np.exp(np.cumsum(daily_returns, axis=1))
        metrics = self.compute_risk_metrics(price_paths)

        return MonteCarloResult(
            ticker=req.ticker,
            simulations=req.simulations,
            days=req.days,
            method=req.method,
            final_prices=metrics["final_prices"],
            returns=metrics["returns"],
            var_95=metrics["var_95"],
            var_99=metrics["var_99"],
            cvar_95=metrics["cvar_95"],
            max_drawdowns=metrics["max_drawdowns"],
            median_final=metrics["median_final"],
            mean_final=metrics["mean_final"],
            std_final=metrics["std_final"],
        )

    def run_portfolio_simulation(
        self, req: PortfolioMonteCarloRequest, returns_dict: dict[str, np.ndarray]
    ) -> dict:
        portfolio_daily_returns = np.zeros((req.simulations, req.days))
        for pos in req.positions:
            ticker = pos["ticker"]
            weight = pos["weight"]
            ret = returns_dict[ticker]
            method = getattr(req, "method", "historical")
            if method == "historical":
                sim_returns = self.historical_bootstrap(ret, req.days, req.simulations)
            else:
                mu = float(np.mean(ret))
                sigma = float(np.std(ret))
                sim_returns = self.parametric_simulation(mu, sigma, req.days, req.simulations)
            portfolio_daily_returns += weight * sim_returns

        price_paths = 100.0 * np.exp(np.cumsum(portfolio_daily_returns, axis=1))
        metrics = self.compute_risk_metrics(price_paths)
        return metrics