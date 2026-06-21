import pytest
from pydantic import ValidationError


class TestBreakoutSchemas:
    def test_breakout_signal_valid(self):
        from app.engines.breakout.schemas import BreakoutSignal
        sig = BreakoutSignal(
            ticker="AAPL", direction="bullish", strength=0.75,
            breakout_type="gaussian_channel", confirmed=True,
        )
        assert sig.ticker == "AAPL"
        assert sig.direction == "bullish"
        assert 0 <= sig.strength <= 1

    def test_breakout_signal_invalid_direction(self):
        from app.engines.breakout.schemas import BreakoutSignal
        with pytest.raises(ValidationError):
            BreakoutSignal(
                ticker="AAPL", direction="sideways", strength=0.5,
                breakout_type="gaussian_channel", confirmed=False,
            )

    def test_breakout_signal_invalid_strength(self):
        from app.engines.breakout.schemas import BreakoutSignal
        with pytest.raises(ValidationError):
            BreakoutSignal(
                ticker="AAPL", direction="bullish", strength=1.5,
                breakout_type="gaussian_channel", confirmed=True,
            )

    def test_breakout_response(self):
        from app.engines.breakout.schemas import BreakoutResponse
        resp = BreakoutResponse(ticker="AAPL")
        assert resp.ticker == "AAPL"
