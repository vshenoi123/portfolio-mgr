import numpy as np


class TestBlackScholes:
    def test_black_scholes_d1_basic(self):
        from app.engines.options.service import black_scholes_d1
        d1 = black_scholes_d1(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20)
        expected = (0.05 + 0.5 * 0.04) / 0.20
        assert np.isclose(d1, expected, atol=1e-6)

    def test_black_scholes_d2_from_d1(self):
        from app.engines.options.service import black_scholes_d1, black_scholes_d2
        d1 = black_scholes_d1(S=100.0, K=105.0, T=0.5, r=0.03, sigma=0.25)
        d2 = black_scholes_d2(S=100.0, K=105.0, T=0.5, r=0.03, sigma=0.25)
        expected = d1 - 0.25 * np.sqrt(0.5)
        assert np.isclose(d2, expected, atol=1e-6)

    def test_black_scholes_d1_zero_vol(self):
        from app.engines.options.service import black_scholes_d1
        d1 = black_scholes_d1(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.0)
        assert d1 == 0.0

    def test_black_scholes_call_price_atm(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, option_type="call")
        assert price > 0
        assert price < 100.0

    def test_black_scholes_put_price_atm(self):
        from app.engines.options.service import black_scholes_price
        price = black_scholes_price(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, option_type="put")
        assert price > 0
        assert price < 100.0

    def test_black_scholes_call_put_parity(self):
        from app.engines.options.service import black_scholes_price
        S, K, T, r, sigma = 105.0, 100.0, 0.5, 0.04, 0.25
        call = black_scholes_price(S, K, T, r, sigma, "call")
        put = black_scholes_price(S, K, T, r, sigma, "put")
        parity = call - put
        expected = S - K * np.exp(-r * T)
        assert np.isclose(parity, expected, atol=0.01)

    def test_black_scholes_deep_itm_call_delta(self):
        from app.engines.options.service import black_scholes_delta
        delta = black_scholes_delta(S=150.0, K=100.0, T=1.0, r=0.05, sigma=0.20, option_type="call")
        assert np.isclose(delta, 1.0, atol=0.05)

    def test_black_scholes_deep_otm_call_delta(self):
        from app.engines.options.service import black_scholes_delta
        delta = black_scholes_delta(S=100.0, K=150.0, T=1.0, r=0.05, sigma=0.20, option_type="call")
        assert np.isclose(delta, 0.0, atol=0.05)

    def test_black_scholes_put_delta_negative(self):
        from app.engines.options.service import black_scholes_delta
        delta = black_scholes_delta(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, option_type="put")
        assert delta < 0

    def test_probability_of_profit_call(self):
        from app.engines.options.service import probability_of_profit
        pop = probability_of_profit(S=100.0, K=105.0, T=0.5, r=0.05, sigma=0.25, option_type="call", premium=5.0)
        assert 0 <= pop <= 1

    def test_probability_of_profit_put(self):
        from app.engines.options.service import probability_of_profit
        pop = probability_of_profit(S=100.0, K=95.0, T=0.5, r=0.05, sigma=0.25, option_type="put", premium=5.0)
        assert 0 <= pop <= 1

    def test_annualized_yield_basic(self):
        from app.engines.options.service import annualized_yield
        y = annualized_yield(premium=2.0, strike=100.0, days_to_expiration=30)
        expected = (2.0 / 100.0) * (365.0 / 30.0)
        assert np.isclose(y, expected)


class TestCSPGeneration:
    def test_generate_csp_returns_csp_option(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result is not None
        assert result.strategy == "csp"
        assert result.ticker == "AAPL"
        assert result.strike < result.underlying_price

    def test_generate_csp_strike_below_price(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30, target_delta=0.30)
        assert result.strike < result.underlying_price

    def test_generate_csp_annualized_yield_positive(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result.annualized_yield > 0

    def test_generate_csp_pop_reasonable(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert 0 < result.probability_of_profit < 1

    def test_generate_csp_delta_negative(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result.delta < 0

    def test_generate_csp_short_dte(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=7)
        assert result.days_to_expiration == 7
        assert result.annualized_yield > 0

    def test_generate_csp_different_ticker(self):
        from app.engines.options.service import generate_csp
        result = generate_csp("SPY", underlying_price=500.0, implied_volatility=0.15, days_to_expiration=45)
        assert result.ticker == "SPY"
        assert result.strike < 500.0


class TestLEAPSGeneration:
    def test_generate_leaps_returns_leaps_option(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result is not None
        assert result.strategy == "leaps"
        assert result.ticker == "AAPL"

    def test_generate_leaps_delta_positive_high(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.delta > 0.5

    def test_generate_leaps_leverage_factor(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.leverage_factor > 1.0

    def test_generate_leaps_intrinsic_value(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.intrinsic_value >= 0
        assert result.time_value >= 0

    def test_generate_leaps_long_dte(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=730)
        assert result.days_to_expiration == 730

    def test_generate_leaps_strike_below_price(self):
        from app.engines.options.service import generate_leaps
        result = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365, target_delta=0.75)
        assert result.strike < result.underlying_price

    def test_generate_leaps_different_target_delta(self):
        from app.engines.options.service import generate_leaps
        result_70 = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365, target_delta=0.70)
        result_80 = generate_leaps("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365, target_delta=0.80)
        assert result_70.strike != result_80.strike or abs(result_70.delta - 0.70) < abs(result_80.delta - 0.70)


class TestPMCCGeneration:
    def test_generate_pmcc_returns_pmcc_option(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result is not None
        assert result.strategy == "pmcc"
        assert result.ticker == "AAPL"

    def test_generate_pmcc_long_strike_below_short(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.long_strike < result.short_strike

    def test_generate_pmcc_net_debit_positive(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.net_debit > 0

    def test_generate_pmcc_max_loss_equals_net_debit(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert abs(result.max_loss - result.net_debit) < 0.01

    def test_generate_pmcc_break_even_reasonable(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.break_even > result.long_strike

    def test_generate_pmcc_longer_dte(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=730)
        assert result.days_to_long_expiration == 730

    def test_generate_pmcc_short_expiration_is_30(self):
        from app.engines.options.service import generate_pmcc
        result = generate_pmcc("AAPL", underlying_price=155.0, implied_volatility=0.30, days_to_expiration=365)
        assert result.days_to_short_expiration == 30


class TestCoveredCallGeneration:
    def test_generate_covered_call_returns_covered_call_option(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result is not None
        assert result.strategy == "covered_call"
        assert result.ticker == "AAPL"

    def test_generate_covered_call_strike_above_price(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result.strike > result.underlying_price

    def test_generate_covered_call_delta_positive(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result.delta > 0

    def test_generate_covered_call_annualized_yield(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert result.annualized_yield > 0

    def test_generate_covered_call_pop_reasonable(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30)
        assert 0 < result.probability_of_profit < 1

    def test_generate_covered_call_short_dte(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=7)
        assert result.days_to_expiration == 7

    def test_generate_covered_call_otm_strike(self):
        from app.engines.options.service import generate_covered_call
        result = generate_covered_call("AAPL", underlying_price=155.0, implied_volatility=0.25, days_to_expiration=30, target_delta=0.25)
        assert result.strike > result.underlying_price
