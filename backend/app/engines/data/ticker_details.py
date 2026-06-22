import os
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
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
    """Get ticker details with live prices from Polygon bulk snapshot."""
    global _cache
    if _cache is None:
        _cache = _load_cache()
    if not _cache:
        logger.info("Ticker details cache is empty, refreshing from Polygon API")
        refresh_ticker_details()

    result = {}
    for t in (tickers or []):
        info = dict(_cache.get(t, {}))
        result[t] = info

    if tickers:
        live_prices = _fetch_live_prices(tickers)
        for t in tickers:
            if t in live_prices:
                result[t]["last_price"] = live_prices[t]

    if not tickers:
        return _cache
    return result


def _fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest prices from Polygon bulk snapshot API (1 call)."""
    prices = {}
    try:
        resp = requests.get(
            "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"apiKey": settings.polygon_api_key},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning("Bulk snapshot API returned %d", resp.status_code)
            return prices
        data = resp.json()
        ticker_set = set(t.upper() for t in tickers)
        for t in data.get("tickers", []):
            ticker = t.get("ticker", "").upper()
            if ticker not in ticker_set:
                continue
            lt = t.get("lastTrade") or {}
            day = t.get("day") or {}
            price = lt.get("p") or day.get("c")
            if price:
                prices[ticker] = float(price)
    except Exception as e:
        logger.warning("Failed to fetch live prices: %s", e)
    return prices


def _fetch_market_cap(ticker: str) -> tuple[str, float | None]:
    """Fetch market_cap for a single ticker via REST API."""
    try:
        resp = requests.get(
            f"https://api.polygon.io/v3/reference/tickers/{ticker}",
            params={"apiKey": settings.polygon_api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return ticker, None
        data = resp.json()
        results = data.get("results", {})
        mc = results.get("market_cap")
        return ticker, mc
    except Exception:
        return ticker, None


def refresh_ticker_details() -> int:
    """Fetch ticker details from Polygon API and cache them (no caps)."""
    global _cache
    try:
        client = RESTClient(settings.polygon_api_key)
        details = {}

        for t in client.list_tickers(market="stocks", type="CS", active=True, limit=1000):
            raw_exchange = t.primary_exchange or ""
            details[t.ticker.upper()] = {
                "ticker": t.ticker.upper(),
                "name": t.name or "",
                "type": "stock",
                "exchange": EXCHANGE_NAMES.get(raw_exchange, raw_exchange),
                "active": t.active if t.active is not None else True,
                "market_cap": 0,
            }

        for t in client.list_tickers(market="stocks", type="ETF", active=True, limit=1000):
            raw_exchange = t.primary_exchange or ""
            details[t.ticker.upper()] = {
                "ticker": t.ticker.upper(),
                "name": t.name or "",
                "type": "etf",
                "exchange": EXCHANGE_NAMES.get(raw_exchange, raw_exchange),
                "active": t.active if t.active is not None else True,
                "market_cap": 0,
            }

        ticker_list = list(details.keys())
        logger.info("Fetching market_cap for %d tickers", len(ticker_list))
        with ThreadPoolExecutor(max_workers=10) as pool:
            fut_map = {pool.submit(_fetch_market_cap, t): t for t in ticker_list}
            for fut in as_completed(fut_map):
                ticker, mc = fut.result()
                if mc is not None:
                    details[ticker]["market_cap"] = float(mc)

        filled = sum(1 for d in details.values() if d["market_cap"] > 0)
        logger.info("Market cap populated: %d/%d tickers", filled, len(details))

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
