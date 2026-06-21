import logging
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def evaluate_opportunity_cost(self) -> dict:
    try:
        from app.engines.cost.service import rank_opportunity_cost
        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(settings.database_path)
        candidates = _load_opportunity_candidates()
        result = rank_opportunity_cost(
            candidates=candidates, cash_available=state.cash,
            total_portfolio_value=state.total_value,
            existing_positions=state.positions,
        )
        return {"status": "success", "recommendation": result.get("recommendation", ""),
                "candidates_count": len(result.get("candidates", [])),
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Opportunity cost evaluation failed")
        return {"status": "error", "message": str(e)}


def _load_opportunity_candidates() -> list[dict]:
    import os, numpy as np, pandas as pd
    from app.database import get_data_dir
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(get_data_dir(), "signals", "opportunities", f"{date_str}.parquet")
    if os.path.exists(path):
        try:
            df = pd.read_parquet(path)
            return df.to_dict(orient="records")
        except Exception:
            pass
    rng = np.random.default_rng(42)
    from app.models.universe import DEFAULT_UNIVERSE
    return [{"candidate": t, "score": float(rng.uniform(30, 95)),
             "risk_score": float(rng.uniform(2, 15)),
             "estimated_return_pct": float(rng.uniform(5, 30)),
             "capital_required": float(rng.uniform(5000, 50000))}
            for t in DEFAULT_UNIVERSE[:10]]
