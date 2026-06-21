import pytest


class TestOpportunityCost:
    def test_basic_ranking_orders_by_score(self):
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "AAPL", "score": 85, "risk_score": 5, "estimated_return_pct": 15, "capital_required": 10000},
            {"candidate": "MSFT", "score": 75, "risk_score": 4, "estimated_return_pct": 12, "capital_required": 8000},
        ]
        result = rank_opportunity_cost(candidates, 50000)
        assert result["candidates"][0]["candidate"] == "AAPL"
        assert result["candidates"][1]["candidate"] == "MSFT"

    def test_empty_candidates_returns_empty(self):
        from app.engines.cost.service import rank_opportunity_cost
        result = rank_opportunity_cost([], 50000)
        assert result["candidates"] == []

    def test_risk_adjustment_works(self):
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "T1", "score": 90, "risk_score": 60, "estimated_return_pct": 10, "capital_required": 5000},
            {"candidate": "T2", "score": 70, "risk_score": 5, "estimated_return_pct": 15, "capital_required": 5000},
        ]
        result = rank_opportunity_cost(candidates, 50000)
        assert result["candidates"][0]["candidate"] == "T2"

    def test_capital_constraint_penalty(self):
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "AAPL", "score": 80, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 100000},
            {"candidate": "MSFT", "score": 60, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 5000},
        ]
        result = rank_opportunity_cost(candidates, 10000)
        assert result["candidates"][0]["candidate"] == "MSFT"

    def test_existing_holdings_considered(self):
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "AAPL", "score": 75, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 5000},
            {"candidate": "NVDA", "score": 80, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 5000},
        ]
        existing = [{"ticker": "AAPL", "weight_pct": 5}]
        result = rank_opportunity_cost(candidates, 50000, existing_positions=existing)
        assert result["candidates"][0]["candidate"] == "AAPL"

    def test_watchlist_considered(self):
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "AAPL", "score": 75, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 5000},
            {"candidate": "MSFT", "score": 75, "risk_score": 5, "estimated_return_pct": 10, "capital_required": 5000},
        ]
        result = rank_opportunity_cost(candidates, 50000, watchlist=["AAPL"])
        assert result["candidates"][0]["candidate"] == "AAPL"
