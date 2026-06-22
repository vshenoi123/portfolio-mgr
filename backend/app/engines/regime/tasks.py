import logging
import os
from datetime import datetime, timezone

import pandas as pd
from celery import shared_task

from app.engines.data.service import PolygonDataService
from app.engines.regime.service import full_regime_analysis
from app.database import get_data_dir

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_regime(self, ticker: str = "SPY", n_states: int = 4, lookback_days: int = 756) -> dict:
    service = PolygonDataService()
    try:
        df = service.load_ohlcv(ticker, days=lookback_days)
        if df.empty:
            return {"ticker": ticker, "status": "error", "message": f"No data for {ticker}"}

        returns = df["close"].pct_change().dropna()
        analysis = full_regime_analysis(returns, n_states=n_states)
        _save_regime(ticker, analysis)

        logger.info("Regime for %s: %s", ticker, analysis["overall_regime"].regime)
        return {
            "ticker": ticker,
            "status": "success",
            "regime": analysis["overall_regime"].regime,
            "probability": analysis["overall_regime"].probability,
            "confidence": analysis["overall_regime"].confidence,
            "message": analysis["overall_regime"].explanation,
        }
    except Exception as e:
        logger.exception("Failed to compute regime for %s", ticker)
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_regimes(n_states: int = 4, lookback_days: int = 756) -> list[dict]:
    from app.models.universe import get_universe
    results = []
    for ticker in get_universe():
        result = compute_regime.delay(ticker, n_states=n_states, lookback_days=lookback_days)
        results.append(result)
    return results


def _save_regime(ticker: str, analysis: dict) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = os.path.join(data_dir, "signals", "regime")
    os.makedirs(signals_dir, exist_ok=True)
    pred = analysis["overall_regime"]
    row = {
        "ticker": ticker, "date": date_str,
        "regime": pred.regime, "probability": pred.probability,
        "confidence": pred.confidence, "explanation": pred.explanation,
        **analysis["state_probabilities"],
        "trained_on_bars": analysis["trained_on_bars"],
    }
    path = os.path.join(signals_dir, f"{date_str}.parquet")
    pd.DataFrame([row]).to_parquet(path, index=False)
    return path
