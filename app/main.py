"""OSINT Hub — FastAPI application entrypoint."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.config import settings
from app.database import init_db
from app.routers import auth, history, search

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("osint_hub")


def _ensure_dirs() -> None:
    os.makedirs(settings.reports_dir, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        path = settings.database_url.split(":///")[-1]
        if path and path != ":memory:":
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_dirs()
    await init_db()
    logger.info("OSINT Hub v%s started", __version__)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="OSINT Hub", version=__version__, lifespan=lifespan)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=settings.session_max_age,
        same_site="lax",
    )
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.include_router(auth.router)
    app.include_router(search.router)
    app.include_router(history.router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness check endpoint."""
        return {"status": "healthy", "version": __version__}

    return app


app = create_app()
