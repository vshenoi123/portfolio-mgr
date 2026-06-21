"""Integration tests for Phase 4 portfolio pipeline end-to-end."""

import pytest
import duckdb
import numpy as np


@pytest.fixture
def portfolio_db(test_db_path):
    """Set up a populated portfolio database for integration tests."""
    from app.database import get_connection, close_connection
    conn = get_connection(test_db_path)
    conn.execute("INSERT INTO portfolio_snapshots (date, total_value, cash) VALUES (CURRENT_DATE, 200000, 50000)")
    conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type, beta, delta) VALUES ('AAPL', 200, 150, 165, 'TECHNOLOGY', 'equity', 1.2, 1.0)")
    conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type, beta, delta) VALUES ('MSFT', 100, 300, 320, 'TECHNOLOGY', 'equity', 0.9, 1.0)")
    conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type, beta, delta) VALUES ('NVDA', 50, 80, 95, 'TECHNOLOGY', 'swing', 1.5, 1.0)")
    conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type, beta, delta) VALUES ('XOM', 100, 120, 125, 'ENERGY', 'equity', 0.8, 1.0)")
    conn.execute("INSERT INTO options_positions (ticker, option_type, strike, expiration, quantity, market_value, delta, gamma, theta, vega, implied_vol, dte, strategy_type, status) VALUES ('AAPL', 'put', 145, '2026-07-17', 1, 250, 0.25, 0.02, -0.05, 0.03, 0.30, 30, 'csp', 'open')")
    results = {}
    rows = conn.execute("SELECT ticker, current_price FROM positions").fetchall()
    for r in rows:
        results[str(r[0])] = float(r[1])
    close_connection(test_db_path)
    return test_db_path, results


class TestPortfolioStateIntegration:
    def test_load_portfolio_state_full(self, portfolio_db):
        from app.engines.portfolio.service import load_portfolio_state
        db_path, _ = portfolio_db
        state = load_portfolio_state(db_path)
        assert state.num_positions == 4
        assert state.num_options == 1
        assert state.equity_value > 0
        assert state.options_value == 250.0
        assert "TECHNOLOGY" in state.sector_exposures
        assert "ENERGY" in state.sector_exposures

    def test_portfolio_impact_with_real_state(self, portfolio_db):
        from app.engines.portfolio.service import load_portfolio_state, calculate_portfolio_impact
        db_path, _ = portfolio_db
        state = load_portfolio_state(db_path)
        result = calculate_portfolio_impact(
            ticker="AAPL", raw_score=85.0,
            positions=state.positions, sector_exposures=state.sector_exposures,
            total_value=state.total_value, cash=state.cash,
        )
        assert result.raw_opportunity_score == 85.0
        assert result.adjusted_score <= 85.0
        assert len(result.impact_factors) > 0


class TestKellyAllocationIntegration:
    def test_kelly_sizing_saves_to_db(self, portfolio_db):
        from app.engines.allocation.service import calculate_position_size, save_allocation
        from app.config import settings
        db_path, _ = portfolio_db
        result = calculate_position_size(
            total_portfolio_value=200000, cash_available=50000,
            kelly_fraction_value=settings.kelly_fraction,
            opportunity_score=80.0, strategy="swing", regime="Bull",
        )
        result.ticker = "AAPL"
        save_allocation(result, "swing", db_path)
        conn = duckdb.connect(db_path)
        rows = conn.execute("SELECT ticker, strategy, position_size FROM capital_allocation").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "AAPL"

    def test_kelly_sizing_different_regimes(self):
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        bull = calculate_position_size(200000, 50000, settings.kelly_fraction, 80.0, "leaps", "Bull")
        bear = calculate_position_size(200000, 50000, settings.kelly_fraction, 80.0, "leaps", "Bear")
        assert bull.position_size > bear.position_size


class TestRiskAssessmentIntegration:
    def test_assess_portfolio_risk(self, portfolio_db):
        from app.engines.risk.service import assess_portfolio_risk
        db_path, _ = portfolio_db
        assessment = assess_portfolio_risk(db_path, total_value=200000, cash=50000)
        assert assessment.portfolio_health_score > 0
        assert assessment.current_exposure > 0
        assert assessment.total_value > 0

    def test_trade_validation_with_real_state(self, portfolio_db):
        from app.engines.portfolio.service import load_portfolio_state
        from app.engines.risk.service import validate_trade
        db_path, _ = portfolio_db
        state = load_portfolio_state(db_path)
        # Small trade in ENERGY sector (not overweight) should pass
        result = validate_trade(
            ticker="XOM", requested_size=5000,
            total_portfolio_value=state.total_value,
            cash_available=state.cash, sector="ENERGY",
            sector_exposures=state.sector_exposures,
            current_delta=state.portfolio_delta_e,
        )
        assert result.checks_passed > 0


class TestReplacementIntegration:
    def test_find_replacements_with_real_data(self, portfolio_db):
        from app.engines.replacement.service import find_replacements
        positions = [
            {"ticker": "XOM", "score": 40, "regime": "Range", "sector": "ENERGY",
             "trend_score": 35, "momentum_score": 30, "unrealized_pl_pct": -5, "days_held": 60},
        ]
        opportunities = [
            {"ticker": "AAPL", "score": 85, "sector": "TECHNOLOGY"},
            {"ticker": "NVDA", "score": 78, "sector": "TECHNOLOGY"},
        ]
        result = find_replacements(positions, opportunities, min_score_gap=10)
        assert len(result.replacements) > 0
        assert result.replacements[0].current_ticker == "XOM"


class TestFullPipeline:
    def test_all_engines_together(self, portfolio_db):
        """All 5 engines work in sequence without error."""
        db_path, _ = portfolio_db

        # 1. Portfolio state
        from app.engines.portfolio.service import load_portfolio_state, calculate_portfolio_impact
        state = load_portfolio_state(db_path)
        assert state.num_positions > 0

        # 2. Allocation
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        alloc = calculate_position_size(state.total_value, state.cash,
            settings.kelly_fraction, 80.0, "swing", "Bull")
        assert alloc.position_size > 0

        # 3. Opportunity cost
        from app.engines.cost.service import rank_opportunity_cost
        candidates = [
            {"candidate": "AAPL", "score": 80, "risk_score": 5, "estimated_return_pct": 15, "capital_required": 10000},
            {"candidate": "XOM", "score": 60, "risk_score": 8, "estimated_return_pct": 8, "capital_required": 5000},
        ]
        cost = rank_opportunity_cost(candidates, state.cash, state.total_value, state.positions)
        assert len(cost["candidates"]) == 2

        # 4. Replacements
        from app.engines.replacement.service import find_replacements
        pos_list = [{"ticker": "XOM", "score": 40, "regime": "Range", "sector": "ENERGY",
                     "trend_score": 35, "momentum_score": 30, "unrealized_pl_pct": -5, "days_held": 60}]
        opps = [{"ticker": "AAPL", "score": 85, "sector": "TECHNOLOGY"}]
        repl = find_replacements(pos_list, opps, min_score_gap=10)
        assert len(repl.evaluations) == 1

        # 5. Risk assessment
        from app.engines.risk.service import assess_portfolio_risk, validate_trade
        assessment = assess_portfolio_risk(db_path, total_value=state.total_value, cash=state.cash)
        assert assessment.portfolio_health_score > 0

        trade = validate_trade("AAPL", 10000, state.total_value, state.cash,
                              "TECHNOLOGY", state.sector_exposures, state.portfolio_delta_e)
        assert trade.checks_passed > 0
