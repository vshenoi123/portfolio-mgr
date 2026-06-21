import pytest
from pydantic import ValidationError


class TestCUSUMSchemas:
    def test_change_point_result_valid(self):
        from app.engines.cusum.schemas import ChangePointResult
        cp = ChangePointResult(
            detected=True, direction="positive", change_probability=0.85,
            days_since_change=5, cumulative_deviation=2.3,
        )
        assert cp.detected is True
        assert cp.direction == "positive"
        assert 0 <= cp.change_probability <= 1

    def test_change_point_result_no_change(self):
        from app.engines.cusum.schemas import ChangePointResult
        cp = ChangePointResult(
            detected=False, direction="none", change_probability=0.05,
            days_since_change=None, cumulative_deviation=0.1,
        )
        assert cp.detected is False

    def test_change_point_result_rejects_invalid_direction(self):
        from app.engines.cusum.schemas import ChangePointResult
        with pytest.raises(ValidationError):
            ChangePointResult(
                detected=True, direction="sideways", change_probability=0.5,
                days_since_change=1, cumulative_deviation=1.0,
            )

    def test_cusum_response(self):
        from app.engines.cusum.schemas import CUSUMResponse
        resp = CUSUMResponse(ticker="AAPL")
        assert resp.ticker == "AAPL"
