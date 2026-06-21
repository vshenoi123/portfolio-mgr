from app.engines.opportunity.schemas import OpportunityScore

SCORE_WEIGHTS = {
    "regime": 0.25,
    "breakout": 0.20,
    "relative_strength": 0.20,
    "cusum": 0.15,
    "volume": 0.10,
    "trend": 0.10,
}


def compute_opportunity_score(
    regime_score: float | None, breakout_score: float | None,
    relative_strength_score: float | None, cusum_score: float | None,
    volume_score: float | None, trend_score: float | None,
) -> float:
    components = {
        "regime": regime_score, "breakout": breakout_score,
        "relative_strength": relative_strength_score,
        "cusum": cusum_score, "volume": volume_score,
        "trend": trend_score,
    }
    weighted_sum = 0.0
    for key, weight in SCORE_WEIGHTS.items():
        val = components.get(key)
        if val is not None:
            weighted_sum += weight * val
    return round(weighted_sum, 2)


def rank_opportunities(
    scores: list[OpportunityScore],
    top_n: int | None = None,
    min_score: float = 0.0,
) -> list[OpportunityScore]:
    filtered = [s for s in scores if s.total_score >= min_score]
    sorted_scores = sorted(filtered, key=lambda s: s.total_score, reverse=True)
    if top_n is not None:
        sorted_scores = sorted_scores[:top_n]
    for i, s in enumerate(sorted_scores):
        s.rank = i + 1
    return sorted_scores


def filter_by_strategy(scores: list[OpportunityScore], strategy_type: str) -> list[OpportunityScore]:
    if strategy_type == "all":
        return scores
    return [s for s in scores if s.strategy_type == strategy_type]


def assign_strategy_type(
    regime_score: float, breakout_score: float,
    relative_strength_score: float, total_score: float,
) -> str:
    if total_score >= 80 and regime_score >= 70 and relative_strength_score >= 70:
        return "leaps"
    if total_score >= 65 and regime_score >= 55:
        if breakout_score >= 60 and relative_strength_score >= 60:
            return "pmcc"
        return "csp"
    return "swing"


def build_opportunity_scores(signals: list[dict], model=None) -> list[OpportunityScore]:
    scores = []
    for sig in signals:
        regime = sig.get("regime_score", 0)
        breakout = sig.get("breakout_score", 0)
        rs = sig.get("relative_strength_score", 0)
        cusum = sig.get("cusum_score", 0)
        volume = sig.get("volume_score", 0)
        trend = sig.get("trend_score", 0)
        total = compute_opportunity_score(regime, breakout, rs, cusum, volume, trend)
        refined = None
        if model is not None:
            try:
                refined = model.refine_single(regime, breakout, rs, cusum, volume, trend)
            except RuntimeError:
                pass
        strategy = assign_strategy_type(regime, breakout, rs, total)
        scores.append(OpportunityScore(
            ticker=sig["ticker"], total_score=total,
            regime_score=regime, breakout_score=breakout,
            relative_strength_score=rs, cusum_score=cusum,
            volume_score=volume, trend_score=trend,
            refined_score=refined, strategy_type=strategy,
        ))
    return scores
