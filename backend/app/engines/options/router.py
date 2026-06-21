import logging
from fastapi import APIRouter
from app.engines.options.schemas import OptionsGenerateRequest
from app.engines.options.service import generate_csp, generate_leaps, generate_pmcc, generate_covered_call

logger = logging.getLogger(__name__)

_GENERATORS = {
    "csp": generate_csp,
    "leaps": generate_leaps,
    "pmcc": generate_pmcc,
    "covered_call": generate_covered_call,
}

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.post("/options/generate")
def generate_options_endpoint(req: OptionsGenerateRequest):
    gen = _GENERATORS[req.strategy]
    result = gen(ticker=req.ticker, underlying_price=req.underlying_price,
                 implied_volatility=req.implied_volatility, risk_free_rate=req.risk_free_rate,
                 dividend_yield=req.dividend_yield, days_to_expiration=req.days_to_expiration,
                 target_delta=req.target_delta)
    if result is None:
        return {"ticker": req.ticker, "strategy": req.strategy, "result": None}
    return {"ticker": req.ticker, "strategy": req.strategy,
            "result": result.model_dump()}
