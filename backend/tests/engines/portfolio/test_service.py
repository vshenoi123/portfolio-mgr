import pytest
import numpy as np


class TestPortfolioStateLoading:
    def test_load_portfolio_state_empty(self, test_db_path):
        from app.database import get_connection, close_connection
        get_connection(test_db_path)
        close_connection(test_db_path)
        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(test_db_path)
        assert state.total_value == 0.0
        assert state.num_positions == 0

    def test_load_portfolio_state_with_positions(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        conn.execute("INSERT INTO portfolio_snapshots (date, total_value, cash) VALUES (CURRENT_DATE, 100000, 25000)")
        conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type) VALUES ('AAPL', 100, 150, 165, 'TECHNOLOGY', 'equity')")
        conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type) VALUES ('NVDA', 50, 80, 95, 'TECHNOLOGY', 'swing')")
        close_connection(test_db_path)

        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(test_db_path)
        assert state.num_positions == 2
        assert state.total_value == 100000.0
        assert state.cash == 25000.0

    def test_load_portfolio_state_sector_exposure_aggregation(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        conn.execute("INSERT INTO portfolio_snapshots (date, total_value, cash) VALUES (CURRENT_DATE, 50000, 10000)")
        conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type) VALUES ('AAPL', 200, 150, 165, 'TECHNOLOGY', 'equity')")
        close_connection(test_db_path)

        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(test_db_path)
        assert "TECHNOLOGY" in state.sector_exposures


class TestPortfolioImpact:
    def test_calculate_portfolio_impact_no_positions(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        result = calculate_portfolio_impact("AAPL", 85.0, [], {}, 100000, 0)
        assert result.adjusted_score == 85.0
        assert result.raw_opportunity_score == 85.0

    def test_calculate_portfolio_impact_sector_concentration(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        result = calculate_portfolio_impact("AAPL", 85.0, [], {"TECHNOLOGY": 30.0}, 100000, 0)
        assert result.adjusted_score < 85.0
        assert any(f["name"] == "sector_concentration" for f in result.impact_factors)

    def test_calculate_portfolio_impact_correlation_penalty(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        corr = {"AMD": {"NVDA": 0.85}}
        positions = [{"ticker": "NVDA", "weight_pct": 5.0}]
        result = calculate_portfolio_impact("AMD", 85.0, positions, {}, 100000, 30000,
                                            correlation_matrix=corr)
        assert result.adjusted_score < 85.0

    def test_calculate_portfolio_impact_cash_reserve_bonus(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        result = calculate_portfolio_impact("AAPL", 85.0, [], {}, 100000, 40000)
        assert result.adjusted_score >= 85.0

    def test_calculate_portfolio_impact_high_concentration_blocks(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        positions = [{"ticker": "AAPL", "market_value": 45000, "weight_pct": 45.0}]
        result = calculate_portfolio_impact("AAPL", 85.0, positions, {"TECHNOLOGY": 45.0}, 100000, 0)
        assert result.adjusted_score < 75

    def test_calculate_portfolio_impact_empty_state(self):
        from app.engines.portfolio.service import calculate_portfolio_impact
        result = calculate_portfolio_impact("AAPL", 0.0, [], {}, 0, 0)
        assert result.adjusted_score == 0.0


class TestPortfolioMetrics:
    def test_compute_portfolio_beta(self):
        from app.engines.portfolio.schemas import PortfolioPosition
        from app.engines.portfolio.service import compute_portfolio_beta
        pos1 = PortfolioPosition(ticker="AAPL", quantity=100, avg_price=150, current_price=165, beta=1.2)
        pos2 = PortfolioPosition(ticker="MSFT", quantity=50, avg_price=300, current_price=330, beta=0.9)
        beta = compute_portfolio_beta([pos1, pos2], 33000.0)
        assert 0.9 < beta < 1.2

    def test_compute_portfolio_beta_no_positions(self):
        from app.engines.portfolio.service import compute_portfolio_beta
        assert compute_portfolio_beta([], 0) == 0.0

    def test_compute_portfolio_delta(self):
        from app.engines.portfolio.schemas import PortfolioPosition
        from app.engines.portfolio.service import compute_portfolio_delta
        pos = PortfolioPosition(ticker="AAPL", quantity=100, avg_price=150, current_price=165, delta=1.0)
        delta = compute_portfolio_delta([pos], [])
        assert delta > 0

    def test_compute_portfolio_delta_no_options(self):
        from app.engines.portfolio.schemas import PortfolioPosition
        from app.engines.portfolio.service import compute_portfolio_delta
        pos = PortfolioPosition(ticker="AAPL", quantity=100, avg_price=150, current_price=165, delta=1.0)
        delta = compute_portfolio_delta([pos], [])
        assert delta == 16500.0

    def test_compute_concentration_top5(self):
        from app.engines.portfolio.schemas import PortfolioPosition
        from app.engines.portfolio.service import compute_concentration
        positions = [PortfolioPosition(ticker=f"T{i}", quantity=100, avg_price=100, current_price=100) for i in range(6)]
        conc = compute_concentration(positions, 60000)
        assert conc > 80

    def test_compute_concentration_empty(self):
        from app.engines.portfolio.service import compute_concentration
        assert compute_concentration([], 0) == 0.0


class TestCorrelationMatrix:
    def test_compute_correlation_matrix(self):
        from app.engines.portfolio.service import compute_correlation_matrix
        rng = np.random.default_rng(42)
        returns = {
            "AAPL": rng.normal(0, 0.02, 100),
            "MSFT": rng.normal(0, 0.02, 100) * 0.8 + rng.normal(0, 0.01, 100) * 0.2,
            "NVDA": rng.normal(0, 0.03, 100),
        }
        result = compute_correlation_matrix(returns)
        assert "AAPL" in result
        assert "MSFT" in result["AAPL"]

    def test_compute_correlation_matrix_single_ticker(self):
        from app.engines.portfolio.service import compute_correlation_matrix
        returns = {"AAPL": np.array([1, 2, 3, 4, 5], dtype=float)}
        result = compute_correlation_matrix(returns)
        assert result["AAPL"]["AAPL"] == 1.0

    def test_compute_correlation_matrix_no_data(self):
        from app.engines.portfolio.service import compute_correlation_matrix
        assert compute_correlation_matrix({}) == {}
