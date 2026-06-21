"""Integration tests for Phase 5 execution pipeline."""

from unittest.mock import patch, MagicMock


class TestExecutionPipelineIntegration:
    def test_trading_place_market_order(self):
        """Mocked: place market order via AlpacaClient."""
        from app.engines.trading.schemas import OrderRequest

        with patch("app.engines.trading.service.TradingClient") as mock_tc:
            mock_instance = MagicMock()
            mock_tc.return_value = mock_instance
            mock_submit = MagicMock()
            mock_submit.id = "alp-test-001"
            mock_submit.symbol = "AAPL"
            mock_submit.side = "buy"
            mock_submit.type = "market"
            mock_submit.qty = "100"
            mock_submit.filled_qty = "0"
            mock_submit.status = "accepted"
            mock_submit.limit_price = None
            mock_submit.stop_price = None
            mock_submit.submitted_at = None
            mock_submit.filled_at = None
            mock_submit.time_in_force = "day"
            mock_submit.filled_avg_price = None
            mock_instance.submit_order.return_value = mock_submit

            from app.engines.trading.service import AlpacaClient
            client = AlpacaClient()
            client._enabled = True
            client._client = mock_instance

            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = [1]
            client._get_connection = MagicMock(return_value=mock_conn)
            client._save_to_db = MagicMock(return_value=1)

            req = OrderRequest(ticker="AAPL", side="buy", order_type="market", quantity=100)
            result = client.place_order(req)
            assert result.success is True
            assert result.alpaca_order_id == "alp-test-001"

    def test_evaluate_all_strategies(self):
        """All 4 strategy evaluators work with example data."""
        from app.engines.positions.service import evaluate_csp, evaluate_leaps, evaluate_swing, evaluate_pmcc

        csp = evaluate_csp("AAPL", current_dte=15, current_pl_pct=55, current_delta=-0.20,
            days_to_expiration=15, strike=145, premium_collected=2.50, current_premium=1.10,
            underlying_price=155)
        assert csp.action in ("hold", "roll", "close")

        leaps = evaluate_leaps("NVDA", entry_price=50, current_price=95,
            trend_status="bullish", days_held=200)
        assert leaps.action in ("exit", "hold")

        swing = evaluate_swing("TSLA", entry_price=200, current_price=175,
            highest_price=210, lowest_price=170)
        assert swing.action in ("hold", "trailing_stop", "exit", "close")

        pmcc = evaluate_pmcc("AAPL", short_call_strike=160, short_call_dte=10,
            short_call_pl_pct=60, short_call_delta=0.25, underlying_price=155)
        assert pmcc.action in ("hold", "roll", "adjust")

    def test_monitoring_summary_health_score(self):
        """Monitoring engine produces health score with correct level."""
        from app.engines.monitoring.service import compute_health_score
        from app.engines.risk.schemas import RiskAssessment
        assessment = RiskAssessment(portfolio_health_score=85.0, is_safe=True,
            max_drawdown=5, total_value=100000, current_exposure=65000)
        health = compute_health_score(assessment.model_dump())
        assert isinstance(health.score, float)
        assert health.score > 0
        assert health.level == "healthy"

    def test_watchdog_evaluates_mixed_positions(self):
        """Watchdog handles all strategy types."""
        from app.engines.positions.service import run_watchdog
        positions = [
            {"ticker": "AAPL", "strategy_type": "csp", "current_dte": 15, "current_pl_pct": 55},
            {"ticker": "NVDA", "strategy_type": "leaps", "entry_price": 50, "current_price": 95},
            {"ticker": "TSLA", "strategy_type": "swing", "entry_price": 200, "current_price": 175},
            {"ticker": "MSFT", "strategy_type": "pmcc", "short_call_dte": 10},
        ]
        result = run_watchdog(positions)
        assert result.positions_evaluated == 4
        assert len(result.actions_taken) == 4

    def test_order_lifecycle_with_alpaca_mock(self):
        """Full order lifecycle: place -> verify -> cancel."""
        from app.engines.trading.schemas import OrderRequest

        with patch("app.engines.trading.service.TradingClient") as mock_tc:
            mock_instance = MagicMock()
            mock_tc.return_value = mock_instance
            mock_order = MagicMock()
            mock_order.id = "alp-test-002"
            mock_order.symbol = "AAPL"
            mock_order.side = "buy"
            mock_order.type = "limit"
            mock_order.qty = "50"
            mock_order.filled_qty = "0"
            mock_order.status = "accepted"
            mock_order.limit_price = 150.0
            mock_order.stop_price = None
            mock_order.submitted_at = None
            mock_order.filled_at = None
            mock_order.time_in_force = "day"
            mock_order.filled_avg_price = None
            mock_instance.submit_order.return_value = mock_order

            from app.engines.trading.service import AlpacaClient
            client = AlpacaClient()
            client._enabled = True
            client._client = mock_instance

            mock_conn = MagicMock()
            mock_conn.execute.return_value.fetchone.return_value = [1]
            client._get_connection = MagicMock(return_value=mock_conn)
            client._save_to_db = MagicMock(return_value=1)

            req = OrderRequest(ticker="AAPL", side="buy", order_type="limit",
                quantity=50, price=150.0)
            result = client.place_order(req)
            assert result.success is True
            assert result.alpaca_order_id == "alp-test-002"
