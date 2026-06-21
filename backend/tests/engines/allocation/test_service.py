import pytest
from datetime import date


class TestKellyCriterion:
    def test_kelly_standard_case(self):
        from app.engines.allocation.service import kelly_criterion
        result = kelly_criterion(0.60, 1.5)
        assert result == pytest.approx(0.3333, rel=0.01)

    def test_kelly_fifty_fifty(self):
        from app.engines.allocation.service import kelly_criterion
        result = kelly_criterion(0.50, 1.0)
        assert result == 0.0

    def test_kelly_high_probability(self):
        from app.engines.allocation.service import kelly_criterion
        result = kelly_criterion(0.90, 2.0)
        assert result > 0.8

    def test_kelly_zero_probability(self):
        from app.engines.allocation.service import kelly_criterion
        assert kelly_criterion(0.0, 1.5) == 0.0

    def test_kelly_certain(self):
        from app.engines.allocation.service import kelly_criterion
        assert kelly_criterion(1.0, 1.5) == 0.0

    def test_fractional_kelly(self):
        from app.engines.allocation.service import fractional_kelly
        result = fractional_kelly(0.60, 1.5, 0.25)
        assert result == pytest.approx(0.0833, rel=0.01)


class TestPositionSizing:
    def test_kelly_with_large_cash(self):
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        result = calculate_position_size(250000.0, 75000.0,
            settings.kelly_fraction, 75.0, "swing", "Bull")
        assert result.position_size > 0

    def test_zero_cash_returns_zero(self):
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        result = calculate_position_size(100000.0, 0.0, settings.kelly_fraction, 80.0, "swing", "Bull")
        assert result.position_size == 0.0

    def test_low_score_small_position(self):
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        result = calculate_position_size(100000.0, 50000.0, settings.kelly_fraction, 30.0, "swing", "Bull")
        assert result.position_size < 5000

    def test_bear_regime_limits_size(self):
        from app.engines.allocation.service import calculate_position_size
        from app.config import settings
        result = calculate_position_size(100000.0, 50000.0, settings.kelly_fraction, 80.0, "leaps", "Bear")
        assert result.capital_pct < 10


class TestRegimeAwareAllocation:
    def test_bull_allocation_leaps_high(self):
        from app.engines.allocation.service import get_strategy_allocation
        allocs = get_strategy_allocation("Bull")
        leaps = next(a for a in allocs if a.strategy == "leaps")
        assert leaps.allocation_pct > 20

    def test_bear_allocation_csp_and_cash(self):
        from app.engines.allocation.service import get_strategy_allocation
        allocs = get_strategy_allocation("Bear")
        csp = next(a for a in allocs if a.strategy == "csp")
        cash = next(a for a in allocs if a.strategy == "cash")
        assert csp.allocation_pct > 15
        assert cash.allocation_pct > 20

    def test_range_allocation(self):
        from app.engines.allocation.service import get_strategy_allocation
        allocs = get_strategy_allocation("Range")
        swing = next(a for a in allocs if a.strategy == "swing")
        csp = next(a for a in allocs if a.strategy == "csp")
        assert swing.allocation_pct > 15
        assert csp.allocation_pct > 10

    def test_unknown_regime_returns_default(self):
        from app.engines.allocation.service import get_strategy_allocation
        allocs = get_strategy_allocation("Unknown")
        assert len(allocs) > 0


class TestSaveAllocation:
    def test_save_and_read_allocation(self, test_db_path):
        from app.engines.allocation.service import save_allocation, AllocationResult
        result = AllocationResult(ticker="AAPL", position_size=15000.0, capital_pct=15.0,
            strategy_allocation_pct=25.0, regime_at_allocation="Bull",
            total_portfolio_value=100000.0, cash_reserve=10000.0)
        save_allocation(result, "swing", test_db_path)

        import duckdb
        conn = duckdb.connect(test_db_path)
        rows = conn.execute("SELECT ticker, strategy, position_size FROM capital_allocation").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "AAPL"
        assert rows[0][1] == "swing"
        assert float(rows[0][2]) == 15000.0
