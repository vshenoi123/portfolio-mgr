from unittest.mock import patch


class TestCspEvaluation:
    def test_csp_profit_close_min(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=30, current_pl_pct=55.0, current_delta=-0.20)
        assert result.action == "close"
        assert result.confidence == 0.7
        assert "profit target range" in result.rationale.lower()

    def test_csp_profit_close_max(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=30, current_pl_pct=80.0, current_delta=-0.15)
        assert result.action == "close"
        assert result.confidence == 0.9
        assert "profit target reached" in result.rationale.lower()

    def test_csp_roll_low_dte(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=10, current_pl_pct=30.0, current_delta=-0.20)
        assert result.action == "roll"
        assert result.confidence == 0.8
        assert result.roll_candidate != ""

    def test_csp_roll_high_delta(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=30, current_pl_pct=30.0, current_delta=-0.35)
        assert result.action == "roll"
        assert result.confidence == 0.6
        assert "delta" in result.rationale.lower()

    def test_csp_hold_healthy(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=30, current_pl_pct=20.0, current_delta=-0.20)
        assert result.action == "hold"
        assert result.confidence == 0.5

    def test_csp_uses_days_to_expiration_fallback(self):
        from app.engines.positions.service import evaluate_csp
        result = evaluate_csp("AAPL", current_dte=0, days_to_expiration=15)
        assert result.action == "roll"
        assert result.current_dte == 15


class TestLeapsEvaluation:
    def test_leaps_profit_target_exit(self):
        from app.engines.positions.service import evaluate_leaps
        result = evaluate_leaps("AAPL", entry_price=100, current_price=210, trend_status="bullish")
        assert result.action == "exit"
        assert result.confidence == 0.85
        assert result.pl_pct >= 100

    def test_leaps_trend_failure_exit(self):
        from app.engines.positions.service import evaluate_leaps
        result = evaluate_leaps("AAPL", entry_price=100, current_price=120, trend_status="bearish")
        assert result.action == "exit"
        assert result.confidence == 0.75

    def test_leaps_loss_exit(self):
        from app.engines.positions.service import evaluate_leaps
        result = evaluate_leaps("AAPL", entry_price=100, current_price=40, trend_status="bullish")
        assert result.action == "exit"
        assert result.confidence == 0.7

    def test_leaps_hold_healthy(self):
        from app.engines.positions.service import evaluate_leaps
        result = evaluate_leaps("AAPL", entry_price=100, current_price=130, trend_status="bullish", days_held=200)
        assert result.action == "hold"
        assert result.confidence == 0.5
        assert "LEAPS" in result.rationale


class TestSwingEvaluation:
    def test_swing_trailing_stop_triggered(self):
        from app.engines.positions.service import evaluate_swing
        result = evaluate_swing("AAPL", entry_price=100, current_price=91, highest_price=105, lowest_price=90)
        trailing_stop = 105 * (1 - 8 / 100)
        assert 91 <= trailing_stop
        assert result.action == "trailing_stop"
        assert result.trailing_stop_triggered is True

    def test_swing_breakdown_stop(self):
        from app.engines.positions.service import evaluate_swing
        result = evaluate_swing("AAPL", entry_price=100, current_price=86, highest_price=90, lowest_price=80)
        breakdown_stop = 100 * (1 - 12 / 100)
        assert 86 <= breakdown_stop
        assert result.action == "exit"
        assert result.confidence == 0.85

    def test_swing_profit_target(self):
        from app.engines.positions.service import evaluate_swing
        result = evaluate_swing("AAPL", entry_price=100, current_price=130, highest_price=130, lowest_price=95)
        profit_target = 100 * (1 + 25 / 100)
        assert 130 >= profit_target
        assert result.action == "close"
        assert result.confidence == 0.8

    def test_swing_hold_above_stops(self):
        from app.engines.positions.service import evaluate_swing
        result = evaluate_swing("AAPL", entry_price=100, current_price=105, highest_price=108, lowest_price=98)
        assert result.action == "hold"
        assert result.confidence == 0.5


class TestPmccEvaluation:
    def test_pmcc_roll_low_dte(self):
        from app.engines.positions.service import evaluate_pmcc
        result = evaluate_pmcc("AAPL", short_call_strike=160, short_call_dte=10, short_call_pl_pct=30.0, short_call_delta=0.20, underlying_price=155)
        assert result.action == "roll"
        assert result.confidence == 0.85
        assert result.roll_candidate_strike > 0

    def test_pmcc_roll_at_profit(self):
        from app.engines.positions.service import evaluate_pmcc
        result = evaluate_pmcc("AAPL", short_call_strike=160, short_call_dte=30, short_call_pl_pct=55.0, short_call_delta=0.20, underlying_price=155)
        assert result.action == "roll"
        assert result.confidence == 0.8

    def test_pmcc_adjust_high_delta(self):
        from app.engines.positions.service import evaluate_pmcc
        result = evaluate_pmcc("AAPL", short_call_strike=160, short_call_dte=30, short_call_pl_pct=20.0, short_call_delta=0.40, underlying_price=155)
        assert result.action == "adjust"
        assert result.confidence == 0.6

    def test_pmcc_hold_healthy(self):
        from app.engines.positions.service import evaluate_pmcc
        result = evaluate_pmcc("AAPL", short_call_strike=160, short_call_dte=30, short_call_pl_pct=20.0, short_call_delta=0.20, underlying_price=155)
        assert result.action == "hold"
        assert result.confidence == 0.5


class TestWatchdog:
    def test_watchdog_empty(self):
        from app.engines.positions.service import run_watchdog
        result = run_watchdog([])
        assert result.positions_evaluated == 0
        assert result.actions_taken == []

    def test_watchdog_with_csp_position(self):
        from app.engines.positions.service import run_watchdog
        positions = [{"ticker": "AAPL", "strategy_type": "csp"}]
        result = run_watchdog(positions)
        assert result.positions_evaluated == 1
        assert len(result.actions_taken) == 1
        assert result.actions_taken[0].ticker == "AAPL"

    def test_watchdog_all_strategies(self):
        from app.engines.positions.service import run_watchdog
        positions = [
            {"ticker": "AAPL", "strategy_type": "csp"},
            {"ticker": "MSFT", "strategy_type": "leaps"},
            {"ticker": "GOOG", "strategy_type": "swing"},
            {"ticker": "TSLA", "strategy_type": "pmcc"},
        ]
        result = run_watchdog(positions)
        assert result.positions_evaluated == 4
        assert len(result.actions_taken) == 4
        assert "Evaluated 4 positions" in result.summary
