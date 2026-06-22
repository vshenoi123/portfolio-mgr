import logging
import numpy as np
from datetime import datetime, timezone

from app.engines.strategy.service import select_strategy, rule_based_scores
from app.engines.data.service import PolygonDataService
from app.engines.data.ticker_details import get_ticker_details

logger = logging.getLogger(__name__)


def build_context_from_market_data(ticker: str) -> dict:
    """Build strategy context from real market data."""
    service = PolygonDataService()
    df = service.load_ohlcv(ticker, days=365)

    if df.empty or len(df) < 30:
        return _default_context(ticker)

    close = df["close"].values.astype(float)
    volume = df["volume"].values.astype(float) if "volume" in df.columns else np.ones(len(close))

    # Regime: use recent returns
    returns = np.diff(np.log(close[-60:])) if len(close) >= 60 else np.diff(np.log(close))
    mean_ret = float(np.mean(returns)) if len(returns) > 0 else 0.0
    if mean_ret > 0.001:
        regime = "Bull"
    elif mean_ret < -0.001:
        regime = "Bear"
    else:
        regime = "Range"

    # Momentum: 20-day return
    if len(close) >= 20:
        momentum = float((close[-1] / close[-20]) - 1)
    else:
        momentum = 0.0

    # Trend strength: ADX-like from recent closes
    if len(close) >= 20:
        diffs = np.diff(close[-20:])
        trend_strength = float(min(1.0, abs(np.mean(diffs)) / (np.std(diffs) + 1e-8)))
    else:
        trend_strength = 0.3

    # IV percentile: use historical volatility
    if len(returns) >= 20:
        hv_20 = float(np.std(returns[-20:]) * np.sqrt(252))
        hv_all = float(np.std(returns) * np.sqrt(252))
        iv_percentile = min(1.0, hv_20 / (hv_all + 1e-8))
    else:
        iv_percentile = 0.5

    # Drawdown from 52-week high
    if len(close) >= 20:
        peak = float(np.max(close[-252:]) if len(close) >= 252 else np.max(close))
        drawdown = float((peak - close[-1]) / peak)
    else:
        drawdown = 0.0

    # RSI
    if len(returns) >= 14:
        gains = np.where(returns[-14:] > 0, returns[-14:], 0)
        losses = np.where(returns[-14:] < 0, -returns[-14:], 0)
        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))
        rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 1e-8)))
    else:
        rsi = 50.0

    return {
        "ticker": ticker,
        "regime": regime,
        "momentum": round(momentum, 4),
        "trend_strength": round(trend_strength, 4),
        "iv_percentile": round(iv_percentile, 4),
        "put_skew": 0.1,
        "term_structure": 0.05,
        "drawdown": round(drawdown, 4),
        "days_to_expiry": 30,
        "rsi": round(rsi, 2),
        "underlying_price": float(close[-1]),
    }


def _default_context(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "regime": "Range",
        "momentum": 0.0,
        "trend_strength": 0.3,
        "iv_percentile": 0.5,
        "put_skew": 0.0,
        "term_structure": 0.0,
        "drawdown": 0.0,
        "days_to_expiry": 30,
        "rsi": 50.0,
        "underlying_price": 0.0,
    }


STRATEGY_MAP = {
    "sell_csp": "csp",
    "buy_leaps": "leaps",
    "pmcc": "pmcc",
    "covered_call": "covered_call",
    "buy_stock": "csp",  # fallback
}


def generate_trade(ticker: str, dte: int = 30, target_delta: float = 0.30) -> dict:
    """Full pipeline: market data -> strategy -> option generation."""
    context = build_context_from_market_data(ticker)
    strategy_output = select_strategy(context)
    recommendation = strategy_output.recommendation

    option_strategy = STRATEGY_MAP.get(recommendation)
    if not option_strategy or recommendation in ("close", "roll", "hold", "avoid"):
        return {
            "ticker": ticker,
            "strategy_output": strategy_output.model_dump(),
            "trade": None,
            "message": f"Recommendation is '{recommendation}' — no trade to generate",
        }

    underlying_price = context["underlying_price"]

    # Fetch live options chain from Polygon
    try:
        from app.engines.options.polygon_chain import fetch_chain_with_snapshots, find_nearest_contract

        contract_type = "put" if option_strategy in ("csp",) else "call"
        dte_min = max(7, dte - 10)
        dte_max = dte + 10

        live_contracts = fetch_chain_with_snapshots(ticker, contract_type, dte_min, dte_max, underlying_price=underlying_price)
        nearest = find_nearest_contract(live_contracts, target_delta) if live_contracts else None

        if not nearest or nearest.get("bid") is None:
            return {
                "ticker": ticker,
                "strategy_output": strategy_output.model_dump(),
                "trade": None,
                "message": f"Options data unavailable for {ticker} — no live contracts found with valid quotes",
                "context": {
                    "regime": context["regime"],
                    "momentum": context["momentum"],
                    "rsi": context["rsi"],
                    "iv_percentile": context["iv_percentile"],
                    "drawdown": context["drawdown"],
                },
            }

        nearest["underlying_price"] = underlying_price
        nearest["dte"] = dte

        trade = None
        if option_strategy == "csp":
            from app.engines.options.service import generate_csp_live
            trade = generate_csp_live(ticker, nearest)
        elif option_strategy == "leaps":
            from app.engines.options.service import generate_leaps_live
            trade = generate_leaps_live(ticker, nearest)
        elif option_strategy == "covered_call":
            from app.engines.options.service import generate_covered_call_live
            trade = generate_covered_call_live(ticker, nearest)

        if trade:
            trade.live_data = True

        return {
            "ticker": ticker,
            "strategy_output": strategy_output.model_dump(),
            "trade": trade.model_dump() if trade else None,
            "live_data": True,
            "context": {
                "regime": context["regime"],
                "momentum": context["momentum"],
                "rsi": context["rsi"],
                "iv_percentile": context["iv_percentile"],
                "drawdown": context["drawdown"],
            },
        }

    except Exception as e:
        logger.warning("Live options chain failed for %s: %s", ticker, e)
        return {
            "ticker": ticker,
            "strategy_output": strategy_output.model_dump(),
            "trade": None,
            "message": f"Options data unavailable for {ticker} — Polygon API error: {e}",
            "context": {
                "regime": context["regime"],
                "momentum": context["momentum"],
                "rsi": context["rsi"],
                "iv_percentile": context["iv_percentile"],
                "drawdown": context["drawdown"],
            },
        }
