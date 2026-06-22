import logging
from pydantic import BaseModel, field_validator
from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)

_cached_universe: list[str] | None = None


def fetch_universe_from_polygon() -> list[str]:
    """Fetch all active stock and ETF tickers from Polygon API (no cap)."""
    global _cached_universe
    try:
        client = RESTClient(settings.polygon_api_key)
        tickers = set()

        for t in client.list_tickers(market="stocks", type="CS", active=True, limit=1000):
            tickers.add(t.ticker.upper())

        for t in client.list_tickers(market="stocks", type="ETF", active=True, limit=1000):
            tickers.add(t.ticker.upper())

        result = sorted(tickers)
        logger.info("Fetched %d tickers from Polygon API", len(result))
        _cached_universe = result
        return result
    except Exception as e:
        logger.warning("Failed to fetch from Polygon: %s", e)
        return []


def get_universe() -> list[str]:
    """Get ticker universe from Polygon API (cached). Returns empty list if unavailable."""
    global _cached_universe
    if _cached_universe:
        return _cached_universe
    return fetch_universe_from_polygon()


class UniverseEntry(BaseModel):
    ticker: str
    active: bool = True

    @field_validator("ticker")
    @classmethod
    def ticker_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ticker cannot be empty")
        return v.upper().strip()
