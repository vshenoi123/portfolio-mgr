import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.asyncio


def _make_mock_state():
    from app.engines.portfolio.schemas import PortfolioState
    return PortfolioState(
        total_value=100000.0,
        cash=25000.0,
        equity_value=70000.0,
        options_value=5000.0,
        num_positions=2,
        num_options=1,
        positions=[
            {"ticker": "AAPL", "quantity": 100, "avg_price": 150,
             "current_price": 165, "market_value": 16500,
             "unrealized_pl": 1500, "unrealized_pl_pct": 10.0,
             "beta": 1.2, "sector": "TECHNOLOGY", "strategy_type": "equity",
             "weight_pct": 16.5},
            {"ticker": "NVDA", "quantity": 50, "avg_price": 80,
             "current_price": 95, "market_value": 4750,
             "unrealized_pl": 750, "unrealized_pl_pct": 18.75,
             "beta": 1.5, "sector": "TECHNOLOGY", "strategy_type": "swing",
             "weight_pct": 4.75},
        ],
        options_positions=[
            {"ticker": "AAPL", "option_type": "call", "strike": 170,
             "expiration": "2026-07-17", "quantity": 1, "market_value": 500,
             "delta": 0.4, "gamma": 0.02, "theta": -0.1, "vega": 0.05,
             "implied_vol": 0.35, "dte": 30, "strategy_type": "csp", "status": "open"},
        ],
        sector_exposures={"TECHNOLOGY": 21.25},
        portfolio_beta=1.3,
        portfolio_delta_e=5000.0,
    )


def _make_mock_assessment():
    from app.engines.risk.schemas import RiskAssessment
    return RiskAssessment(
        portfolio_health_score=85.0,
        max_drawdown=-5.0,
        current_exposure=75000.0,
        total_value=100000.0,
        concentration_pct=21.25,
        violations=[],
        is_safe=True,
        details={"exposure_pct": 75.0, "cash_pct": 25.0},
    )


@pytest_asyncio.fixture
async def client():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestPortfolioRouter:
    async def test_get_portfolio_summary(self, client):
        with patch("app.engines.portfolio.router.load_portfolio_state") as mock_load:
            mock_load.return_value = _make_mock_state()
            resp = await client.get("/api/v1/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] == 100000.0
        assert data["num_positions"] == 2
        assert len(data["top_holdings"]) == 2

    async def test_get_holdings(self, client):
        with patch("app.engines.portfolio.router.load_portfolio_state") as mock_load:
            mock_load.return_value = _make_mock_state()
            resp = await client.get("/api/v1/portfolio/holdings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["ticker"] == "AAPL"

    async def test_get_health(self, client):
        with patch("app.engines.portfolio.router.assess_portfolio_risk") as mock_assess:
            mock_assess.return_value = _make_mock_assessment()
            resp = await client.get("/api/v1/portfolio/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_health_score"] == 85.0

    async def test_get_exposure(self, client):
        mock_state = _make_mock_state()
        with (
            patch("app.engines.portfolio.router.load_portfolio_state", return_value=mock_state),
            patch("app.engines.portfolio.router.compute_concentration", return_value=21.25),
        ):
            resp = await client.get("/api/v1/portfolio/exposure")
        assert resp.status_code == 200
        data = resp.json()
        assert "sector_exposures" in data
        assert data["concentration_pct"] == 21.25

    async def test_get_portfolio_impact(self, client):
        from app.engines.portfolio.schemas import PortfolioImpactScore
        mock_impact = PortfolioImpactScore(ticker="AAPL", raw_opportunity_score=85.0, adjusted_score=80.5)
        with (
            patch("app.engines.portfolio.router.load_portfolio_state"),
            patch("app.engines.portfolio.router.calculate_portfolio_impact", return_value=mock_impact),
        ):
            resp = await client.get("/api/v1/portfolio/impact/AAPL?raw_score=85")
        assert resp.status_code == 200
        data = resp.json()
        assert data["adjusted_score"] == 80.5

    async def test_get_allocation(self, client):
        resp = await client.get("/api/v1/portfolio/allocation?regime=Bull")
        assert resp.status_code == 200
        data = resp.json()
        assert "allocations" in data
        assert len(data["allocations"]) == 5

    async def test_post_optimize(self, client):
        resp = await client.post("/api/v1/portfolio/optimize", json={
            "regime": "Bull", "cash_available": 50000,
            "total_portfolio_value": 100000,
            "opportunities": [{"ticker": "AAPL", "score": 80, "strategy": "swing"}],
        })
        assert resp.status_code == 200
        assert "allocations" in resp.json()

    async def test_opportunity_cost(self, client):
        resp = await client.post("/api/v1/portfolio/opportunity-cost", json={
            "candidates": [{"candidate": "AAPL", "score": 85, "risk_score": 5,
                            "estimated_return_pct": 15, "capital_required": 10000}],
            "cash_available": 50000,
        })
        assert resp.status_code == 200
        assert "candidates" in resp.json()

    async def test_replacements(self, client):
        resp = await client.post("/api/v1/portfolio/replacements", json={
            "current_positions": [{"ticker": "AAPL", "score": 50, "regime": "Range", "sector": "TECHNOLOGY"}],
            "opportunity_scores": [{"ticker": "NVDA", "score": 85, "sector": "TECHNOLOGY"}],
        })
        assert resp.status_code == 200
        assert "evaluations" in resp.json()

    async def test_validate_trade(self, client):
        mock_state = _make_mock_state()
        with patch("app.engines.portfolio.router.load_portfolio_state", return_value=mock_state):
            resp = await client.post("/api/v1/portfolio/validate-trade", json={
                "ticker": "AAPL", "requested_size": 10000, "sector": "TECHNOLOGY",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "is_allowed" in data
