import pytest
from pydantic import ValidationError


class TestOptionsSchemas:
    def test_csp_option_valid(self):
        from app.engines.options.schemas import CSPOption
        opt = CSPOption(
            ticker="AAPL", strike=150.0, expiration="2025-01-17",
            premium=2.50, implied_volatility=0.25, delta=-0.30, gamma=0.02,
            theta=-0.05, vega=0.10, rho=-0.01, bid=2.45, ask=2.55,
            last_price=2.50, open_interest=1000, volume=500,
            underlying_price=155.0, days_to_expiration=30,
            annualized_yield=0.12, probability_of_profit=0.70,
        )
        assert opt.ticker == "AAPL"
        assert opt.strategy == "csp"
        assert opt.annualized_yield >= 0

    def test_csp_option_invalid_delta(self):
        from app.engines.options.schemas import CSPOption
        with pytest.raises(ValidationError):
            CSPOption(
                ticker="AAPL", strike=150.0, expiration="2025-01-17",
                premium=2.50, implied_volatility=0.25, delta=2.0, gamma=0.02,
                theta=-0.05, vega=0.10, rho=-0.01, bid=2.45, ask=2.55,
                last_price=2.50, open_interest=1000, volume=500,
                underlying_price=155.0, days_to_expiration=30,
                annualized_yield=0.12, probability_of_profit=0.70,
            )

    def test_csp_option_invalid_yield(self):
        from app.engines.options.schemas import CSPOption
        with pytest.raises(ValidationError):
            CSPOption(
                ticker="AAPL", strike=150.0, expiration="2025-01-17",
                premium=2.50, implied_volatility=0.25, delta=-0.30, gamma=0.02,
                theta=-0.05, vega=0.10, rho=-0.01, bid=2.45, ask=2.55,
                last_price=2.50, open_interest=1000, volume=500,
                underlying_price=155.0, days_to_expiration=30,
                annualized_yield=-0.01, probability_of_profit=0.70,
            )

    def test_leaps_option_valid(self):
        from app.engines.options.schemas import LEAPSOption
        opt = LEAPSOption(
            ticker="AAPL", strike=120.0, expiration="2026-01-16",
            premium=45.00, implied_volatility=0.30, delta=0.75, gamma=0.01,
            theta=-0.02, vega=0.15, rho=0.05, bid=44.50, ask=45.50,
            last_price=45.00, open_interest=5000, volume=200,
            underlying_price=155.0, days_to_expiration=365,
            leverage_factor=3.5, intrinsic_value=35.0, time_value=10.0,
        )
        assert opt.ticker == "AAPL"
        assert opt.strategy == "leaps"
        assert 0 <= opt.delta <= 1

    def test_leaps_option_invalid_delta(self):
        from app.engines.options.schemas import LEAPSOption
        with pytest.raises(ValidationError):
            LEAPSOption(
                ticker="AAPL", strike=120.0, expiration="2026-01-16",
                premium=45.00, implied_volatility=0.30, delta=-0.75, gamma=0.01,
                theta=-0.02, vega=0.15, rho=0.05, bid=44.50, ask=45.50,
                last_price=45.00, open_interest=5000, volume=200,
                underlying_price=155.0, days_to_expiration=365,
                leverage_factor=3.5, intrinsic_value=35.0, time_value=10.0,
            )

    def test_pmcc_option_valid(self):
        from app.engines.options.schemas import PMMCOption
        opt = PMMCOption(
            ticker="AAPL", long_strike=120.0, short_strike=160.0,
            long_expiration="2026-01-16", short_expiration="2025-01-17",
            long_premium=45.00, short_premium=3.50, net_debit=41.50,
            max_profit=18.50, max_loss=41.50, break_even=161.50,
            delta=0.45, underlying_price=155.0, days_to_long_expiration=365,
            days_to_short_expiration=30, probability_of_profit=0.55,
            annualized_yield=0.08,
        )
        assert opt.ticker == "AAPL"
        assert opt.strategy == "pmcc"
        assert opt.net_debit > 0

    def test_pmcc_option_invalid_net_debit(self):
        from app.engines.options.schemas import PMMCOption
        with pytest.raises(ValidationError):
            PMMCOption(
                ticker="AAPL", long_strike=120.0, short_strike=160.0,
                long_expiration="2026-01-16", short_expiration="2025-01-17",
                long_premium=45.00, short_premium=3.50, net_debit=0.0,
                max_profit=18.50, max_loss=41.50, break_even=161.50,
                delta=0.45, underlying_price=155.0, days_to_long_expiration=365,
                days_to_short_expiration=30, probability_of_profit=0.55,
                annualized_yield=0.08,
            )

    def test_covered_call_option_valid(self):
        from app.engines.options.schemas import CoveredCallOption
        opt = CoveredCallOption(
            ticker="AAPL", strike=165.0, expiration="2025-01-17",
            premium=2.50, implied_volatility=0.25, delta=0.35, gamma=0.02,
            theta=0.04, vega=0.10, rho=0.01, bid=2.45, ask=2.55,
            last_price=2.50, open_interest=2000, volume=800,
            underlying_price=155.0, days_to_expiration=30,
            annualized_yield=0.15, probability_of_profit=0.65,
        )
        assert opt.ticker == "AAPL"
        assert opt.strategy == "covered_call"
        assert 0 <= opt.delta <= 1

    def test_covered_call_option_invalid_yield(self):
        from app.engines.options.schemas import CoveredCallOption
        with pytest.raises(ValidationError):
            CoveredCallOption(
                ticker="AAPL", strike=165.0, expiration="2025-01-17",
                premium=2.50, implied_volatility=0.25, delta=0.35, gamma=0.02,
                theta=0.04, vega=0.10, rho=0.01, bid=2.45, ask=2.55,
                last_price=2.50, open_interest=2000, volume=800,
                underlying_price=155.0, days_to_expiration=30,
                annualized_yield=-0.01, probability_of_profit=0.65,
            )

    def test_options_generate_request_valid(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        req = OptionsGenerateRequest(
            ticker="AAPL", underlying_price=155.0, implied_volatility=0.25,
            days_to_expiration=30, strategy="csp",
        )
        assert req.ticker == "AAPL"
        assert req.target_delta == 0.30
        assert req.risk_free_rate == 0.05

    def test_options_generate_request_invalid_price(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        with pytest.raises(ValidationError):
            OptionsGenerateRequest(
                ticker="AAPL", underlying_price=0.0, implied_volatility=0.25,
                days_to_expiration=30, strategy="csp",
            )

    def test_options_generate_request_invalid_iv(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        with pytest.raises(ValidationError):
            OptionsGenerateRequest(
                ticker="AAPL", underlying_price=155.0, implied_volatility=1.5,
                days_to_expiration=30, strategy="csp",
            )

    def test_options_generate_request_invalid_delta(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        with pytest.raises(ValidationError):
            OptionsGenerateRequest(
                ticker="AAPL", underlying_price=155.0, implied_volatility=0.25,
                days_to_expiration=30, strategy="csp", target_delta=0.8,
            )

    def test_options_generate_request_invalid_dte(self):
        from app.engines.options.schemas import OptionsGenerateRequest
        with pytest.raises(ValidationError):
            OptionsGenerateRequest(
                ticker="AAPL", underlying_price=155.0, implied_volatility=0.25,
                days_to_expiration=0, strategy="csp",
            )
