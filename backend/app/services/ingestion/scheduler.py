"""APScheduler configuration and ingestion runner."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.data_source import DataSource
from app.services.ingestion.base import BaseIngester
from app.services.ingestion.games import GameIngester
from app.services.ingestion.holidays import HolidayIngester
from app.services.ingestion.movies import MovieIngester
from app.services.ingestion.political import PoliticalIngester
from app.services.ingestion.sports import SportsIngester

logger = logging.getLogger(__name__)

INGESTERS: dict[str, type[BaseIngester]] = {
    "Nager.Date": HolidayIngester,
    "TheSportsDB": SportsIngester,
    "TMDB": MovieIngester,
    "RAWG": GameIngester,
    "GDELT": PoliticalIngester,
}

scheduler = AsyncIOScheduler()


async def run_ingestion_for_source(source: DataSource, session: AsyncSession) -> int:
    ingester_cls = INGESTERS.get(source.name)
    if not ingester_cls:
        logger.warning(f"No ingester registered for source: {source.name}")
        return 0

    ingester = ingester_cls(session, source)
    return await ingester.run()


async def _run_source_by_name(source_name: str):
    """Job function for APScheduler — opens its own session."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(DataSource).where(DataSource.name == source_name, DataSource.is_active == True)  # noqa: E712
        )
        source = result.scalar_one_or_none()
        if not source:
            return
        await run_ingestion_for_source(source, session)


def setup_scheduler():
    """Register all scheduled ingestion jobs."""
    # Holidays: daily at 2am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour=2, minute=0),
        args=["Nager.Date"], id="holidays", replace_existing=True,
    )
    # Sports: every 6 hours
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour="*/6", minute=0),
        args=["TheSportsDB"], id="sports", replace_existing=True,
    )
    # Movies: daily at 3am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour=3, minute=0),
        args=["TMDB"], id="movies", replace_existing=True,
    )
    # Games: daily at 3:30am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour=3, minute=30),
        args=["RAWG"], id="games", replace_existing=True,
    )
    # Political: weekly Sunday at 4am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(day_of_week="sun", hour=4, minute=0),
        args=["GDELT"], id="political", replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started with ingestion jobs")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")
