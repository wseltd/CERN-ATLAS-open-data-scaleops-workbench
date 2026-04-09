"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from atlas_workbench.db.session import bootstrap_db

__version__ = "0.1.0"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    bootstrap_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="ATLAS Open Data ScaleOps Workbench",
        version=__version__,
        description=(
            "Control-plane-first data engineering system for the ATLAS 2024 research "
            "open-data release in DAOD_PHYSLITE format (65.3 TiB, 70,611 files)."
        ),
        lifespan=_lifespan,
    )

    from atlas_workbench.api.routers import (
        collections,
        eval_router,
        manifests,
        plans,
        seed_query,
        validate_evidence,
    )

    app.include_router(seed_query.router)
    app.include_router(collections.router)
    app.include_router(manifests.router)
    app.include_router(plans.router)
    app.include_router(validate_evidence.router)
    app.include_router(eval_router.router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
