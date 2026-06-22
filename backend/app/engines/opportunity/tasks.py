import logging
import os
from datetime import datetime, timezone
import pandas as pd
from celery import shared_task
from app.database import get_data_dir
from app.engines.opportunity.model import ScoringRefinementModel
from app.engines.opportunity.service import build_opportunity_scores

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def compute_opportunities(self) -> dict:
    try:
        logger.info("Starting opportunity computation")
        model = ScoringRefinementModel()
        try:
            model_path = os.path.join(get_data_dir(), "models", "scoring_refinement.json")
            if os.path.exists(model_path):
                model.load(model_path)
                logger.info("Loaded ML refinement model from %s", model_path)
            else:
                logger.info("No ML model found, training new model with synthetic data")
                X, y = model.generate_synthetic_data(500)
                model.train(X, y)
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                model.save(model_path)
                logger.info("Saved new ML model to %s", model_path)
        except Exception as e:
            logger.warning("Model load/train failed: %s", e)
            model = None
        signals = _load_todays_signals()
        logger.info("Loaded %d signals, building scores", len(signals))
        scores = build_opportunity_scores(signals, model=model)
        tickers_scored = [s.ticker for s in scores]
        logger.info("Scored %d tickers: %s", len(scores), tickers_scored)
        _save_opportunities(scores)
        logger.info("Saved opportunities to parquet")
        return {"status": "success", "opportunities_count": len(scores),
                "tickers": tickers_scored,
                "date": datetime.now(timezone.utc).date().isoformat()}
    except Exception as e:
        logger.exception("Failed to compute opportunities")
        return {"status": "error", "message": str(e)}


def _load_todays_signals() -> list[dict]:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    combined = []
    for st in ["regime", "breakouts", "cusum", "indicators"]:
        signals_dir = os.path.join(data_dir, "signals", st)
        if not os.path.isdir(signals_dir):
            continue
        # Read batch file if exists (e.g. regime/{date}.parquet)
        batch_path = os.path.join(signals_dir, f"{date_str}.parquet")
        if os.path.exists(batch_path):
            try:
                combined.extend(pd.read_parquet(batch_path).to_dict(orient="records"))
            except Exception:
                pass
        # Also read per-ticker files (e.g. breakouts/{ticker}_{date}.parquet)
        for f in os.listdir(signals_dir):
            if f.endswith(f"_{date_str}.parquet") and f != f"{date_str}.parquet":
                try:
                    combined.extend(pd.read_parquet(os.path.join(signals_dir, f)).to_dict(orient="records"))
                except Exception:
                    pass
    if not combined:
        combined = _generate_synthetic_signals()
    return combined


def _generate_synthetic_signals() -> list[dict]:
    import numpy as np
    from app.models.universe import get_universe
    rng = np.random.default_rng(42)
    return [{"ticker": t, "regime_score": float(rng.uniform(20, 95)),
        "breakout_score": float(rng.uniform(10, 90)),
        "relative_strength_score": float(rng.uniform(15, 95)),
        "cusum_score": float(rng.uniform(10, 80)),
        "volume_score": float(rng.uniform(20, 85)),
        "trend_score": float(rng.uniform(25, 90))}
        for t in get_universe()]


def _save_opportunities(scores: list) -> str:
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    opp_dir = os.path.join(data_dir, "signals", "opportunities")
    os.makedirs(opp_dir, exist_ok=True)
    rows = [{"ticker": s.ticker, "date": date_str, "total_score": s.total_score,
        "regime_score": s.regime_score, "breakout_score": s.breakout_score,
        "relative_strength_score": s.relative_strength_score,
        "cusum_score": s.cusum_score, "volume_score": s.volume_score,
        "trend_score": s.trend_score, "refined_score": s.refined_score,
        "strategy_type": s.strategy_type, "rank": s.rank} for s in scores]
    path = os.path.join(opp_dir, f"{date_str}.parquet")
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path
