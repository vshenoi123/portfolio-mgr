def rank_opportunity_cost(
    candidates: list[dict],
    cash_available: float,
    total_portfolio_value: float = 0.0,
    existing_positions: list[dict] | None = None,
    watchlist: list[str] | None = None,
) -> dict:
    existing_positions = existing_positions or []
    watchlist = watchlist or []
    existing_tickers = {p.get("ticker", "").upper() for p in existing_positions}
    watchlist_set = {t.upper() for t in watchlist}

    scored = []
    for c in candidates:
        score = c.get("score", 0)
        risk = c.get("risk_score", 5)
        est_return = c.get("estimated_return_pct", 0)
        capital = c.get("capital_required", 0)
        ticker = c.get("candidate", "").upper()

        risk_adjusted = score * (1 - risk / 200.0)
        return_per_dollar = (est_return / capital * 100) if capital > 0 else 0

        if ticker in existing_tickers:
            type_bonus = 5.0
            cost_type = "add_to_existing"
        elif ticker in watchlist_set:
            type_bonus = 3.0
            cost_type = "watchlist"
        else:
            type_bonus = 0.0
            cost_type = "new_position"

        existing_weight = 0.0
        for p in existing_positions:
            if p.get("ticker", "").upper() == ticker:
                existing_weight = p.get("weight_pct", 0)
                break
        concentration_penalty = 0
        if existing_weight > 20:
            concentration_penalty = 5

        capital_penalty = 0
        if capital > cash_available:
            capital_penalty = 20

        final_score = risk_adjusted + (return_per_dollar * 0.5) + type_bonus - concentration_penalty - capital_penalty

        scored.append({
            "candidate": c.get("candidate", ticker),
            "original_score": score,
            "risk_adjusted_score": round(risk_adjusted, 2),
            "final_score": round(final_score, 2),
            "cost_type": cost_type,
            "estimated_return_pct": est_return,
            "risk_score": risk,
            "capital_required": capital,
            "rationale": _generate_rationale(cost_type, ticker, existing_weight, capital_penalty),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)

    rec = "No candidates"
    if scored:
        best = scored[0]
        rec = f"Best opportunity: {best['candidate']} (score: {best['final_score']:.1f}, cost: {best['cost_type']})"

    return {
        "candidates": scored,
        "cash_available": cash_available,
        "total_portfolio_value": total_portfolio_value,
        "recommendation": rec,
        "details": {"total_candidates": len(candidates), "qualified": len(scored)},
    }


def _generate_rationale(cost_type: str, ticker: str, existing_weight: float, capital_penalty: int) -> str:
    if cost_type == "add_to_existing":
        return f"{ticker}: adding to existing position (weight: {existing_weight:.1f}%)"
    elif cost_type == "watchlist":
        return f"{ticker}: watchlist candidate with affinity bonus"
    else:
        base = f"{ticker}: new position opportunity"
        if capital_penalty > 0:
            base += " (constrained by available cash)"
        return base
