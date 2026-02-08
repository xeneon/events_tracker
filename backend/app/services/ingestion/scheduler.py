"""APScheduler configuration and ingestion runner."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.data_source import DataSource
from app.services.ingestion.base import BaseIngester
from app.services.ingestion.calendarific import CalendarificIngester
from app.services.ingestion.trakt import TraktIngester

logger = logging.getLogger(__name__)

INGESTERS: dict[str, type[BaseIngester]] = {
    "Calendarific": CalendarificIngester,
    "Trakt": TraktIngester,
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
    # Calendarific US holidays: daily at 2am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour=2, minute=0),
        args=["Calendarific"], id="calendarific", replace_existing=True,
    )
    # Trakt anticipated movies/shows: daily at 3am UTC
    scheduler.add_job(
        _run_source_by_name, CronTrigger(hour=3, minute=0),
        args=["Trakt"], id="trakt", replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler started with ingestion jobs")


def shutdown_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("APScheduler shut down")
