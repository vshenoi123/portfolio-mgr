import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


pytestmark = pytest.mark.asyncio


class TestPhase3Endpoints:
    async def test_opportunities_endpoint_exists(self, client):
        resp = await client.get("/api/v1/opportunities")
        assert resp.status_code == 200

    async def test_strategy_endpoint_exists(self, client):
        resp = await client.get("/api/v1/opportunities/strategy/AAPL")
        assert resp.status_code == 200

    async def test_options_generate_endpoint_exists(self, client):
        resp = await client.post("/api/v1/opportunities/options/generate",
            json={"ticker": "AAPL", "underlying_price": 150.0,
                  "implied_volatility": 0.30, "risk_free_rate": 0.05,
                  "strategy": "csp", "days_to_expiration": 30})
        assert resp.status_code == 200

    @patch("app.engines.opportunity.router.compute_opp_task")
    async def test_opportunities_compute_endpoint_exists(self, mock_task, client):
        mock_task.delay.return_value = MagicMock(id="task-301")
        resp = await client.post("/api/v1/opportunities/compute")
        assert resp.status_code == 202


class TestPhase4Endpoints:
    async def test_portfolio_summary_endpoint(self, client):
        with patch("app.engines.portfolio.router.load_portfolio_state") as m:
            from app.engines.portfolio.schemas import PortfolioState
            m.return_value = PortfolioState(total_value=100000, cash=25000,
                equity_value=70000, options_value=5000, num_positions=2, num_options=1,
                portfolio_beta=1.1, portfolio_delta_e=200)
            resp = await client.get("/api/v1/portfolio")
        assert resp.status_code == 200

    async def test_portfolio_health_endpoint(self, client):
        with patch("app.engines.portfolio.router.assess_portfolio_risk") as m:
            from app.engines.risk.schemas import RiskAssessment
            m.return_value = RiskAssessment(portfolio_health_score=85.0, is_safe=True)
            resp = await client.get("/api/v1/portfolio/health")
        assert resp.status_code == 200

    async def test_portfolio_holdings_endpoint(self, client):
        with patch("app.engines.portfolio.router.load_portfolio_state") as m:
            from app.engines.portfolio.schemas import PortfolioState
            m.return_value = PortfolioState(total_value=100000, cash=25000,
                equity_value=70000, options_value=5000, num_positions=2, num_options=1)
            resp = await client.get("/api/v1/portfolio/holdings")
        assert resp.status_code == 200

    async def test_portfolio_exposure_endpoint(self, client):
        with (
            patch("app.engines.portfolio.router.load_portfolio_state") as m1,
            patch("app.engines.portfolio.router.compute_concentration", return_value=21.25),
        ):
            from app.engines.portfolio.schemas import PortfolioState
            m1.return_value = PortfolioState(total_value=100000, cash=25000,
                equity_value=70000, options_value=5000, num_positions=2, num_options=1,
                sector_exposures={"TECHNOLOGY": 21.25})
            resp = await client.get("/api/v1/portfolio/exposure")
        assert resp.status_code == 200

    async def test_portfolio_impact_endpoint(self, client):
        from app.engines.portfolio.schemas import PortfolioImpactScore
        with (
            patch("app.engines.portfolio.router.load_portfolio_state") as m1,
            patch("app.engines.portfolio.router.calculate_portfolio_impact") as m2,
        ):
            from app.engines.portfolio.schemas import PortfolioState
            m1.return_value = PortfolioState(total_value=100000, cash=25000)
            m2.return_value = PortfolioImpactScore(ticker="AAPL", raw_opportunity_score=85.0, adjusted_score=80.5)
            resp = await client.get("/api/v1/portfolio/impact/AAPL?raw_score=85")
        assert resp.status_code == 200
        assert resp.json()["adjusted_score"] == 80.5

    async def test_portfolio_allocation_endpoint(self, client):
        resp = await client.get("/api/v1/portfolio/allocation?regime=Bull")
        assert resp.status_code == 200

    async def test_portfolio_validate_trade_endpoint(self, client):
        with patch("app.engines.portfolio.router.load_portfolio_state") as m:
            from app.engines.portfolio.schemas import PortfolioState
            m.return_value = PortfolioState(total_value=100000, cash=25000,
                equity_value=70000, options_value=5000, num_positions=2, num_options=1,
                portfolio_beta=1.1, portfolio_delta_e=200)
            resp = await client.post("/api/v1/portfolio/validate-trade",
                json={"ticker": "AAPL", "requested_size": 10000, "sector": "TECHNOLOGY"})
        assert resp.status_code == 200
        assert "is_allowed" in resp.json()
