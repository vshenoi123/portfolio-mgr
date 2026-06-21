

class TestStressService:
    def test_run_single_position_stress(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.2, "market_value": 10000, "sector": "Technology"},
        ]
        results = service.run_stress_test(positions, scenarios=["2008 Crash"])
        assert len(results) == 1
        assert results[0].scenario_name == "2008 Crash"
        assert results[0].total_portfolio_impact < 0
        assert results[0].total_portfolio_impact == -6000.0

    def test_run_multi_position_stress(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.2, "market_value": 10000, "sector": "Technology"},
            {"ticker": "TLT", "beta": -0.3, "market_value": 5000, "sector": "Treasuries"},
        ]
        results = service.run_stress_test(positions, scenarios=["2008 Crash"])
        assert len(results) == 1
        assert results[0].total_portfolio_impact < 0

    def test_custom_scenario(self):
        from app.engines.stress_test.service import StressTestService
        from app.engines.stress_test.schemas import ScenarioDefinition
        service = StressTestService()
        positions = [{"ticker": "AAPL", "beta": 1.0, "market_value": 10000}]
        custom = [ScenarioDefinition(name="Custom", equity_shock=-0.20)]
        results = service.run_stress_test(positions, scenarios=[], custom_scenarios=custom)
        assert len(results) == 1
        assert results[0].scenario_name == "Custom"
        assert results[0].total_portfolio_impact == -2000.0

    def test_top_vulnerable_sorted_by_impact(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [
            {"ticker": "AAPL", "beta": 1.5, "market_value": 10000, "sector": "Technology"},
            {"ticker": "MSFT", "beta": 1.0, "market_value": 8000, "sector": "Technology"},
            {"ticker": "TLT", "beta": -0.3, "market_value": 5000, "sector": "Treasuries"},
        ]
        results = service.run_stress_test(positions, scenarios=["2008 Crash"])
        assert results[0].top_vulnerable[0] == "AAPL"

    def test_all_predefined_scenarios(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        positions = [{"ticker": "SPY", "beta": 1.0, "market_value": 10000}]
        results = service.run_stress_test(positions)
        assert len(results) == 5
        scenario_names = {r.scenario_name for r in results}
        assert "2008 Crash" in scenario_names
        assert "COVID Crash" in scenario_names
        assert "Dot-com Bust" in scenario_names
        assert "2022 Bear Market" in scenario_names
        assert "1987 Black Monday" in scenario_names

    def test_available_scenarios_method(self):
        from app.engines.stress_test.service import StressTestService
        service = StressTestService()
        scenarios = service.available_scenarios()
        assert len(scenarios) == 5
        assert all("equity_shock" in v for v in scenarios.values())