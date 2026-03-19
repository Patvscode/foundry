from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from foundry.api.router import router as api_router
from foundry.config import FoundrySettings, get_settings
from foundry.jobs.runner import JobRunner
from foundry.logging_setup import configure_logging
from foundry.storage.database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: FoundrySettings = get_settings()
    configure_logging(settings.logging.level, Path(settings.storage.data_dir))
    logger = logging.getLogger("foundry.main")

    db_path = Path(settings.storage.data_dir) / "foundry.db"
    db = await init_database(db_path)

    # Start job runner
    runner = JobRunner(db, settings)
    await runner.start()

    app.state.settings = settings
    app.state.db = db
    app.state.runner = runner
    app.state.started_at = time.monotonic()

    logger.info(
        "Foundry startup complete",
        extra={
            "host": settings.server.host,
            "port": settings.server.port,
            "db_path": str(db_path),
            "data_dir": settings.storage.data_dir,
        },
    )
    try:
        yield
    finally:
        logger.info("Foundry shutting down")
        await runner.stop()
        await db.close()


app = FastAPI(title="Foundry", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
