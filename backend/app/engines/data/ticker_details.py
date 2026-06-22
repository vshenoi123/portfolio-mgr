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
    """Get ticker details (name, type, exchange, market_cap, last_price) from cache."""
    global _cache
    if _cache is None:
        _cache = _load_cache()

    result = {}
    for t in (tickers or []):
        info = dict(_cache.get(t, {}))
        if "last_price" not in info or info["last_price"] is None:
            info["last_price"] = _get_last_price(t)
        result[t] = info
    if not tickers:
        return _cache
    return result


def _get_last_price(ticker: str) -> float | None:
    """Read last close price from stored OHLCV Parquet."""
    from app.database import get_data_dir
    parquet_path = os.path.join(get_data_dir(), "ohlcv", ticker.lower()[:1], f"{ticker.lower()}.parquet")
    if not os.path.exists(parquet_path):
        # Try flat structure
        parquet_path = os.path.join(get_data_dir(), "ohlcv", f"{ticker.lower()}.parquet")
    if not os.path.exists(parquet_path):
        return None
    try:
        df = pd.read_parquet(parquet_path)
        if df.empty or "close" not in df.columns:
            return None
        return float(df["close"].iloc[-1])
    except Exception:
        return None


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
