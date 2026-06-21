import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.engines.data.router import router as data_router
from app.engines.features.router import router as features_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Starting AI Portfolio Manager backend")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Portfolio Manager",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(data_router)
    app.include_router(features_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
