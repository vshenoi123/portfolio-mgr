from unittest.mock import patch


class TestOptionsTasks:
    def test_generate_options_csp_task(self):
        from app.engines.options.tasks import generate_options
        from app.engines.options.schemas import CSPOption
        with patch("app.engines.options.service.generate_csp") as mock_gen:
            mock_gen.return_value = CSPOption(
                ticker="AAPL", strike=145.0, expiration="2026-08-21",
                delta=0.25, premium=2.50, annualized_yield=8.5,
                probability_of_profit=0.72, implied_volatility=0.30,
                underlying_price=150.0, days_to_expiration=45,
                gamma=0.05, theta=-0.02, vega=0.30, rho=0.01,
                bid=2.40, ask=2.60, last_price=2.50,
                open_interest=0, volume=0,
            )
            result = generate_options("AAPL", strategy="csp", underlying_price=150.0)
            assert result["ticker"] == "AAPL"
            assert result["status"] == "success"

    def test_generate_options_leaps_task(self):
        from app.engines.options.tasks import generate_options
        from app.engines.options.schemas import LEAPSOption
        with patch("app.engines.options.service.generate_leaps") as mock_gen:
            mock_gen.return_value = LEAPSOption(
                ticker="AAPL", strike=120.0, expiration="2027-06-18",
                delta=0.78, premium=38.50, implied_volatility=0.35,
                underlying_price=150.0, days_to_expiration=365,
                leverage_factor=3.90, intrinsic_value=30.0, time_value=8.50,
                gamma=0.01, theta=-0.01, vega=0.40, rho=0.02,
                bid=36.50, ask=40.50, last_price=38.50,
                open_interest=0, volume=0,
            )
            result = generate_options("AAPL", strategy="leaps", underlying_price=150.0)
            assert result["status"] == "success"

    def test_generate_options_unknown_strategy(self):
        from app.engines.options.tasks import generate_options
        result = generate_options("AAPL", strategy="unknown", underlying_price=100.0)
        assert result["status"] == "error"

    def test_generate_options_error(self):
        from app.engines.options.tasks import generate_options
        with patch("app.engines.options.service.generate_csp") as mock_gen:
            mock_gen.side_effect = Exception("fail")
            result = generate_options("AAPL", strategy="csp", underlying_price=100.0)
            assert result["status"] == "error"
