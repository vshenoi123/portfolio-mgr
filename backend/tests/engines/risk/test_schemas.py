import pytest
from pydantic import ValidationError


class TestRiskSchemas:
    def test_risk_limit_valid(self):
        from app.engines.risk.schemas import RiskLimit
        rl = RiskLimit(name="max_position", value=15.0, unit="%", description="Max position size")
        assert rl.name == "max_position"

    def test_risk_assessment_valid(self):
        from app.engines.risk.schemas import RiskAssessment
        ra = RiskAssessment(portfolio_health_score=85.0, max_drawdown=10.0,
            current_exposure=65000.0, total_value=100000.0)
        assert ra.exposure_pct == 65.0

    def test_risk_assessment_safe_default(self):
        from app.engines.risk.schemas import RiskAssessment
        ra = RiskAssessment(portfolio_health_score=100.0)
        assert ra.is_safe is True

    def test_trade_risk_check_valid(self):
        from app.engines.risk.schemas import TradeRiskCheck
        trc = TradeRiskCheck(ticker="AAPL", requested_size=15000.0,
            details=[{"check": "size", "passed": True}])
        assert trc.checks_passed == 0  # not auto-calculated
