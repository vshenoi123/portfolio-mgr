"""Live options chain fetcher using Polygon API."""

import logging
from datetime import date, timedelta

from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> RESTClient:
    return RESTClient(settings.polygon_api_key)


def fetch_option_chain(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
    limit: int = 250,
) -> list[dict]:
    """Fetch available option contracts for a ticker within DTE range."""
    client = _get_client()
    today = date.today()
    exp_gte = today + timedelta(days=dte_min)
    exp_lte = today + timedelta(days=dte_max)

    try:
        contracts = client.list_options_contracts(
            underlying_ticker=ticker,
            contract_type=contract_type,
            expiration_date_gte=exp_gte.isoformat(),
            expiration_date_lte=exp_lte.isoformat(),
            limit=limit,
            sort="strike_price",
            order="asc",
        )
        result = []
        for c in contracts:
            exp_date = date.fromisoformat(c.expiration_date)
            dte = (exp_date - today).days
            result.append(
                {
                    "ticker": c.ticker,
                    "strike": c.strike_price,
                    "type": c.contract_type,
                    "expiration_date": c.expiration_date,
                    "dte": dte,
                }
            )
        logger.info(
            "Fetched %d %s contracts for %s (DTE %d-%d)",
            len(result),
            contract_type,
            ticker,
            dte_min,
            dte_max,
        )
        return result
    except Exception as e:
        logger.warning("Failed to fetch option chain for %s: %s", ticker, e)
        return []


def fetch_chain_snapshot(
    ticker: str,
    option_ticker: str,
) -> dict | None:
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
            "underlying_price": snap.underlying_asset.price
            if snap.underlying_asset
            else None,
        }
    except Exception as e:
        logger.warning("Failed to fetch snapshot for %s: %s", option_ticker, e)
        return None


def fetch_chain_with_snapshots(
    ticker: str,
    contract_type: str = "put",
    dte_min: int = 20,
    dte_max: int = 45,
) -> list[dict]:
    """Fetch option contracts with live snapshots in batch."""
    contracts = fetch_option_chain(ticker, contract_type, dte_min, dte_max)
    if not contracts:
        return []

    result = []
    for c in contracts:
        snap = fetch_chain_snapshot(ticker, c["ticker"])
        if snap:
            result.append({**c, **snap})
        else:
            result.append({**c, "iv": None, "bid": None, "ask": None})

    logger.info(
        "Fetched snapshots for %d/%d contracts for %s",
        len(result),
        len(contracts),
        ticker,
    )
    return result


def find_nearest_contract(
    contracts: list[dict],
    target_delta: float = 0.30,
) -> dict | None:
    """Find the contract with delta closest to target_delta."""
    valid = [c for c in contracts if c.get("delta") is not None]
    if not valid:
        return None
    return min(valid, key=lambda c: abs(abs(c["delta"]) - abs(target_delta)))
