"""Live options chain fetcher using Polygon API."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Callable

from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)

_SNAPSHOT_WORKERS = 10
_MAX_ROUNDS = 3
_STRIKE_RANGE = 0.20
_TARGET_LOW  = 0.20
_TARGET_HIGH = 0.40


def _get_client() -> RESTClient:
    return RESTClient(settings.polygon_api_key)


def fetch_option_chain(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
    limit: int = 250,
    strike_gte: float | None = None,
    strike_lte: float | None = None,
) -> list[dict]:
    """Fetch available option contracts within DTE and strike range."""
    client = _get_client()
    today = date.today()
    exp_gte = today + timedelta(days=dte_min)
    exp_lte = today + timedelta(days=dte_max)

    try:
        params = dict(
            underlying_ticker=ticker,
            contract_type=contract_type,
            expiration_date_gte=exp_gte.isoformat(),
            expiration_date_lte=exp_lte.isoformat(),
            limit=limit,
            sort="strike_price",
            order="asc",
        )
        if strike_gte is not None:
            params["strike_price_gte"] = strike_gte
        if strike_lte is not None:
            params["strike_price_lte"] = strike_lte

        contracts = client.list_options_contracts(**params)
        result = []
        for c in contracts:
            exp_date = date.fromisoformat(c.expiration_date)
            dte = (exp_date - today).days
            result.append({
                "ticker": c.ticker,
                "strike": c.strike_price,
                "type": c.contract_type,
                "expiration_date": c.expiration_date,
                "dte": dte,
            })
        return result
    except Exception as e:
        logger.warning("Failed to fetch option chain for %s: %s", ticker, e)
        return []


def fetch_chain_snapshot(ticker: str, option_ticker: str) -> dict | None:
    """Fetch live snapshot for a single option contract."""
    client = _get_client()
    try:
        snap = client.get_snapshot_option(ticker, option_ticker)
        if snap is None:
            return None
        greeks = snap.greeks
        quote = snap.last_quote
        trade = snap.last_trade
        return {
            "iv": snap.implied_volatility,
            "delta": greeks.delta if greeks else None,
            "gamma": greeks.gamma if greeks else None,
            "theta": greeks.theta if greeks else None,
            "vega": greeks.vega if greeks else None,
            "bid": quote.bid if quote else None,
            "ask": quote.ask if quote else None,
            "midpoint": quote.midpoint if quote else None,
            "last_price": trade.price if trade else None,
            "volume": int(trade.size) if trade and trade.size else 0,
            "open_interest": int(snap.open_interest) if snap.open_interest else 0,
            "break_even": snap.break_even_price,
            "underlying_price": snap.underlying_asset.price if snap.underlying_asset else None,
        }
    except Exception as e:
        logger.warning("Failed to fetch snapshot for %s: %s", option_ticker, e)
        return None


def _snapshot_contracts(ticker: str, contracts: list[dict]) -> list[dict]:
    """Fetch snapshots for all contracts concurrently. Returns enriched contracts."""
    if not contracts:
        return []
    out = [None] * len(contracts)
    with ThreadPoolExecutor(max_workers=_SNAPSHOT_WORKERS) as pool:
        fut_map = {
            pool.submit(fetch_chain_snapshot, ticker, c["ticker"]): i
            for i, c in enumerate(contracts)
        }
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            snap = fut.result()
            if snap:
                out[idx] = {**contracts[idx], **snap}
            else:
                out[idx] = {**contracts[idx], "iv": None, "bid": None, "ask": None}
    return [c for c in out if c]


def fetch_chain_with_snapshots(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
    underlying_price: float | None = None,
) -> list[dict]:
    """Fetch option contracts with live snapshots. Adaptive strike range search.

    Starts at ±20% of underlying_price, expands outward if target delta
    (0.20–0.40) not found. Max 3 rounds.
    """
    if not underlying_price:
        fallback = fetch_option_chain(ticker, contract_type, dte_min, dte_max, limit=50)
        logger.info("No underlying price — fetching first 50 contracts for %s", ticker)
        return _snapshot_contracts(ticker, fallback)

    lower = underlying_price * (1 - _STRIKE_RANGE)
    upper = underlying_price * (1 + _STRIKE_RANGE)
    seen_tickers: set[str] = set()
    merged: dict[str, dict] = {}

    for round_num in range(1, _MAX_ROUNDS + 1):
        contracts = fetch_option_chain(
            ticker, contract_type, dte_min, dte_max,
            strike_gte=lower, strike_lte=upper,
        )
        # Skip contracts already fetched in prior rounds
        new_contracts = [c for c in contracts if c["ticker"] not in seen_tickers]
        if not new_contracts:
            break

        for c in contracts:
            seen_tickers.add(c["ticker"])

        enriched = _snapshot_contracts(ticker, new_contracts)
        for c in enriched:
            merged[c["ticker"]] = c

        # Check if we found the target delta
        valid_deltas = [c for c in merged.values() if c.get("delta") is not None]
        if valid_deltas:
            min_d = min(abs(c["delta"]) for c in valid_deltas)
            max_d = max(abs(c["delta"]) for c in valid_deltas)
            if min_d <= _TARGET_HIGH and max_d >= _TARGET_LOW:
                # Target delta range is covered
                logger.info("Round %d/%d — target delta found (%s)", round_num, _MAX_ROUNDS, ticker)
                break

            if round_num < _MAX_ROUNDS:
                # Expand in the direction of the delta gap
                if min_d > _TARGET_HIGH:
                    # All fetched deltas are too high (ITM) — need lower strikes
                    lower_val = min(c["strike"] for c in valid_deltas)
                    lower = lower_val * (1 - _STRIKE_RANGE)
                    logger.info("Round %d/%d — deltas too high (%.2f-%.2f), expanding lower to %.0f",
                                round_num, _MAX_ROUNDS, min_d, max_d, lower)
                elif max_d < _TARGET_LOW:
                    # All fetched deltas are too low (OTM) — need higher strikes
                    upper_val = max(c["strike"] for c in valid_deltas)
                    upper = upper_val * (1 + _STRIKE_RANGE)
                    logger.info("Round %d/%d — deltas too low (%.2f-%.2f), expanding upper to %.0f",
                                round_num, _MAX_ROUNDS, min_d, max_d, upper)

    result = list(merged.values())
    valid = [c for c in result if c.get("delta") is not None]
    logger.info("Fetched %d contracts (%d with delta) for %s",
                len(result), len(valid), ticker)
    return result


def find_nearest_contract(contracts: list[dict], target_delta: float = 0.30) -> dict | None:
    """Find the contract with delta closest to target_delta."""
    valid = [c for c in contracts if c.get("delta") is not None]
    if not valid:
        return None
    return min(valid, key=lambda c: abs(abs(c["delta"]) - abs(target_delta)))
