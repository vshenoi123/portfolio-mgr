import json
import numpy as np
import duckdb
from datetime import datetime, timezone
from app.engines.portfolio.schemas import (
    PortfolioState, PortfolioPosition, PortfolioImpactScore, CorrelationPair
)

_SECTOR_MAP = {
    "AAPL": "TECHNOLOGY", "MSFT": "TECHNOLOGY", "NVDA": "TECHNOLOGY",
    "GOOGL": "TECHNOLOGY", "AMZN": "CONSUMER_CYCLICAL", "META": "TECHNOLOGY",
    "TSLA": "AUTOMOTIVE", "BRK.B": "FINANCIAL", "JPM": "FINANCIAL",
    "V": "FINANCIAL", "JNJ": "HEALTHCARE", "WMT": "CONSUMER_DEFENSIVE",
    "MA": "FINANCIAL", "PG": "CONSUMER_DEFENSIVE", "UNH": "HEALTHCARE",
    "HD": "CONSUMER_CYCLICAL", "BAC": "FINANCIAL", "DIS": "ENTERTAINMENT",
    "ADBE": "TECHNOLOGY", "CRM": "TECHNOLOGY", "NFLX": "ENTERTAINMENT",
    "CMCSA": "ENTERTAINMENT", "PFE": "HEALTHCARE", "TMO": "HEALTHCARE",
    "XOM": "ENERGY", "CVX": "ENERGY", "DOW": "BASIC_MATERIALS",
    "SPY": "ETF", "QQQ": "ETF", "IWM": "ETF",
}

_SECTOR_DEFAULT = "UNKNOWN"


def _get_sector_for_ticker(ticker: str) -> str:
    return _SECTOR_MAP.get(ticker.upper(), _SECTOR_DEFAULT)


