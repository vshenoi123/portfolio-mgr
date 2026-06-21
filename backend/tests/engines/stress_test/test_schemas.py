import pytest
from pydantic import ValidationError


class TestScenarioDefinition:
    def test_predefined_scenario(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        s = ScenarioDefinition(name="2008 Crash", equity_shock=-0.50)
        assert s.name == "2008 Crash"
        assert s.equity_shock == -0.50

    def test_custom_scenario_with_bond_shift(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        s = ScenarioDefinition(
            name="Custom", equity_shock=-0.20,
            bond_yield_shift=0.50, vol_shock=0.30, dollar_shock=0.05,
        )
        assert s.bond_yield_shift == 0.50

    def test_invalid_equity_shock(self):
        from app.engines.stress_test.schemas import ScenarioDefinition
        with pytest.raises(ValidationError):
            ScenarioDefinition(name="Bad", equity_shock=0.10)


class TestStressTestRequest:
    def test_valid_request(self):
        from app.engines.stress_test.schemas import StressTestRequest
        req = StressTestRequest(
            positions=[{"ticker": "AAPL", "beta": 1.2, "market_value": 10000}],
        )
        assert len(req.positions) == 1

    def test_request_with_custom_scenarios(self):
        from app.engines.stress_test.schemas import StressTestRequest
        req = StressTestRequest(
            positions=[{"ticker": "AAPL", "beta": 1.2, "market_value": 10000}],
            custom_scenarios=[{"name": "My Scenario", "equity_shock": -0.15}],
        )
        assert len(req.custom_scenarios) == 1


class TestStressTestResult:
    def test_valid_result(self):
        from app.engines.stress_test.schemas import StressTestResult
        r = StressTestResult(
            scenario_name="2008 Crash",
            total_portfolio_impact=-5000.0,
            total_portfolio_impact_pct=-0.15,
            position_impacts=[{"ticker": "AAPL", "impact": -3000.0, "impact_pct": -0.18}],
            top_vulnerable=["AAPL"],
        )
        assert r.total_portfolio_impact == -5000.0
        assert r.top_vulnerable == ["AAPL"]