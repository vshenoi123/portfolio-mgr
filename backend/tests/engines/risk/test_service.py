import pytest


class TestPortfolioHealth:
    def test_health_score_perfect(self):
        from app.engines.risk.service import calculate_portfolio_health
        score = calculate_portfolio_health(max_drawdown=5, concentration_pct=20,
            portfolio_beta=1.0, total_exposure_pct=50, cash_pct=20)
        assert 80 <= score <= 100

    def test_health_score_poor(self):
        from app.engines.risk.service import calculate_portfolio_health
        score = calculate_portfolio_health(max_drawdown=30, concentration_pct=80,
            portfolio_beta=2.5, total_exposure_pct=95, cash_pct=0, num_violations=5)
        assert score < 40

    def test_health_score_mid(self):
        from app.engines.risk.service import calculate_portfolio_health
        score = calculate_portfolio_health(max_drawdown=15, concentration_pct=40,
            portfolio_beta=1.2, total_exposure_pct=65, cash_pct=15, num_violations=1)
        assert 40 <= score <= 80

    def test_health_score_extreme_drawdown(self):
        from app.engines.risk.service import calculate_portfolio_health
        score = calculate_portfolio_health(max_drawdown=50)
        assert score < 50


class TestRiskLimitEnforcement:
    def test_position_size_passes(self):
        from app.engines.risk.service import check_position_size_limit
        result = check_position_size_limit("AAPL", 10000, 100000, 15.0)
        assert result["passed"] is True

    def test_position_size_fails(self):
        from app.engines.risk.service import check_position_size_limit
        result = check_position_size_limit("AAPL", 20000, 100000, 15.0)
        assert result["passed"] is False

    def test_sector_exposure_passes(self):
        from app.engines.risk.service import check_sector_exposure
        result = check_sector_exposure("TECHNOLOGY", 5000, {"TECHNOLOGY": 20}, 100000)
        assert result["passed"] is True

    def test_sector_unknown_passes(self):
        from app.engines.risk.service import check_sector_exposure
        result = check_sector_exposure("UNKNOWN", 50000, {}, 100000)
        assert result["passed"] is True

    def test_delta_passes(self):
        from app.engines.risk.service import check_portfolio_delta
        result = check_portfolio_delta(100, 200, 500)
        assert result["passed"] is True

    def test_delta_fails(self):
        from app.engines.risk.service import check_portfolio_delta
        result = check_portfolio_delta(400, 200, 500)
        assert result["passed"] is False

    def test_cash_passes(self):
        from app.engines.risk.service import check_cash_available
        result = check_cash_available(5000, 20000, 10, 100000)
        assert result["passed"] is True

    def test_cash_fails(self):
        from app.engines.risk.service import check_cash_available
        result = check_cash_available(50000, 20000, 10, 100000)
        assert result["passed"] is False


class TestTradeRiskCheck:
    def test_all_checks_pass(self):
        from app.engines.risk.service import validate_trade
        result = validate_trade("AAPL", 10000, 100000, 30000, "TECHNOLOGY", {}, 100)
        assert result.is_allowed is True
        assert result.checks_failed == 0

    def test_blocked_by_size(self):
        from app.engines.risk.service import validate_trade
        result = validate_trade("AAPL", 50000, 100000, 30000, "TECHNOLOGY", {}, 100)
        assert result.is_allowed is False

    def test_blocked_by_sector(self):
        from app.engines.risk.service import validate_trade
        result = validate_trade("AAPL", 5000, 100000, 30000, "TECHNOLOGY",
                               {"TECHNOLOGY": 28.0}, 100)
        assert result.is_allowed is False

    def test_blocked_by_cash(self):
        from app.engines.risk.service import validate_trade
        result = validate_trade("AAPL", 50000, 100000, 5000, "TECHNOLOGY", {}, 100)
        assert result.is_allowed is False


class TestRiskAssessmentFull:
    def test_safe_assessment(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        conn.execute("INSERT INTO portfolio_snapshots (date, total_value, cash) VALUES (CURRENT_DATE, 100000, 25000)")
        conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type) VALUES ('AAPL', 50, 150, 160, 'TECHNOLOGY', 'equity')")
        close_connection(test_db_path)

        from app.engines.risk.service import assess_portfolio_risk
        assessment = assess_portfolio_risk(test_db_path, total_value=100000, cash=25000)
        assert assessment.is_safe is True

    def test_violations_with_concentrated(self, test_db_path):
        from app.database import get_connection, close_connection
        conn = get_connection(test_db_path)
        conn.execute("INSERT INTO portfolio_snapshots (date, total_value, cash) VALUES (CURRENT_DATE, 100000, 10000)")
        conn.execute("INSERT INTO positions (ticker, quantity, avg_price, current_price, sector, strategy_type) VALUES ('AAPL', 500, 150, 160, 'TECHNOLOGY', 'equity')")
        close_connection(test_db_path)

        from app.engines.risk.service import assess_portfolio_risk
        assessment = assess_portfolio_risk(test_db_path, total_value=100000, cash=10000)
        assert len(assessment.violations) > 0
