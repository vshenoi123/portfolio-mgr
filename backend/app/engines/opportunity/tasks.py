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


REGIME_SCORE_MAP = {
    "Bull": 85, "Bull High Vol": 65,
    "Range": 50,
    "Bear": 30, "Bear High Vol": 20,
    "Crisis": 10,
}


def _merge_signal_dirs() -> list[dict]:
    """Original 4-dir merge logic — reads signal files per ticker."""
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    merged: dict[str, dict] = {}

    # Load regimes — convert regime name + probability to regime_score
    signals_dir = os.path.join(data_dir, "signals", "regime")
    if os.path.isdir(signals_dir):
        for f in os.listdir(signals_dir):
            if not f.endswith(f"_{date_str}.parquet"):
                continue
            try:
                records = pd.read_parquet(os.path.join(signals_dir, f)).to_dict(orient="records")
            except Exception:
                continue
            for rec in records:
                ticker = rec.get("ticker", "")
                if not ticker:
                    continue
                if ticker not in merged:
                    merged[ticker] = {"ticker": ticker}
                regime_name = rec.get("regime", "Range")
                prob = rec.get("probability", 0.5)
                merged[ticker]["regime_score"] = REGIME_SCORE_MAP.get(regime_name, 50) * prob

    # Load breakouts — use max strength across all signals
    signals_dir = os.path.join(data_dir, "signals", "breakouts")
    if os.path.isdir(signals_dir):
        for f in os.listdir(signals_dir):
            if not f.endswith(f"_{date_str}.parquet"):
                continue
            try:
                records = pd.read_parquet(os.path.join(signals_dir, f)).to_dict(orient="records")
            except Exception:
                continue
            for rec in records:
                ticker = rec.get("ticker", "")
                if not ticker:
                    continue
                if ticker not in merged:
                    merged[ticker] = {"ticker": ticker}
                strength = rec.get("strength", 0)
                current = merged[ticker].get("breakout_score", 0)
                merged[ticker]["breakout_score"] = max(current, strength * 100)

    # Load CUSUM — use change_probability as cusum_score
    signals_dir = os.path.join(data_dir, "signals", "cusum")
    if os.path.isdir(signals_dir):
        for f in os.listdir(signals_dir):
            if not f.endswith(f"_{date_str}.parquet"):
                continue
            try:
                records = pd.read_parquet(os.path.join(signals_dir, f)).to_dict(orient="records")
            except Exception:
                continue
            for rec in records:
                ticker = rec.get("ticker", "")
                if not ticker:
                    continue
                if ticker not in merged:
                    merged[ticker] = {"ticker": ticker}
                merged[ticker]["cusum_score"] = rec.get("change_probability", 0) * 100

    # Load indicators (features) — flatten nested dicts
    signals_dir = os.path.join(data_dir, "signals", "indicators")
    if os.path.isdir(signals_dir):
        for f in os.listdir(signals_dir):
            if not f.endswith(f"_{date_str}.parquet"):
                continue
            try:
                records = pd.read_parquet(os.path.join(signals_dir, f)).to_dict(orient="records")
            except Exception:
                continue
            for rec in records:
                ticker = rec.get("ticker", "")
                if not ticker:
                    continue
                if ticker not in merged:
                    merged[ticker] = {"ticker": ticker}
                market_rel = rec.get("market_relative", {})
                volume = rec.get("volume", {})
                trend = rec.get("trend", {})
                momentum = rec.get("momentum", {})
                rs = market_rel.get("relative_strength", 1)
                merged[ticker]["relative_strength_score"] = min(100, max(0, rs * 50))
                rel_vol = volume.get("relative_volume_21", 1)
                merged[ticker]["volume_score"] = min(100, max(0, rel_vol * 25))
                merged[ticker]["trend_score"] = min(100, max(0, trend.get("adx", 50)))

    return list(merged.values())


SCORE_COLS = ["regime_score", "breakout_score", "cusum_score",
              "relative_strength_score", "volume_score", "trend_score"]


def _clean_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaN scores with 0 and clip to [0, 100]."""
    for col in SCORE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0).clip(0, 100)
    return df


def _load_todays_signals() -> list[dict]:
    """Load signals — prefer consolidated market scan, fall back to dir merge."""
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(data_dir, "signals", "market_scan", f"{date_str}.parquet")
    if os.path.exists(path):
        return _clean_scores(pd.read_parquet(path)).to_dict(orient="records")
    return _merge_signal_dirs()


def build_market_scan() -> str:
    """Build consolidated market_scan/{date}.parquet with metadata + all scores."""
    data_dir = get_data_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = os.path.join(data_dir, "signals", "market_scan")
    os.makedirs(output_dir, exist_ok=True)

    signals = _merge_signal_dirs()
    signals_df = pd.DataFrame(signals)

    details_path = os.path.join(data_dir, "cache", "ticker_details.parquet")
    if os.path.exists(details_path):
        meta_df = pd.read_parquet(details_path)
        meta_df = meta_df[["ticker", "name", "exchange", "type", "market_cap", "sic_code"]]
        signals_df = signals_df.merge(meta_df, on="ticker", how="left")
        signals_df["name"] = signals_df["name"].fillna("")
        signals_df["exchange"] = signals_df["exchange"].fillna("")
        signals_df["type"] = signals_df["type"].fillna("stock")
        signals_df["market_cap"] = signals_df["market_cap"].fillna(0).astype(float)
        signals_df["sic_code"] = signals_df["sic_code"].fillna(0).astype(int)

    signals_df = _clean_scores(signals_df)

    path = os.path.join(output_dir, f"{date_str}.parquet")
    signals_df.to_parquet(path, index=False)
    logger.info("Saved market scan: %s (%d rows)", path, len(signals_df))
    return path


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
