import logging
from celery import shared_task
from app.engines.strategy.service import select_strategy

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_strategy(self, ticker: str, signals: dict) -> dict:
    try:
        context = {"ticker": ticker, **signals}
        output = select_strategy(context)
        return {"ticker": ticker, "status": "success",
            "recommendation": output.recommendation,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "risk_assessment": output.risk_assessment}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "message": str(e)}


@shared_task
def compute_all_strategies() -> list[dict]:
    from app.models.universe import DEFAULT_UNIVERSE
    results = []
    for ticker in DEFAULT_UNIVERSE:
        signals = {"regime": "Range", "regime_score": 50.0,
            "breakout_score": 50.0, "relative_strength_score": 50.0,
            "cusum_score": 50.0, "volume_score": 50.0, "trend_score": 50.0,
            "has_position": False, "dte_remaining": 0}
        results.append(compute_strategy.delay(ticker, signals))
    return results
