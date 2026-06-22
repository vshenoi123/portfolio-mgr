import os
import logging
from datetime import datetime, timezone

import pandas as pd
from polygon import RESTClient

from app.config import settings
from app.database import get_data_dir

logger = logging.getLogger(__name__)

EXCHANGE_NAMES = {
    "XNAS": "NASDAQ",
    "XNYS": "NYSE",
    "ARCX": "NYSE Arca",
    "BATS": "Cboe BZX",
    "EDGX": "Cboe EDGX",
    "EDGA": "Cboe EDGA",
    "IEX": "IEX",
    "MEMX": "MEMX",
    "NYSE": "NYSE",
    "NASDAQ": "NASDAQ",
    "OTC": "OTC",
}

_cache: dict[str, dict] | None = None


def get_ticker_details(tickers: list[str] | None = None) -> dict[str, dict]:
    """Get ticker details with live prices from Polygon snapshots."""
    global _cache
    if _cache is None:
        _cache = _load_cache()

    result = {}
    for t in (tickers or []):
        info = dict(_cache.get(t, {}))
        result[t] = info

    # Fetch live prices from Polygon snapshots
    if tickers:
        live_prices = _fetch_live_prices(tickers)
        for t in tickers:
            if t in live_prices:
                result[t]["last_price"] = live_prices[t]

    if not tickers:
        return _cache
    return result


def _fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest prices from Polygon snapshot API."""
    prices = {}
    try:
        client = RESTClient(settings.polygon_api_key)
        for ticker in tickers:
            try:
                snap = client.get_snapshot_ticker("stocks", ticker)
                if snap and snap.last_trade and snap.last_trade.price:
                    prices[ticker.upper()] = snap.last_trade.price
                elif snap and snap.day and snap.day.close:
                    prices[ticker.upper()] = snap.day.close
            except Exception:
                pass
    except Exception as e:
        logger.warning("Failed to fetch live prices: %s", e)
    return prices


def refresh_ticker_details() -> int:
    """Fetch ticker details from Polygon API and cache them."""
    global _cache
    try:
        client = RESTClient(settings.polygon_api_key)
        details = {}

        # Fetch stocks
        stock_resp = client.list_tickers(market="stocks", type="CS", active=True, limit=1000)
        for t in stock_resp:
            raw_exchange = t.primary_exchange or ""
            d = {
                "ticker": t.ticker.upper(),
                "name": t.name or "",
                "type": "stock",
                "exchange": EXCHANGE_NAMES.get(raw_exchange, raw_exchange),
                "active": t.active if t.active is not None else True,
            }
            if hasattr(t, "market_cap") and t.market_cap:
                d["market_cap"] = t.market_cap
            else:
                d["market_cap"] = 0
            details[t.ticker.upper()] = d

        # Fetch ETFs
        etf_resp = client.list_tickers(market="stocks", type="ETF", active=True, limit=500)
        for t in etf_resp:
            raw_exchange = t.primary_exchange or ""
            details[t.ticker.upper()] = {
                "ticker": t.ticker.upper(),
                "name": t.name or "",
                "type": "etf",
                "exchange": EXCHANGE_NAMES.get(raw_exchange, raw_exchange),
                "market_cap": 0,
                "active": t.active if t.active is not None else True,
            }

        _cache = details
        _save_cache(details)
        logger.info("Refreshed ticker details for %d tickers", len(details))
        return len(details)
    except Exception as e:
        logger.error("Failed to refresh ticker details: %s", e)
        return 0


def _save_cache(details: dict[str, dict]) -> None:
    data_dir = get_data_dir()
    cache_dir = os.path.join(data_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "ticker_details.parquet")
    df = pd.DataFrame(details.values())
    df.to_parquet(path, index=False)


def _load_cache() -> dict[str, dict]:
    data_dir = get_data_dir()
    path = os.path.join(data_dir, "cache", "ticker_details.parquet")
    if os.path.exists(path):
        try:
            df = pd.read_parquet(path)
            return {row["ticker"]: row for _, row in df.iterrows()}
        except Exception:
            pass
    return {}
