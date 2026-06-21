import pytest
from pydantic import ValidationError


class TestReplacementSchemas:
    def test_position_evaluation_valid(self):
        from app.engines.replacement.schemas import PositionEvaluation
        ev = PositionEvaluation(ticker="AAPL", score=75.0, action="keep", rationale="Strong trend")
        assert ev.action == "keep"

    def test_position_evaluation_rejects_bad_action(self):
        from app.engines.replacement.schemas import PositionEvaluation
        with pytest.raises(ValidationError):
            PositionEvaluation(ticker="AAPL", score=75, action="invalid", rationale="")

    def test_trade_replacement_valid(self):
        from app.engines.replacement.schemas import TradeReplacement
        tr = TradeReplacement(current_ticker="AAPL", current_score=60.0,
            replacement_ticker="NVDA", replacement_score=85.0)
        assert tr.replacement_ticker == "NVDA"

    def test_replacement_response_valid(self):
        from app.engines.replacement.schemas import ReplacementResponse
        resp = ReplacementResponse(total_positions_evaluated=5)
        assert resp.total_positions_evaluated == 5
