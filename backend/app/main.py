import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.engines.cusum.router import router as cusum_router
from app.engines.data.router import router as data_router
from app.engines.features.router import router as features_router
from app.engines.regime.router import router as regime_router
from app.engines.breakout.router import router as breakout_router
from app.engines.opportunity.router import router as opportunity_router
from app.engines.strategy.router import router as strategy_router
from app.engines.options.router import router as options_router
from app.engines.portfolio.router import router as portfolio_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend (Phase 4)")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="AI Portfolio Manager", version="0.4.0", lifespan=lifespan)

    app.include_router(cusum_router)
    app.include_router(data_router)
    app.include_router(features_router)
    app.include_router(regime_router)
    app.include_router(breakout_router)
    app.include_router(opportunity_router)
    app.include_router(strategy_router)
    app.include_router(options_router)
    app.include_router(portfolio_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.4.0"}

    return app


app = create_app()
