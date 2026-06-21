from datetime import datetime, timezone


class TestTradeRecord:
    def test_default_construction(self):
        from app.engines.self_learning.schemas import TradeRecord
        tr = TradeRecord(
            ticker="AAPL", side="buy", strategy_type="momentum",
            entry_price=150.0, quantity=100, entry_date=datetime.now(timezone.utc),
        )
        assert tr.ticker == "AAPL"
        assert tr.days_held == 0
        assert tr.exit_reason == ""
        assert tr.regime_at_entry == "Unknown"

    def test_full_construction(self):
        from app.engines.self_learning.schemas import TradeRecord
        dt = datetime.now(timezone.utc)
        tr = TradeRecord(
            ticker="NVDA", side="sell", strategy_type="swing",
            entry_price=800.0, exit_price=850.0, quantity=50,
            gross_pl=2500.0, net_pl=2450.0, entry_date=dt, exit_date=dt,
            days_held=15, exit_reason="target_hit",
            regime_at_entry="Bull", regime_at_exit="Bull",
        )
        assert tr.gross_pl == 2500.0
        assert tr.days_held == 15
        assert tr.exit_reason == "target_hit"
        assert tr.regime_at_entry == "Bull"


class TestSignalEfficacy:
    def test_default_construction(self):
        from app.engines.self_learning.schemas import SignalEfficacy
        se = SignalEfficacy(signal_type="rsi_oversold")
        assert se.total_signals == 0
        assert se.accuracy_pct == 0.0

    def test_full_construction(self):
        from app.engines.self_learning.schemas import SignalEfficacy
        se = SignalEfficacy(
            signal_type="macd_cross", total_signals=20, accurate=15,
            accuracy_pct=75.0, avg_return=2.5,
        )
        assert se.accuracy_pct == 75.0
        assert se.avg_return == 2.5


class TestSelfLearningSummary:
    def test_default_construction(self):
        from app.engines.self_learning.schemas import SelfLearningSummary
        sls = SelfLearningSummary()
        assert sls.total_trades == 0
        assert sls.win_rate == 0.0
        assert sls.signal_efficacy == []

    def test_with_signal_efficacy(self):
        from app.engines.self_learning.schemas import SelfLearningSummary, SignalEfficacy
        se = SignalEfficacy(signal_type="rsi_oversold", total_signals=10, accurate=7, accuracy_pct=70.0, avg_return=1.5)
        sls = SelfLearningSummary(
            total_trades=50, win_rate=60.0, avg_win=500.0, avg_loss=300.0,
            profit_factor=1.8, best_regime="Bull", worst_regime="Bear",
            strategy_breakdown={"momentum": {"count": 20, "avg_pl": 250.0}},
            signal_efficacy=[se],
        )
        assert sls.total_trades == 50
        assert sls.profit_factor == 1.8
        assert len(sls.signal_efficacy) == 1
        assert sls.signal_efficacy[0].accuracy_pct == 70.0
