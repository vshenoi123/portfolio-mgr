from app.engines.stress_test.schemas import (
    ScenarioDefinition,
    PREDEFINED_SCENARIOS,
    StressTestResult,
)


class StressTestService:
    def run_stress_test(self, positions: list[dict], scenarios: list[str] | None = None,
                        custom_scenarios: list[ScenarioDefinition] | None = None) -> list[StressTestResult]:
        scenario_list = scenarios if scenarios is not None else list(PREDEFINED_SCENARIOS.keys())
        all_scenarios = {**PREDEFINED_SCENARIOS}
        if custom_scenarios:
            for s in custom_scenarios:
                all_scenarios[s.name] = s
                if s.name not in scenario_list:
                    scenario_list.append(s.name)

        results = []
        for scenario_name in scenario_list:
            scenario = all_scenarios.get(scenario_name)
            if not scenario:
                continue

            total_impact = 0.0
            position_impacts = []

            for pos in positions:
                ticker = pos.get("ticker", "")
                beta = pos.get("beta", 1.0)
                market_value = pos.get("market_value", 0.0)
                sector = pos.get("sector", "Unknown")

                equity_impact = market_value * beta * scenario.equity_shock
                total_impact += equity_impact

                position_impacts.append({
                    "ticker": ticker,
                    "impact": round(equity_impact, 2),
                    "impact_pct": round((equity_impact / market_value * 100) if market_value else 0, 2),
                    "sector": sector,
                    "beta": beta,
                })

            position_impacts.sort(key=lambda x: x["impact"])
            top_vulnerable = [p["ticker"] for p in position_impacts[:3]]

            total_market_value = sum(p.get("market_value", 0) for p in positions)
            total_impact_pct = (total_impact / total_market_value * 100) if total_market_value else 0

            results.append(StressTestResult(
                scenario_name=scenario_name,
                total_portfolio_impact=round(total_impact, 2),
                total_portfolio_impact_pct=round(total_impact_pct, 2),
                position_impacts=position_impacts,
                top_vulnerable=top_vulnerable,
            ))

        return results

    def available_scenarios(self) -> dict[str, dict]:
        return {
            name: {
                "name": s.name,
                "equity_shock": s.equity_shock,
                "bond_yield_shift": s.bond_yield_shift,
                "vol_shock": s.vol_shock,
                "dollar_shock": s.dollar_shock,
                "credit_spread_widen": s.credit_spread_widen,
            }
            for name, s in PREDEFINED_SCENARIOS.items()
        }