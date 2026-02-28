"""FastAPI application with lifespan startup for DB seeding."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .seed import run_seed
from .routes.home import router as home_router
from .routes.config_routes import router as config_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_seed()
    yield


app = FastAPI(lifespan=lifespan, title="Events Tracker")
app.include_router(home_router)
app.include_router(config_router)
