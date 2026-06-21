from app.engines.replacement.schemas import PositionEvaluation, TradeReplacement, ReplacementResponse


def evaluate_position(
    ticker: str, score: float, regime: str,
    trend_score: float = 50.0, momentum_score: float = 50.0,
    unrealized_pl_pct: float = 0.0, days_held: int = 0,
) -> PositionEvaluation:
    combined = (score + trend_score + momentum_score) / 3

    if regime in ("Bear", "Bear High Vol", "Crisis"):
        if unrealized_pl_pct < -15 or score < 30:
            return PositionEvaluation(ticker=ticker, score=score, action="exit",
                rationale=f"Exit: bearish regime with loss {unrealized_pl_pct:.1f}% or low score {score:.0f}")
        if combined < 50:
            return PositionEvaluation(ticker=ticker, score=score, action="reduce",
                rationale=f"Reduce: bearish regime, combined score {combined:.0f} < 50")
    elif regime == "Bull":
        if score >= 75 and trend_score >= 70:
            return PositionEvaluation(ticker=ticker, score=score, action="keep",
                rationale=f"Keep: strong score {score:.0f} with bullish trend {trend_score:.0f}")
        if 50 <= score <= 75 and unrealized_pl_pct > 5:
            return PositionEvaluation(ticker=ticker, score=score, action="keep",
                rationale=f"Keep: profitable {unrealized_pl_pct:.1f}% in bullish regime")
    elif regime == "Range":
        if combined < 35:
            return PositionEvaluation(ticker=ticker, score=score, action="exit",
                rationale=f"Exit: range regime, very weak combined score {combined:.0f}")
        if combined < 55 and unrealized_pl_pct >= -20:
            return PositionEvaluation(ticker=ticker, score=score, action="reduce",
                rationale=f"Reduce: range regime, combined score {combined:.0f} < 55")

    if unrealized_pl_pct < -20:
        return PositionEvaluation(ticker=ticker, score=score, action="exit",
            rationale=f"Exit: loss exceeds 20% ({unrealized_pl_pct:.1f}%)")
    if score < 40:
        return PositionEvaluation(ticker=ticker, score=score, action="reduce",
            rationale=f"Reduce: poor score {score:.0f}")
    if score >= 65 and days_held > 30:
        return PositionEvaluation(ticker=ticker, score=score, action="keep",
            rationale=f"Keep: decent score {score:.0f}, held {days_held} days")

    return PositionEvaluation(ticker=ticker, score=score, action="keep",
        rationale=f"Hold: no strong signal to change ({score:.0f})")


def find_replacements(
    current_positions: list[dict],
    opportunity_scores: list[dict],
    min_score_gap: float = 10.0,
) -> ReplacementResponse:
    evaluations = []
    replacements = []

    for pos in current_positions:
        ticker = pos.get("ticker", "")
        score = pos.get("score", 50)
        regime = pos.get("regime", "Range")
        ev = evaluate_position(
            ticker=ticker, score=score, regime=regime,
            trend_score=pos.get("trend_score", 50),
            momentum_score=pos.get("momentum_score", 50),
            unrealized_pl_pct=pos.get("unrealized_pl_pct", 0),
            days_held=pos.get("days_held", 0),
        )
        evaluations.append(ev)

        if ev.action not in ("keep",):
            sector = pos.get("sector", "UNKNOWN")
            for opp in sorted(opportunity_scores, key=lambda x: x.get("score", 0), reverse=True):
                opp_ticker = opp.get("ticker", "")
                if opp_ticker == ticker:
                    continue
                opp_score = opp.get("score", 0)
                gap = opp_score - score
                if gap >= min_score_gap:
                    opp_sector = opp.get("sector", "UNKNOWN")
                    if opp_sector == sector:
                        gap *= 1.2
                    else:
                        gap *= 0.8
                    confidence = min(0.95, max(0.3, gap / 100))
                    replacements.append(TradeReplacement(
                        current_ticker=ticker, current_score=score,
                        replacement_ticker=opp_ticker, replacement_score=opp_score,
                        rationale=f"Replace {ticker} ({score:.0f}) with {opp_ticker} ({opp_score:.0f})",
                        estimated_upside_pct=round(gap, 1),
                        confidence=round(confidence, 2),
                    ))
                    break

    return ReplacementResponse(
        evaluations=evaluations, replacements=replacements,
        total_positions_evaluated=len(current_positions),
    )


def evaluate_all_positions(positions_data: list[dict]) -> list[PositionEvaluation]:
    results = []
    for pos in positions_data:
        ev = evaluate_position(
            ticker=pos.get("ticker", ""),
            score=pos.get("score", 50),
            regime=pos.get("regime", "Range"),
            trend_score=pos.get("trend_score", 50),
            momentum_score=pos.get("momentum_score", 50),
            unrealized_pl_pct=pos.get("unrealized_pl_pct", 0),
            days_held=pos.get("days_held", 0),
        )
        results.append(ev)
    return results
