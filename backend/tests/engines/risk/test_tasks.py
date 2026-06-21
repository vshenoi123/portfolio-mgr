import pytest
from unittest.mock import patch, MagicMock


class TestRiskTasks:
    @patch("app.engines.risk.service.assess_portfolio_risk")
    def test_assess_risk_safe(self, mock_assess):
        from app.engines.risk.tasks import assess_risk_and_alert
        from app.engines.risk.schemas import RiskAssessment
        mock_assess.return_value = RiskAssessment(portfolio_health_score=85.0, violations=[], is_safe=True)
        result = assess_risk_and_alert()
        assert result["status"] == "success"
        assert result["is_safe"] is True
        assert len(result["alerts"]) == 0

    @patch("app.engines.risk.service.assess_portfolio_risk")
    def test_assess_risk_violations(self, mock_assess):
        from app.engines.risk.tasks import assess_risk_and_alert
        from app.engines.risk.schemas import RiskAssessment
        mock_assess.return_value = RiskAssessment(portfolio_health_score=45.0,
            violations=[{"type": "concentration", "value": 55, "limit": 40}], is_safe=False)
        result = assess_risk_and_alert()
        assert result["status"] == "success"
        assert result["is_safe"] is False
        assert len(result["alerts"]) > 0
