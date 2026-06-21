"""Integration tests for Phase 3 opportunity pipeline end-to-end."""

import pytest
import numpy as np


@pytest.fixture
def sample_signals():
    rng = np.random.default_rng(42)
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
    return [{"ticker": t, "regime_score": float(rng.uniform(20, 95)),
        "breakout_score": float(rng.uniform(10, 90)),
        "relative_strength_score": float(rng.uniform(15, 95)),
        "cusum_score": float(rng.uniform(10, 80)),
        "volume_score": float(rng.uniform(20, 85)),
        "trend_score": float(rng.uniform(25, 90))}
        for t in tickers]


class TestOpportunityPipelineIntegration:
    def test_build_scores_with_realistic_signals(self, sample_signals):
        """build_opportunity_scores works with realistic signal dicts."""
        from app.engines.opportunity.service import build_opportunity_scores
        scores = build_opportunity_scores(sample_signals)
        assert len(scores) == len(sample_signals)
        for s in scores:
            assert 0 <= s.total_score <= 100
            assert s.ticker in [sig["ticker"] for sig in sample_signals]
            assert s.strategy_type in ("swing", "csp", "leaps", "pmcc")

    def test_ranking_produces_consistent_order(self, sample_signals):
        """rank_opportunities sorts descending."""
        from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities
        scores = build_opportunity_scores(sample_signals)
        ranked = rank_opportunities(scores)
        for i in range(len(ranked) - 1):
            assert ranked[i].total_score >= ranked[i + 1].total_score
        assert ranked[0].rank == 1

    def test_xgboost_refinement_integration(self, sample_signals):
        """XGBoost model refines scores in pipeline."""
        from app.engines.opportunity.model import ScoringRefinementModel
        from app.engines.opportunity.service import build_opportunity_scores
        model = ScoringRefinementModel()
        X, y = model.generate_synthetic_data(200)
        model.train(X, y)
        scores = build_opportunity_scores(sample_signals, model=model)
        has_refined = sum(1 for s in scores if s.refined_score is not None)
        assert has_refined == len(sample_signals)
        for s in scores:
            assert 0 <= s.refined_score <= 100

    def test_score_formula_consistency(self):
        """High scores > medium > low."""
        from app.engines.opportunity.service import compute_opportunity_score
        high = compute_opportunity_score(90, 85, 95, 80, 75, 90)
        mid = compute_opportunity_score(50, 50, 50, 50, 50, 50)
        low = compute_opportunity_score(10, 10, 10, 10, 10, 10)
        assert high > mid > low

    def test_strategy_selection_edge_cases(self):
        """Strategy engine handles missing data gracefully."""
        from app.engines.strategy.service import select_strategy

        no_signal = select_strategy({"ticker": "TEST", "regime": "Range",
            "trend_strength": 0.5, "momentum": 0.0})
        assert no_signal.recommendation in ("hold", "covered_call", "avoid")

        bearish = select_strategy({"ticker": "TEST", "regime": "Crisis"})
        assert bearish.recommendation == "close"

        bear_hold = select_strategy({"ticker": "TEST", "regime": "Bear"})
        assert bear_hold.recommendation == "hold"

    def test_black_scholes_consistency(self):
        """Lower strike = higher call premium."""
        from app.engines.options.service import black_scholes_price
        prices = [black_scholes_price(100.0, K, 0.5, 0.05, 0.25, option_type="call")
                  for K in [80, 90, 100, 110, 120]]
        for i in range(len(prices) - 1):
            assert prices[i] > prices[i + 1]

    def test_csp_generation_reasonable_values(self):
        """CSP has reasonable delta, yield, PoP."""
        from app.engines.options.service import generate_csp
        csp = generate_csp(ticker="AAPL", underlying_price=150.0, implied_volatility=0.30,
                           risk_free_rate=0.05, days_to_expiration=45)
        assert 0.15 <= abs(csp.delta) <= 0.35
        assert csp.annualized_yield > 0
        assert csp.probability_of_profit > 0.5

    def test_leaps_generation_reasonable_values(self):
        """LEAPS has deep ITM delta, cost basis, breakeven."""
        from app.engines.options.service import generate_leaps
        leaps = generate_leaps(ticker="AAPL", underlying_price=150.0, implied_volatility=0.35,
                               risk_free_rate=0.05, days_to_expiration=365)
        assert leaps.delta >= 0.65
        assert leaps.leverage_factor > 0
        assert leaps.intrinsic_value >= 0

    def test_full_pipeline_runs_without_error(self, sample_signals):
        """End-to-end: signals -> opportunities -> strategy -> option generation."""
        from app.engines.opportunity.service import build_opportunity_scores, rank_opportunities
        from app.engines.strategy.service import select_strategy
        from app.engines.options.service import generate_csp

        scores = build_opportunity_scores(sample_signals)
        ranked = rank_opportunities(scores, top_n=3)
        assert len(ranked) == 3

        for s in ranked:
            context = {"ticker": s.ticker, "regime_score": s.regime_score,
                "breakout_score": s.breakout_score,
                "relative_strength_score": s.relative_strength_score,
                "regime": "Bull" if s.total_score > 60 else "Range",
                "momentum": 0.01,
                "trend_strength": 0.5,
                "iv_percentile": 0.6,
                "put_skew": 0.1,
                "term_structure": 0.1}
            strat = select_strategy(context)
            assert strat.recommendation in (
                "buy_stock", "buy_leaps", "sell_csp", "pmcc",
                "covered_call", "close", "roll", "hold", "avoid")

        csp = generate_csp(ticker=ranked[0].ticker, underlying_price=150.0,
                           implied_volatility=0.30, risk_free_rate=0.05,
                           days_to_expiration=45)
        assert csp.premium > 0
