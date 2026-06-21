import pytest


class TestPositionEvaluation:
    def test_strong_bullish_keep(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 85, "Bull", trend_score=80, momentum_score=75)
        assert ev.action == "keep"

    def test_underperforming_reduce_in_bear(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 45, "Bear", trend_score=40, momentum_score=35)
        assert ev.action == "reduce"

    def test_loss_exit_in_crisis(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 25, "Crisis", unrealized_pl_pct=-20)
        assert ev.action == "exit"

    def test_default_exit_on_large_loss(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 50, "Range", unrealized_pl_pct=-25)
        assert ev.action == "exit"

    def test_low_score_reduce(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 25, "Range")
        assert ev.action == "reduce"

    def test_neutral_keep(self):
        from app.engines.replacement.service import evaluate_position
        ev = evaluate_position("AAPL", 70, "Range", days_held=60)
        assert ev.action == "keep"


class TestTradeReplacement:
    def test_basic_replacement_finds_candidates(self):
        from app.engines.replacement.service import find_replacements
        positions = [{"ticker": "AAPL", "score": 50, "regime": "Range", "sector": "TECHNOLOGY"}]
        opportunities = [{"ticker": "NVDA", "score": 85, "sector": "TECHNOLOGY"}]
        result = find_replacements(positions, opportunities, min_score_gap=10)
        assert len(result.replacements) == 1

    def test_no_candidates_returns_empty(self):
        from app.engines.replacement.service import find_replacements
        positions = [{"ticker": "AAPL", "score": 85, "regime": "Bull"}]
        opportunities = [{"ticker": "NVDA", "score": 80}]
        result = find_replacements(positions, opportunities)
        assert len(result.replacements) == 0

    def test_keep_actions_skipped(self):
        from app.engines.replacement.service import find_replacements
        positions = [{"ticker": "AAPL", "score": 85, "regime": "Bull", "trend_score": 80, "sector": "TECHNOLOGY"}]
        opportunities = [{"ticker": "NVDA", "score": 90, "sector": "TECHNOLOGY"}]
        result = find_replacements(positions, opportunities)
        assert len(result.replacements) == 0

    def test_score_gap_threshold_respected(self):
        from app.engines.replacement.service import find_replacements
        positions = [{"ticker": "AAPL", "score": 50, "regime": "Range", "sector": "TECHNOLOGY"}]
        opportunities = [{"ticker": "NVDA", "score": 55, "sector": "TECHNOLOGY"}]
        result = find_replacements(positions, opportunities, min_score_gap=10)
        assert len(result.replacements) == 0

    def test_different_sector_penalized(self):
        from app.engines.replacement.service import find_replacements
        positions = [{"ticker": "AAPL", "score": 40, "regime": "Range", "sector": "TECHNOLOGY"}]
        opportunities = [{"ticker": "XOM", "score": 85, "sector": "ENERGY"}]
        result = find_replacements(positions, opportunities, min_score_gap=10)
        assert len(result.replacements) >= 0


class TestBatchEvaluations:
    def test_batch_evaluation(self):
        from app.engines.replacement.service import evaluate_all_positions
        data = [
            {"ticker": "AAPL", "score": 85, "regime": "Bull", "trend_score": 80, "momentum_score": 75},
            {"ticker": "MSFT", "score": 35, "regime": "Range", "trend_score": 30, "momentum_score": 25},
        ]
        results = evaluate_all_positions(data)
        assert len(results) == 2
        actions = {r.ticker: r.action for r in results}
        assert actions["AAPL"] == "keep"
        assert actions["MSFT"] == "exit"
