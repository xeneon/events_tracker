"""Schema create_all + seed categories/data_sources on startup."""

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from ingest.db import Base, async_session_maker, engine
from ingest.models import Category, DataSource, Event  # noqa: F401 — registers Event table

logger = logging.getLogger(__name__)

CATEGORIES = [
    {"slug": "federal-holiday", "name": "Federal Holiday", "color": "#dc2626", "sort_order": 1},
    {"slug": "state-holiday",   "name": "State Holiday",   "color": "#ea580c", "sort_order": 2},
    {"slug": "observance",      "name": "Observance",      "color": "#d97706", "sort_order": 3},
    {"slug": "religious",       "name": "Religious",       "color": "#65a30d", "sort_order": 4},
    {"slug": "other",           "name": "Other",           "color": "#6366f1", "sort_order": 5},
    {"slug": "movies",          "name": "Movies",          "color": "#7c3aed", "sort_order": 6},
    {"slug": "tv-shows",        "name": "TV Shows",        "color": "#db2777", "sort_order": 7},
    {"slug": "video-games",     "name": "Video Games",     "color": "#0369a1", "sort_order": 8},
    {"slug": "music-releases",  "name": "Music Releases",  "color": "#0891b2", "sort_order": 9},
]

DATA_SOURCES = [
    {
        "name": "Calendarific",
        "source_type": "api",
        "base_url": "https://calendarific.com/api/v2",
        "api_key_env_var": "CALENDARIFIC_API_KEY",
        "is_active": True,
    },
    {
        "name": "IGDB",
        "source_type": "api",
        "base_url": "https://api.igdb.com/v4",
        "api_key_env_var": "TWITCH_CLIENT_ID",
        "is_active": True,
    },
    {
        "name": "Trakt",
        "source_type": "api",
        "base_url": "https://api.trakt.tv",
        "api_key_env_var": "TRAKT_CLIENT_ID",
        "is_active": True,
    },
    {
        "name": "Wikipedia Albums",
        "source_type": "scraper",
        "base_url": "https://en.wikipedia.org",
        "api_key_env_var": "LASTFM_API_KEY",
        "is_active": True,
    },
]


async def run_seed() -> None:
    """Idempotently create tables and seed reference data."""
    logger.info("Running database seed...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        for cat in CATEGORIES:
            stmt = pg_insert(Category).values(**cat).on_conflict_do_nothing(index_elements=["slug"])
            await session.execute(stmt)

        for src in DATA_SOURCES:
            stmt = pg_insert(DataSource).values(**src).on_conflict_do_nothing(index_elements=["name"])
            await session.execute(stmt)

        await session.commit()

    logger.info("Database seed complete.")