def load_portfolio_state(db_path: str) -> PortfolioState:
    conn = duckdb.connect(db_path)
    try:
        positions_raw = conn.execute(
            "SELECT ticker, quantity, avg_price, current_price, beta, delta, "
            "gamma, theta, vega, sector, strategy_type FROM positions WHERE quantity != 0"
        ).fetchall()
        pos_cols = ["ticker", "quantity", "avg_price", "current_price", "beta", "delta",
                     "gamma", "theta", "vega", "sector", "strategy_type"]

        positions = []
        total_equity = 0.0
        sector_exposures: dict[str, float] = {}

        for row in positions_raw:
            p = dict(zip(pos_cols, row))
            pos = PortfolioPosition(
                ticker=p["ticker"], quantity=float(p["quantity"]),
                avg_price=float(p["avg_price"]), current_price=float(p["current_price"]),
                beta=float(p["beta"]), delta=float(p["delta"]),
                gamma=float(p["gamma"]), theta=float(p["theta"]),
                vega=float(p["vega"]), sector=str(p["sector"] or _get_sector_for_ticker(p["ticker"])),
                strategy_type=str(p["strategy_type"]),
            )
            positions.append(pos)
            total_equity += pos.market_value
            sector_exposures[pos.sector] = sector_exposures.get(pos.sector, 0) + pos.market_value

        options_raw = conn.execute(
            "SELECT ticker, option_type, strike, expiration, quantity, market_value, "
            "delta, gamma, theta, vega, implied_vol, dte, strategy_type, status "
            "FROM options_positions WHERE status = 'open'"
        ).fetchall()

        total_options = 0.0
        options_list = []
        for row in options_raw:
            opts = {
                "ticker": row[0], "option_type": row[1], "strike": float(row[2]),
                "expiration": str(row[3]), "quantity": row[4],
                "market_value": float(row[5]), "delta": float(row[6]),
                "gamma": float(row[7]), "theta": float(row[8]), "vega": float(row[9]),
                "implied_vol": float(row[10]), "dte": row[11],
                "strategy_type": row[12], "status": row[13],
            }
            options_list.append(opts)
            total_options += float(row[5])

        snapshots = conn.execute(
            "SELECT total_value, cash FROM portfolio_snapshots ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        total_value = float(snapshots[0]) if snapshots else total_equity + total_options
        cash = float(snapshots[1]) if snapshots else 0.0

        portfolio_beta = compute_portfolio_beta(positions, total_equity)
        portfolio_delta = compute_portfolio_delta(positions, options_list)

        return PortfolioState(
            total_value=total_value, cash=cash,
            equity_value=round(total_equity, 2),
            options_value=round(total_options, 2),
            num_positions=len(positions), num_options=len(options_list),
            positions=[p.model_dump() for p in positions],
            options_positions=options_list,
            sector_exposures={k: round(v / total_value * 100, 2) if total_value > 0 else 0
                             for k, v in sector_exposures.items()},
            portfolio_beta=round(portfolio_beta, 4),
            portfolio_delta_e=round(portfolio_delta, 2),
        )
    finally:
        conn.close()


def calculate_portfolio_impact(
    ticker: str, raw_score: float, positions: list[dict],
    sector_exposures: dict, total_value: float, cash: float,
    correlation_matrix: dict | None = None,
) -> PortfolioImpactScore:
    factors = []
    adjusted = float(raw_score)

    # Sector concentration penalty
    sector = _get_sector_for_ticker(ticker)
    sector_pct = sector_exposures.get(sector, 0.0)
    if sector_pct > 25:
        penalty = min(15, (sector_pct - 25) * 1.5)
        adjusted -= penalty
        factors.append({"name": "sector_concentration", "impact": -penalty,
                        "detail": f"{sector} at {sector_pct:.1f}%"})
    elif sector_pct > 35:
        penalty = min(20, (sector_pct - 35) * 2.0)
        adjusted -= penalty
        factors.append({"name": "sector_overweight", "impact": -penalty,
                        "detail": f"{sector} severely overweight at {sector_pct:.1f}%"})

    # Existing position penalty
    existing = next((p for p in positions if p["ticker"] == ticker.upper()), None)
    if existing:
        weight = existing.get("weight_pct", 0)
        if weight > 10:
            penalty = min(10, (weight - 10) * 0.8)
            adjusted -= penalty
            factors.append({"name": "existing_position", "impact": -penalty,
                            "detail": f"Already hold {weight:.1f}% portfolio weight"})

    # Correlation penalty
    if correlation_matrix and ticker.upper() in correlation_matrix:
        corrs = correlation_matrix[ticker.upper()]
        high_corr = [(t, c) for t, c in corrs.items() if c >= 0.70 and t != ticker.upper()]
        for t, c in high_corr:
            if any(p["ticker"] == t for p in positions):
                penalty = min(10, (c - 0.70) * 20)
                adjusted -= penalty
                factors.append({"name": "correlation", "impact": -penalty,
                                "detail": f"High correlation ({c:.2f}) with held {t}"})

    # Cash reserve bonus
    cash_pct = (cash / total_value * 100) if total_value > 0 else 0
    if cash_pct >= 25:
        bonus = min(5, (cash_pct - 25) * 0.3)
        adjusted += bonus
        factors.append({"name": "cash_reserve", "impact": bonus,
                        "detail": f"Healthy cash reserve at {cash_pct:.1f}%"})

    # Concentration penalty
    top5_pct = _compute_top_holdings_pct(positions, total_value)
    if top5_pct > 70:
        penalty = min(15, (top5_pct - 70) * 0.8)
        adjusted -= penalty
        factors.append({"name": "portfolio_concentration", "impact": -penalty,
                        "detail": f"Top 5 holdings at {top5_pct:.1f}%"})

    adjusted = max(0, min(100, adjusted))
    return PortfolioImpactScore(ticker=ticker, raw_opportunity_score=raw_score,
                                adjusted_score=round(adjusted, 2), impact_factors=factors)


def compute_portfolio_beta(positions: list, total_equity_value: float) -> float:
    if total_equity_value <= 0 or not positions:
        return 0.0
    total = sum(p.market_value * p.beta for p in positions)
    return total / total_equity_value


def compute_portfolio_delta(positions: list, options_positions: list) -> float:
    total = 0.0
    for p in positions:
        total += p.market_value * p.delta
    for o in options_positions:
        total += o.get("market_value", 0) * o.get("delta", 0)
    return total


def compute_concentration(positions: list, total_value: float) -> float:
    if total_value <= 0 or not positions:
        return 0.0
    sorted_pos = sorted(positions, key=lambda p: p.market_value, reverse=True)
    top5_value = sum(p.market_value for p in sorted_pos[:5])
    return round(top5_value / total_value * 100, 2)


def _compute_top_holdings_pct(positions: list[dict], total_value: float) -> float:
    if total_value <= 0 or not positions:
        return 0.0
    sorted_pos = sorted(positions, key=lambda p: p.get("market_value", 0), reverse=True)
    top5_value = sum(p.get("market_value", 0) for p in sorted_pos[:5])
    return round(top5_value / total_value * 100, 2)


def compute_correlation_matrix(returns: dict[str, np.ndarray]) -> dict:
    if len(returns) < 2:
        data = {}
        for k in returns:
            data[k] = {k: 1.0}
        return data

    tickers = list(returns.keys())
    min_len = min(len(v) for v in returns.values())
    aligned = np.array([returns[t][:min_len] for t in tickers])
    corr = np.corrcoef(aligned)
    result = {}
    for i, t1 in enumerate(tickers):
        result[t1] = {}
        for j, t2 in enumerate(tickers):
            result[t1][t2] = round(float(corr[i, j]), 4)
    return result
