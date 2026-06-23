import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

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
            timeout=5,
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


def _fetch_ticker_details(ticker: str) -> tuple[str, dict | None]:
    """Fetch name, exchange, type, market_cap for a single ticker (1 API call)."""
    try:
        resp = requests.get(
            f"https://api.polygon.io/v3/reference/tickers/{ticker}",
            params={"apiKey": settings.polygon_api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return ticker, None
        data = resp.json()
        r = data.get("results", {})
        raw_exchange = r.get("primary_exchange", "")
        raw_type = r.get("type", "")
        info = {
            "ticker": ticker,
            "name": r.get("name", "") or "",
            "type": "etf" if raw_type == "ETF" else "stock",
            "exchange": EXCHANGE_NAMES.get(raw_exchange, raw_exchange),
            "market_cap": float(r["market_cap"]) if r.get("market_cap") else 0,
            "sic_code": int(r.get("sic_code") or 0),
            "active": True,
        }
        return ticker, info
    except Exception:
        return ticker, None


def refresh_ticker_details() -> int:
    """Fetch all ticker metadata from Polygon via batch get_ticker_details (1 pass)."""
    global _cache
    try:
        from app.models.universe import get_universe
        ticker_list = get_universe()
        if not ticker_list:
            logger.warning("Universe is empty, cannot refresh ticker details")
            return 0

        details = {}
        logger.info("Fetching ticker details for %d tickers (1 pass, concurrent)", len(ticker_list))
        with ThreadPoolExecutor(max_workers=20) as pool:
            fut_map = {pool.submit(_fetch_ticker_details, t): t for t in ticker_list}
            for fut in as_completed(fut_map):
                ticker, info = fut.result()
                if info:
                    details[ticker] = info

        _cache = details
        _save_cache(details)
        filled = sum(1 for d in details.values() if d["market_cap"] > 0)
        logger.info("Refreshed %d/%d tickers (market_cap: %d populated)", len(details), len(ticker_list), filled)
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
    if "sic_code" in df.columns:
        df["sic_code"] = pd.to_numeric(df["sic_code"], errors="coerce").fillna(0).astype(int)
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
