import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.core.dependencies import verify_api_key
from app.engines.portfolio.service import (
    load_portfolio_state, calculate_portfolio_impact,
    compute_portfolio_beta, compute_portfolio_delta,
    compute_concentration,
)
from app.engines.portfolio.schemas import (
    PortfolioSummaryResponse, HoldingDetail, PortfolioImpactScore, PortfolioPosition,
)
from app.engines.allocation.service import get_strategy_allocation, calculate_position_size
from app.engines.cost.service import rank_opportunity_cost
from app.engines.replacement.service import find_replacements, evaluate_all_positions
from app.engines.risk.service import assess_portfolio_risk, validate_trade
from app.database import get_data_dir
from app.config import settings
import os, json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


@router.get("")
def get_portfolio_summary():
    state = load_portfolio_state(settings.database_path)
    top_holdings = []
    sorted_positions = sorted(state.positions, key=lambda p: p.get("market_value", 0), reverse=True)[:5]
    for p in sorted_positions:
        weight = (p.get("market_value", 0) / state.total_value * 100) if state.total_value > 0 else 0
        top_holdings.append(HoldingDetail(
            ticker=p.get("ticker", ""), quantity=p.get("quantity", 0),
            avg_price=p.get("avg_price", 0), current_price=p.get("current_price", 0),
            market_value=p.get("market_value", 0), unrealized_pl=p.get("unrealized_pl", 0),
            unrealized_pl_pct=p.get("unrealized_pl_pct", 0),
            weight_pct=round(weight, 2),
            sector=p.get("sector", "UNKNOWN"), beta=p.get("beta", 1.0),
            strategy_type=p.get("strategy_type", "equity"),
        ))
    return PortfolioSummaryResponse(
        total_value=state.total_value, cash=state.cash,
        equity_value=state.equity_value, options_value=state.options_value,
        num_positions=state.num_positions, num_options=state.num_options,
        portfolio_beta=state.portfolio_beta, portfolio_delta_e=state.portfolio_delta_e,
        top_holdings=top_holdings,
    )


@router.get("/holdings")
def get_holdings():
    state = load_portfolio_state(settings.database_path)
    holdings = []
    for p in state.positions:
        weight = (p.get("market_value", 0) / state.total_value * 100) if state.total_value > 0 else 0
        holdings.append(HoldingDetail(
            ticker=p.get("ticker", ""), quantity=p.get("quantity", 0),
            avg_price=p.get("avg_price", 0), current_price=p.get("current_price", 0),
            market_value=p.get("market_value", 0), unrealized_pl=p.get("unrealized_pl", 0),
            unrealized_pl_pct=p.get("unrealized_pl_pct", 0),
            weight_pct=round(weight, 2),
            sector=p.get("sector", "UNKNOWN"), beta=p.get("beta", 1.0),
            strategy_type=p.get("strategy_type", "equity"),
        ))
    return holdings


@router.get("/options")
def get_options_positions():
    state = load_portfolio_state(settings.database_path)
    return state.options_positions


@router.get("/health")
def get_portfolio_health():
    assessment = assess_portfolio_risk(settings.database_path)
    return assessment.model_dump()


@router.get("/exposure")
def get_exposure():
    state = load_portfolio_state(settings.database_path)
    positions_list = [PortfolioPosition(**p) for p in state.positions]
    concentration = compute_concentration(positions_list, state.total_value)
    return {
        "sector_exposures": state.sector_exposures,
        "concentration_pct": concentration,
        "num_sectors": len(state.sector_exposures),
    }


@router.get("/impact/{ticker}")
def get_portfolio_impact(ticker: str, raw_score: float = 75.0):
    state = load_portfolio_state(settings.database_path)
    result = calculate_portfolio_impact(
        ticker=ticker.upper(), raw_score=raw_score,
        positions=state.positions, sector_exposures=state.sector_exposures,
        total_value=state.total_value, cash=state.cash,
    )
    return result.model_dump()


@router.get("/allocation")
def get_allocation(regime: str = "Range"):
    allocs = get_strategy_allocation(regime)
    return {"regime": regime, "allocations": [a.model_dump() for a in allocs]}


@router.post("/optimize")
def optimize_allocation(body: dict):
    regime = body.get("regime", "Range")
    cash_available = body.get("cash_available", 50000)
    total_value = body.get("total_portfolio_value", 100000)
    opportunities = body.get("opportunities", [])

    allocs = get_strategy_allocation(regime)
    results = []
    for opp in opportunities:
        ticker = opp.get("ticker", "")
        score = opp.get("score", 50)
        strategy = opp.get("strategy", "swing")
        result = calculate_position_size(
            total_portfolio_value=total_value, cash_available=cash_available,
            kelly_fraction_value=settings.kelly_fraction,
            opportunity_score=score, strategy=strategy, regime=regime,
            existing_position_value=opp.get("existing_value", 0),
        )
        result.ticker = ticker
        results.append(result.model_dump())
    return {"regime": regime, "allocations": results, "strategy_limits": [a.model_dump() for a in allocs]}


@router.post("/opportunity-cost")
def opportunity_cost(body: dict):
    candidates = body.get("candidates", [])
    cash_available = body.get("cash_available", 0)
    total_value = body.get("total_portfolio_value", 0)
    existing = body.get("existing_positions")
    watchlist = body.get("watchlist")
    result = rank_opportunity_cost(candidates, cash_available, total_value, existing, watchlist)
    return result


@router.post("/replacements")
def replacements(body: dict):
    current_positions = body.get("current_positions", [])
    opportunity_scores = body.get("opportunity_scores", [])
    min_score_gap = body.get("min_score_gap", 10)
    result = find_replacements(current_positions, opportunity_scores, min_score_gap)
    return result.model_dump()


@router.post("/validate-trade")
def validate_trade_endpoint(body: dict):
    ticker = body.get("ticker", "")
    requested_size = body.get("requested_size", 0)
    sector = body.get("sector", "UNKNOWN")
    state = load_portfolio_state(settings.database_path)
    result = validate_trade(
        ticker=ticker.upper(), requested_size=requested_size,
        total_portfolio_value=state.total_value,
        cash_available=state.cash, sector=sector.upper(),
        sector_exposures=state.sector_exposures,
        current_delta=state.portfolio_delta_e,
    )
    return result.model_dump()
