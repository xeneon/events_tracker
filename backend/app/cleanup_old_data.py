"""One-time cleanup: remove old data sources, their events, and orphaned categories."""

import asyncio

from sqlalchemy import delete, select

from app.database import async_session_maker
from app.models.category import Category
from app.models.data_source import DataSource
from app.models.event import Event

OLD_SOURCE_NAMES = ["Nager.Date", "TheSportsDB", "TMDB", "RAWG", "GDELT"]
OLD_CATEGORY_SLUGS = ["public-holiday", "sports", "movie-release", "game-release", "political"]


async def main():
    async with async_session_maker() as session:
        # Find old data source IDs
        result = await session.execute(
            select(DataSource).where(DataSource.name.in_(OLD_SOURCE_NAMES))
        )
        old_sources = result.scalars().all()
        old_source_ids = [s.id for s in old_sources]

        if old_source_ids:
            # Delete events from old data sources
            del_events = await session.execute(
                delete(Event).where(Event.data_source_id.in_(old_source_ids))
            )
            print(f"Deleted {del_events.rowcount} events from old data sources.")

            # Delete old data source rows
            await session.execute(
                delete(DataSource).where(DataSource.id.in_(old_source_ids))
            )
            print(f"Deleted {len(old_source_ids)} old data sources.")
        else:
            print("No old data sources found.")

        # Delete orphaned old categories
        del_cats = await session.execute(
            delete(Category).where(Category.slug.in_(OLD_CATEGORY_SLUGS))
        )
        print(f"Deleted {del_cats.rowcount} old categories.")

        await session.commit()
        print("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())
