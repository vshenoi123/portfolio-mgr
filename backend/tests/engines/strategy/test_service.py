

class TestStrategyRules:
    def test_rule_based_scores_returns_all_recommendations(self):
        from app.engines.strategy.service import rule_based_scores
        context = {"regime": "Bull", "momentum": 0.01, "trend_strength": 0.6, "iv_percentile": 0.3}
        scores = rule_based_scores(context)
        expected_keys = [
            "buy_stock", "buy_leaps", "sell_csp", "pmcc",
            "covered_call", "close", "roll", "hold", "avoid",
        ]
        for key in expected_keys:
            assert key in scores, f"Missing key: {key}"
        assert len(scores) == 9

    def test_rule_based_scores_bull_regime_ranks_buy_stock_highest(self):
        from app.engines.strategy.service import rule_based_scores
        context = {
            "regime": "Bull",
            "momentum": 0.02,
            "trend_strength": 0.7,
            "iv_percentile": 0.3,
            "put_skew": 0.1,
            "term_structure": 0.1,
            "drawdown": 0.02,
            "days_to_expiry": 45,
        }
        scores = rule_based_scores(context)
        assert scores["buy_stock"] > scores["hold"]
        assert scores["buy_stock"] > scores["avoid"]
        assert 0 <= scores["buy_stock"] <= 1

    def test_rule_based_scores_crisis_regime_ranks_avoid_highest(self):
        from app.engines.strategy.service import rule_based_scores
        context = {
            "regime": "Crisis",
            "momentum": -0.08,
            "trend_strength": 0.1,
            "iv_percentile": 0.9,
            "put_skew": 0.5,
            "term_structure": -0.3,
            "drawdown": 0.2,
            "days_to_expiry": 10,
        }
        scores = rule_based_scores(context)
        assert scores["avoid"] > scores["buy_stock"]
        assert scores["close"] > scores["hold"]
        assert scores["avoid"] > 0.5

    def test_rule_based_scores_range_regime_prefers_covered_call(self):
        from app.engines.strategy.service import rule_based_scores
        context = {
            "regime": "Range",
            "momentum": 0.005,
            "trend_strength": 0.2,
            "iv_percentile": 0.6,
            "put_skew": 0.2,
            "term_structure": 0.1,
            "drawdown": 0.03,
            "days_to_expiry": 30,
        }
        scores = rule_based_scores(context)
        assert scores["covered_call"] >= 0.4
        assert scores["sell_csp"] >= 0.4

    def test_rule_based_scores_defaults_when_context_empty(self):
        from app.engines.strategy.service import rule_based_scores
        scores = rule_based_scores({})
        for key, val in scores.items():
            assert 0 <= val <= 1, f"Score out of range for {key}: {val}"

    def test_select_strategy_returns_strategy_output_with_rules_only(self):
        from app.engines.strategy.service import select_strategy
        context = {"ticker": "SPY", "regime": "Bull", "momentum": 0.015, "trend_strength": 0.6}
        result = select_strategy(context, ml_model=None)
        assert result.ticker == "SPY"
        assert result.recommendation in [
            "buy_stock", "buy_leaps", "sell_csp", "pmcc",
            "covered_call", "close", "roll", "hold", "avoid",
        ]
        assert 0 <= result.confidence <= 1
        assert isinstance(result.reasoning, str)
        assert isinstance(result.risk_assessment, str)
        assert "rule_scores" in result.details

    def test_select_strategy_handles_missing_ticker(self):
        from app.engines.strategy.service import select_strategy
        context = {"regime": "Bear", "momentum": -0.02, "trend_strength": 0.1}
        result = select_strategy(context)
        assert result.ticker == "UNKNOWN"


class TestStrategyMLConfidence:
    def test_ml_model_initially_not_fitted(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        assert not model.fitted

    def test_ml_model_fit_and_predict(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        contexts = [
            {"regime": "Bull", "momentum": 0.02, "trend_strength": 0.7, "iv_percentile": 0.3},
            {"regime": "Bear", "momentum": -0.03, "trend_strength": 0.2, "iv_percentile": 0.8},
            {"regime": "Range", "momentum": 0.001, "trend_strength": 0.1, "iv_percentile": 0.5},
            {"regime": "Crisis", "momentum": -0.08, "trend_strength": 0.05, "iv_percentile": 0.9},
            {"regime": "Bull High Vol", "momentum": 0.01, "trend_strength": 0.5, "iv_percentile": 0.4},
        ]
        targets = [0.8, 0.1, 0.5, 0.05, 0.7]
        model.fit(contexts, targets)
        assert model.fitted

        conf, unc = model.predict(contexts[0])
        assert 0 <= conf <= 1
        assert unc >= 0

    def test_ml_model_predict_returns_tuple(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        contexts = [
            {"regime": "Bull", "momentum": 0.01, "trend_strength": 0.5, "iv_percentile": 0.4},
            {"regime": "Bear", "momentum": -0.02, "trend_strength": 0.2, "iv_percentile": 0.7},
        ]
        targets = [0.7, 0.2]
        model.fit(contexts, targets)
        conf, unc = model.predict({"regime": "Bull", "momentum": 0.02, "trend_strength": 0.6, "iv_percentile": 0.3})
        assert isinstance(conf, float)
        assert isinstance(unc, float)
        assert 0 <= conf <= 1
        assert unc >= 0

    def test_ml_model_predict_before_fit_still_returns(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        conf, unc = model.predict({"regime": "Bull", "momentum": 0.01, "trend_strength": 0.5, "iv_percentile": 0.3})
        assert 0 <= conf <= 1
        assert unc == 0.0

    def test_select_strategy_with_ml_model(self):
        from app.engines.strategy.service import select_strategy, StrategyConfidenceModel
        model = StrategyConfidenceModel()
        contexts = [
            {"regime": "Bull", "momentum": 0.02, "trend_strength": 0.7, "iv_percentile": 0.3},
            {"regime": "Bear", "momentum": -0.03, "trend_strength": 0.2, "iv_percentile": 0.8},
            {"regime": "Range", "momentum": 0.001, "trend_strength": 0.1, "iv_percentile": 0.5},
        ]
        targets = [0.85, 0.1, 0.45]
        model.fit(contexts, targets)

        result = select_strategy({"ticker": "SPY", "regime": "Bull", "momentum": 0.02, "trend_strength": 0.7}, ml_model=model)
        assert result.ticker == "SPY"
        assert 0 <= result.confidence <= 1
        assert result.details["ml_confidence"] is not None

    def test_strategy_confidence_model_robust_to_missing_features(self):
        from app.engines.strategy.service import StrategyConfidenceModel
        model = StrategyConfidenceModel()
        contexts = [{"regime": "Bull"}, {"regime": "Bear"}, {"regime": "Range"}]
        targets = [0.7, 0.2, 0.5]
        model.fit(contexts, targets)
        conf, unc = model.predict({"regime": "Bull"})
        assert 0 <= conf <= 1
        assert unc >= 0
