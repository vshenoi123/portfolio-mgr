import logging
from celery import shared_task

logger = logging.getLogger(__name__)


def _get_generator(strategy: str):
    from app.engines.options.service import generate_csp, generate_leaps, generate_pmcc, generate_covered_call
    generators = {"csp": generate_csp, "leaps": generate_leaps,
                  "pmcc": generate_pmcc, "covered_call": generate_covered_call}
    return generators.get(strategy)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_options(self, ticker: str, strategy: str = "csp",
                     underlying_price: float = 100.0, implied_volatility: float = 0.30,
                     days_to_expiration: int = 45, target_delta: float = 0.30,
                     risk_free_rate: float = 0.05, dividend_yield: float = 0.0) -> dict:
    try:
        gen = _get_generator(strategy)
        if gen is None:
            return {"ticker": ticker, "status": "error",
                    "message": f"Unknown strategy: {strategy}"}
        result = gen(ticker=ticker, underlying_price=underlying_price,
                     implied_volatility=implied_volatility,
                     days_to_expiration=days_to_expiration,
                     target_delta=target_delta,
                     risk_free_rate=risk_free_rate,
                     dividend_yield=dividend_yield)
        return {"ticker": ticker, "status": "success", "strategy": strategy,
                "details": result.model_dump()}
    except Exception as e:
        return {"ticker": ticker, "status": "error", "strategy": strategy,
                "message": str(e)}
