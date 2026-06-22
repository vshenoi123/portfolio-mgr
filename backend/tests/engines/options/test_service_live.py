class TestCSPGenerationLive:
    def test_generate_csp_live_uses_polygon_data(self):
        from app.engines.options.service import generate_csp_live
        live_data = {
            "strike": 195.0, "delta": -0.28, "iv": 0.32,
            "bid": 3.00, "ask": 3.20, "midpoint": 3.10,
            "open_interest": 500, "volume": 50,
            "gamma": 0.02, "theta": -0.05, "vega": 0.15,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_csp_live("AAPL", live_data)
        assert result is not None
        assert result.strike == 195.0
        assert result.bid == 3.00
        assert result.ask == 3.20
        assert result.open_interest == 500
        assert result.volume == 50
        assert result.live_data is True

    def test_generate_csp_live_returns_none_without_data(self):
        from app.engines.options.service import generate_csp_live
        result = generate_csp_live("AAPL", {})
        assert result is None

    def test_generate_csp_live_returns_none_when_none(self):
        from app.engines.options.service import generate_csp_live
        result = generate_csp_live("AAPL", None)
        assert result is None

    def test_generate_csp_live_uses_midpoint(self):
        from app.engines.options.service import generate_csp_live
        live_data = {
            "strike": 195.0, "delta": -0.28, "iv": 0.32,
            "bid": 3.00, "ask": 3.20, "midpoint": 3.10,
            "open_interest": 500, "volume": 50,
            "gamma": 0.02, "theta": -0.05, "vega": 0.15,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_csp_live("AAPL", live_data)
        assert result.premium == 3.10

    def test_generate_csp_live_no_midpoint_uses_avg(self):
        from app.engines.options.service import generate_csp_live
        live_data = {
            "strike": 195.0, "delta": -0.28, "iv": 0.32,
            "bid": 3.00, "ask": 3.20,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_csp_live("AAPL", live_data)
        assert result.premium == 3.10

    def test_generate_csp_live_stores_all_greeks(self):
        from app.engines.options.service import generate_csp_live
        live_data = {
            "strike": 195.0, "delta": -0.28, "iv": 0.32,
            "bid": 3.00, "ask": 3.20,
            "gamma": 0.02, "theta": -0.05, "vega": 0.15,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_csp_live("AAPL", live_data)
        assert result.delta == 0.28  # abs of -0.28
        assert result.gamma == 0.02
        assert result.theta == -0.05
        assert result.vega == 0.15

    def test_generate_csp_live_negative_delta_becomes_positive(self):
        from app.engines.options.service import generate_csp_live
        live_data = {
            "strike": 195.0, "delta": -0.35, "iv": 0.30,
            "bid": 2.50, "ask": 2.70,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_csp_live("AAPL", live_data)
        assert result.delta == 0.35


class TestLEAPSGenerationLive:
    def test_generate_leaps_live_uses_polygon_data(self):
        from app.engines.options.service import generate_leaps_live
        live_data = {
            "strike": 180.0, "delta": 0.72, "iv": 0.28,
            "bid": 25.00, "ask": 25.50, "midpoint": 25.25,
            "open_interest": 1200, "volume": 100,
            "gamma": 0.005, "theta": -0.02, "vega": 0.30,
            "underlying_price": 200.0, "dte": 180,
            "expiration_date": "2025-12-19",
        }
        result = generate_leaps_live("AAPL", live_data)
        assert result is not None
        assert result.strike == 180.0
        assert result.bid == 25.00
        assert result.ask == 25.50
        assert result.open_interest == 1200
        assert result.volume == 100
        assert result.live_data is True

    def test_generate_leaps_live_returns_none_without_data(self):
        from app.engines.options.service import generate_leaps_live
        result = generate_leaps_live("AAPL", {})
        assert result is None

    def test_generate_leaps_live_returns_none_when_none(self):
        from app.engines.options.service import generate_leaps_live
        result = generate_leaps_live("AAPL", None)
        assert result is None

    def test_generate_leaps_live_computes_intrinsic(self):
        from app.engines.options.service import generate_leaps_live
        live_data = {
            "strike": 180.0, "delta": 0.72, "iv": 0.28,
            "bid": 25.00, "ask": 25.50,
            "underlying_price": 200.0, "dte": 180,
            "expiration_date": "2025-12-19",
        }
        result = generate_leaps_live("AAPL", live_data)
        assert result.intrinsic_value == 20.0
        assert result.time_value == 5.25

    def test_generate_leaps_live_computes_leverage(self):
        from app.engines.options.service import generate_leaps_live
        live_data = {
            "strike": 180.0, "delta": 0.72, "iv": 0.28,
            "bid": 25.00, "ask": 25.50,
            "underlying_price": 200.0, "dte": 180,
            "expiration_date": "2025-12-19",
        }
        result = generate_leaps_live("AAPL", live_data)
        assert result.leverage_factor == round(200.0 / 25.25, 2)

    def test_generate_leaps_live_defaults(self):
        from app.engines.options.service import generate_leaps_live
        live_data = {
            "strike": 180.0, "delta": 0.72, "iv": 0.28,
            "bid": 25.00, "ask": 25.50,
            "underlying_price": 200.0, "dte": 180,
            "expiration_date": "2025-12-19",
        }
        result = generate_leaps_live("AAPL", live_data)
        assert result.days_to_expiration == 180
        assert result.strategy == "leaps"


class TestCoveredCallGenerationLive:
    def test_generate_covered_call_live_uses_polygon_data(self):
        from app.engines.options.service import generate_covered_call_live
        live_data = {
            "strike": 210.0, "delta": 0.25, "iv": 0.28,
            "bid": 1.50, "ask": 1.70, "midpoint": 1.60,
            "open_interest": 800, "volume": 75,
            "gamma": 0.01, "theta": -0.03, "vega": 0.10,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_covered_call_live("AAPL", live_data)
        assert result is not None
        assert result.strike == 210.0
        assert result.bid == 1.50
        assert result.ask == 1.70
        assert result.open_interest == 800
        assert result.volume == 75
        assert result.live_data is True

    def test_generate_covered_call_live_returns_none_without_data(self):
        from app.engines.options.service import generate_covered_call_live
        result = generate_covered_call_live("AAPL", {})
        assert result is None

    def test_generate_covered_call_live_returns_none_when_none(self):
        from app.engines.options.service import generate_covered_call_live
        result = generate_covered_call_live("AAPL", None)
        assert result is None

    def test_generate_covered_call_live_computes_yield(self):
        from app.engines.options.service import generate_covered_call_live
        live_data = {
            "strike": 210.0, "delta": 0.25, "iv": 0.28,
            "bid": 1.50, "ask": 1.70,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_covered_call_live("AAPL", live_data)
        assert result.annualized_yield > 0

    def test_generate_covered_call_live_stores_greeks(self):
        from app.engines.options.service import generate_covered_call_live
        live_data = {
            "strike": 210.0, "delta": 0.25, "iv": 0.28,
            "bid": 1.50, "ask": 1.70,
            "gamma": 0.01, "theta": -0.03, "vega": 0.10,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_covered_call_live("AAPL", live_data)
        assert result.gamma == 0.01
        assert result.theta == -0.03
        assert result.vega == 0.10

    def test_generate_covered_call_live_abs_delta(self):
        from app.engines.options.service import generate_covered_call_live
        live_data = {
            "strike": 210.0, "delta": -0.25, "iv": 0.28,
            "bid": 1.50, "ask": 1.70,
            "underlying_price": 200.0, "dte": 30,
            "expiration_date": "2025-07-18",
        }
        result = generate_covered_call_live("AAPL", live_data)
        assert result.delta == 0.25


class TestSchemaLiveDataField:
    def test_csp_option_has_live_data_field(self):
        from app.engines.options.schemas import CSPOption
        opt = CSPOption(
            ticker="AAPL", strike=195.0, expiration="2025-07-18",
            premium=3.0, implied_volatility=0.30, delta=0.30,
            gamma=0.0, theta=0.0, vega=0.0, rho=0.0,
            bid=3.0, ask=3.2, last_price=3.0,
            open_interest=0, volume=0,
            underlying_price=200.0, days_to_expiration=30,
            annualized_yield=0.1, probability_of_profit=0.6,
        )
        assert opt.live_data is False

    def test_csp_option_live_data_true(self):
        from app.engines.options.schemas import CSPOption
        opt = CSPOption(
            ticker="AAPL", strike=195.0, expiration="2025-07-18",
            premium=3.0, implied_volatility=0.30, delta=0.30,
            gamma=0.0, theta=0.0, vega=0.0, rho=0.0,
            bid=3.0, ask=3.2, last_price=3.0,
            open_interest=0, volume=0,
            underlying_price=200.0, days_to_expiration=30,
            annualized_yield=0.1, probability_of_profit=0.6,
            live_data=True,
        )
        assert opt.live_data is True

    def test_leaps_option_has_live_data_field(self):
        from app.engines.options.schemas import LEAPSOption
        opt = LEAPSOption(
            ticker="AAPL", strike=180.0, expiration="2025-12-19",
            premium=25.0, implied_volatility=0.28, delta=0.72,
            gamma=0.0, theta=0.0, vega=0.0, rho=0.0,
            bid=25.0, ask=25.5, last_price=25.0,
            open_interest=0, volume=0,
            underlying_price=200.0, days_to_expiration=180,
            leverage_factor=7.5, intrinsic_value=20.0, time_value=5.0,
        )
        assert opt.live_data is False

    def test_pmcc_option_has_live_data_field(self):
        from app.engines.options.schemas import PMMCOption
        opt = PMMCOption(
            ticker="AAPL", long_strike=180.0, short_strike=210.0,
            long_expiration="2025-12-19", short_expiration="2025-07-18",
            long_premium=25.0, short_premium=3.0,
            net_debit=22.0, max_profit=8.0, max_loss=22.0,
            break_even=202.0, delta=0.30, underlying_price=200.0,
            days_to_long_expiration=180, days_to_short_expiration=30,
            probability_of_profit=0.6, annualized_yield=0.1,
        )
        assert opt.live_data is False

    def test_covered_call_option_has_live_data_field(self):
        from app.engines.options.schemas import CoveredCallOption
        opt = CoveredCallOption(
            ticker="AAPL", strike=210.0, expiration="2025-07-18",
            premium=1.5, implied_volatility=0.28, delta=0.25,
            gamma=0.0, theta=0.0, vega=0.0, rho=0.0,
            bid=1.5, ask=1.7, last_price=1.5,
            open_interest=0, volume=0,
            underlying_price=200.0, days_to_expiration=30,
            annualized_yield=0.1, probability_of_profit=0.6,
        )
        assert opt.live_data is False
