import pytest
from pydantic import ValidationError


class TestPositionSchemas:
    def test_position_signal_valid(self):
        from app.engines.positions.schemas import PositionSignal
        sig = PositionSignal(ticker="AAPL", strategy_type="csp", action="close")
        assert sig.ticker == "AAPL"
        assert sig.confidence == 0.5
        assert sig.action == "close"

    def test_position_signal_invalid_action(self):
        from app.engines.positions.schemas import PositionSignal
        with pytest.raises(ValidationError):
            PositionSignal(ticker="AAPL", strategy_type="csp", action="invalid")

    def test_position_signal_invalid_confidence_negative(self):
        from app.engines.positions.schemas import PositionSignal
        with pytest.raises(ValidationError):
            PositionSignal(ticker="AAPL", strategy_type="csp", action="hold", confidence=-0.1)

    def test_position_signal_invalid_confidence_over_one(self):
        from app.engines.positions.schemas import PositionSignal
        with pytest.raises(ValidationError):
            PositionSignal(ticker="AAPL", strategy_type="csp", action="hold", confidence=1.5)

    def test_csp_evaluation_valid(self):
        from app.engines.positions.schemas import CspEvaluation
        ev = CspEvaluation(ticker="AAPL", strategy_type="csp", action="roll", current_dte=14, current_pl_pct=40.0)
        assert ev.current_dte == 14
        assert ev.roll_candidate == ""

    def test_leaps_evaluation_valid(self):
        from app.engines.positions.schemas import LeapsEvaluation
        ev = LeapsEvaluation(ticker="AAPL", strategy_type="leaps", action="exit", pl_pct=110.0)
        assert ev.pl_pct == 110.0
        assert ev.trend_status == "bullish"

    def test_swing_evaluation_trailing_stop(self):
        from app.engines.positions.schemas import SwingEvaluation
        ev = SwingEvaluation(ticker="AAPL", strategy_type="swing", action="trailing_stop", trailing_stop_triggered=True)
        assert ev.trailing_stop_triggered is True
        assert ev.action == "trailing_stop"

    def test_pmcc_evaluation_valid(self):
        from app.engines.positions.schemas import PmccEvaluation
        ev = PmccEvaluation(ticker="AAPL", strategy_type="pmcc", action="roll", short_call_dte=10, short_call_delta=0.25)
        assert ev.short_call_dte == 10
        assert ev.roll_candidate_strike == 0.0

    def test_management_result_valid(self):
        from app.engines.positions.schemas import ManagementResult
        result = ManagementResult(ticker="AAPL", strategy_type="csp", action_taken="close", success=True)
        assert result.success is True
        assert result.message == ""

    def test_watchdog_result_valid(self):
        from app.engines.positions.schemas import WatchdogResult
        from datetime import datetime
        result = WatchdogResult(timestamp=datetime.now(), positions_evaluated=3)
        assert result.positions_evaluated == 3
        assert result.actions_taken == []

    def test_watchdog_result_with_actions(self):
        from app.engines.positions.schemas import WatchdogResult, ManagementResult
        from datetime import datetime
        action = ManagementResult(ticker="AAPL", strategy_type="csp", action_taken="close", success=True)
        result = WatchdogResult(timestamp=datetime.now(), positions_evaluated=1, actions_taken=[action])
        assert len(result.actions_taken) == 1
        assert result.actions_taken[0].action_taken == "close"
