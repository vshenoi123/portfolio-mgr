import os
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
from polygon import RESTClient

from app.config import settings

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.ERROR)


class PolygonAPIError(Exception):
    pass


polygon_client = RESTClient(settings.polygon_api_key)


class PolygonDataService:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or settings.data_dir
        self.client = polygon_client

    def _ensure_parquet_dir(self, ticker: str, data_type: str = "ohlcv") -> str:
        path = os.path.join(self.data_dir, "market_data", data_type, ticker.lower())
        os.makedirs(path, exist_ok=True)
        return path

    def fetch_ohlcv(
        self,
        ticker: str,
        days: int = 365,
        multiplier: int = 1,
        timespan: str = "day",
    ) -> list[dict]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        try:
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=multiplier,
                timespan=timespan,
                from_=start.strftime("%Y-%m-%d"),
                to=end.strftime("%Y-%m-%d"),
                adjusted=True,
            )
        except Exception as e:
            raise PolygonAPIError(f"Failed to fetch {ticker}: {e}") from e

        bars = []
        for agg in aggs:
            bars.append({
                "ticker": ticker.upper(),
                "timestamp": datetime.fromtimestamp(agg.t / 1000, tz=timezone.utc),
                "open": agg.o,
                "high": agg.h,
                "low": agg.l,
                "close": agg.c,
                "volume": agg.v,
                "vwap": agg.vw if hasattr(agg, "vw") else None,
                "trades": agg.n if hasattr(agg, "n") else None,
            })
        return bars

    def save_ohlcv(self, bars: list[dict]) -> str:
        if not bars:
            raise ValueError("No bars to save")
        df = pd.DataFrame(bars)
        ticker = bars[0]["ticker"]
        parquet_dir = self._ensure_parquet_dir(ticker, "ohlcv")
        parquet_path = os.path.join(parquet_dir, f"{ticker.lower()}.parquet")
        if os.path.exists(parquet_path):
            existing = pd.read_parquet(parquet_path)
            df = pd.concat([existing, df], ignore_index=True)
            df = df.drop_duplicates(subset=["ticker", "timestamp"]).sort_values("timestamp").reset_index(drop=True)
        df.to_parquet(parquet_path, index=False)
        logger.info("Saved %d bars for %s to %s", len(bars), ticker, parquet_path)
        return parquet_path

    def load_ohlcv(
        self,
        ticker: str,
        days: int = 365,
    ) -> pd.DataFrame:
        parquet_dir = self._ensure_parquet_dir(ticker, "ohlcv")
        parquet_path = os.path.join(parquet_dir, f"{ticker.lower()}.parquet")
        if not os.path.exists(parquet_path):
            return pd.DataFrame()
        df = pd.read_parquet(parquet_path)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        df = df[df["timestamp"] >= cutoff]
        return df.sort_values("timestamp").reset_index(drop=True)
