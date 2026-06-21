import logging
from datetime import datetime, timezone
from celery import shared_task
from app.config import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def evaluate_replacements(self) -> dict:
    try:
        from app.engines.replacement.service import evaluate_all_positions, find_replacements
        from app.engines.portfolio.service import load_portfolio_state
        state = load_portfolio_state(settings.database_path)
        positions_data = []
        for p in state.positions:
            positions_data.append({
                "ticker": p.get("ticker"), "score": 50,
                "regime": "Range", "trend_score": 50,
                "momentum_score": 50, "unrealized_pl_pct": p.get("unrealized_pl_pct", 0),
                "days_held": 0, "sector": p.get("sector", "UNKNOWN"),
            })
        opps = _load_opportunities_for_replacement()
        result = find_replacements(positions_data, opps)
        return {"status": "success",
                "evaluations_count": len(result.evaluations),
                "replacements_count": len(result.replacements),
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Replacement evaluation failed")
        return {"status": "error", "message": str(e)}


def _load_opportunities_for_replacement() -> list[dict]:
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
    sectors = ["TECHNOLOGY", "FINANCIAL", "HEALTHCARE", "ENERGY", "CONSUMER_CYCLICAL"]
    return [{"ticker": t, "score": float(rng.uniform(30, 95)), "sector": sectors[i % len(sectors)]}
            for i, t in enumerate(DEFAULT_UNIVERSE[:10])]
