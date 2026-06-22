import logging
from pydantic import BaseModel, field_validator
from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV",
    "XLI", "XLP", "XLU", "XLB", "XLRE", "XLY",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "JNJ", "WMT", "MA", "PG", "UNH", "HD", "BAC",
    "DIS", "ADBE", "NFLX", "CRM", "KO", "PEP", "MRK", "ABBV",
    "AVGO", "CSCO", "INTC", "AMD", "QCOM", "TMO", "ACN", "TXN",
    "NKE", "UPS", "BA", "CAT", "GS", "MS", "C", "WFC",
    "ORCL", "IBM", "PYPL", "SNAP", "UBER", "SQ", "SHOP",
    "ARKK", "TLT", "HYG", "GDX", "SLV", "USO",
]


def fetch_universe_from_polygon(
    tickers_per_type: int = 100,
    min_market_cap: float = 1e9,
) -> list[str]:
    """Fetch active stock and ETF tickers from Polygon API."""
    try:
        client = RESTClient(settings.polygon_api_key)
        tickers = set()

        # Fetch active stocks — sort by volume (valid sort field), filter by market cap
        stock_resp = client.list_tickers(
            market="stocks",
            type="CS",
            active=True,
            limit=tickers_per_type,
            sort="volume",
            order="desc",
        )
        for t in stock_resp:
            if hasattr(t, "market_cap") and t.market_cap and t.market_cap >= min_market_cap:
                tickers.add(t.ticker.upper())

        # Fetch active ETFs
        etf_resp = client.list_tickers(
            market="stocks",
            type="ETF",
            active=True,
            limit=tickers_per_type,
        )
        for t in etf_resp:
            tickers.add(t.ticker.upper())

        result = sorted(tickers)
        logger.info("Fetched %d tickers from Polygon API", len(result))
        return result
    except Exception as e:
        logger.warning("Failed to fetch from Polygon, using default universe: %s", e)
        return DEFAULT_UNIVERSE


def get_universe(use_api: bool = False) -> list[str]:
    """Get ticker universe. Use API if requested, fallback to default."""
    if use_api:
        return fetch_universe_from_polygon()
    return DEFAULT_UNIVERSE


class UniverseEntry(BaseModel):
    ticker: str
    active: bool = True

    @field_validator("ticker")
    @classmethod
    def ticker_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ticker cannot be empty")
        return v.upper().strip()