import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
import app.celery_app  # noqa: F401 — ensure celery_app is loaded and registered as current
from app.engines.cusum.router import router as cusum_router
from app.engines.data.router import router as data_router
from app.engines.features.router import router as features_router
from app.engines.regime.router import router as regime_router
from app.engines.breakout.router import router as breakout_router
from app.engines.opportunity.router import router as opportunity_router
from app.engines.strategy.router import router as strategy_router
from app.engines.options.router import router as options_router
from app.engines.portfolio.router import router as portfolio_router
from app.engines.positions.router import router as positions_router
from app.engines.monitoring.router import router as monitoring_router
from app.engines.trading.router import router as trading_router
from app.engines.ai_manager.router import router as ai_router
from app.engines.self_learning.router import router as self_learning_router
from app.engines.monte_carlo.router import router as monte_carlo_router
from app.engines.stress_test.router import router as stress_test_router
from app.engines.settings.router import router as settings_router
from app.health import get_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend (Phase 6)")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="AI Portfolio Manager", version="1.0.0", lifespan=lifespan)

    app.include_router(cusum_router)
    app.include_router(data_router)
    app.include_router(features_router)
    app.include_router(regime_router)
    app.include_router(breakout_router)
    app.include_router(opportunity_router)
    app.include_router(strategy_router)
    app.include_router(options_router)
    app.include_router(portfolio_router)
    app.include_router(positions_router)
    app.include_router(monitoring_router)
    app.include_router(trading_router)
    app.include_router(ai_router)
    app.include_router(self_learning_router)
    app.include_router(monte_carlo_router)
    app.include_router(stress_test_router)
    app.include_router(settings_router)

    @app.get("/health")
    async def health():
        return get_health()

    return app


app = create_app()