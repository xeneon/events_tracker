"""Standalone CLI for running ingestion scripts.

Usage:
    cd backend
    python -m ingest --list
    python -m ingest calendarific
    python -m ingest trakt --dry-run
    python -m ingest --all
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select

from .base import BaseIngester
from .calendarific import CalendarificIngester
from .db import async_session_maker
from .fashion_weeks import FashionWeeksIngester
from .models import DataSource
from .trakt import TraktIngester
from .wikipedia_albums import WikipediaAlbumsIngester

logger = logging.getLogger(__name__)

INGESTERS: dict[str, type[BaseIngester]] = {
    "Calendarific": CalendarificIngester,
    "Fashion Weeks": FashionWeeksIngester,
    "Trakt": TraktIngester,
    "Wikipedia Albums": WikipediaAlbumsIngester,
}

SOURCE_ALIASES: dict[str, str] = {
    "calendarific": "Calendarific",
    "trakt": "Trakt",
    "fashion-weeks": "Fashion Weeks",
    "wikipedia-albums": "Wikipedia Albums",
}


async def run_ingestion_for_source(source: DataSource, session) -> int:
    """Instantiate the right ingester and run it."""
    ingester_cls = INGESTERS.get(source.name)
    if not ingester_cls:
        print(f"Error: No ingester class registered for '{source.name}'.")
        return 0
    ingester = ingester_cls(session, source)
    return await ingester.run()


async def run_source(name: str, dry_run: bool = False) -> None:
    """Run a single ingester by its CLI alias name."""
    source_name = SOURCE_ALIASES.get(name)
    if not source_name:
        print(f"Error: Unknown ingester '{name}'.")
        print(f"Available: {', '.join(SOURCE_ALIASES)}")
        sys.exit(1)

    ingester_cls = INGESTERS.get(source_name)
    if not ingester_cls:
        print(f"Error: No ingester class registered for '{source_name}'.")
        sys.exit(1)

    async with async_session_maker() as session:
        result = await session.execute(
            select(DataSource).where(DataSource.name == source_name)
        )
        source = result.scalar_one_or_none()
        if not source:
            print(f"Error: DataSource '{source_name}' not found in database.")
            print("Have you run the seed script?  cd backend && python -m app.seed")
            sys.exit(1)

        if dry_run:
            ingester = ingester_cls(session, source)
            await ingester._load_category_map()
            print(f"Fetching events from {source_name}...")
            raw_events = await ingester.fetch_events()
            print(f"  Fetched {len(raw_events)} raw events")

            normalized = []
            for raw in raw_events:
                evt = ingester.normalize(raw)
                if evt:
                    normalized.append(evt)
            print(f"  Normalized {len(normalized)} events (skipped {len(raw_events) - len(normalized)})")

            if normalized:
                sample = normalized[0]
                print(f"  Sample: {sample.get('title', 'N/A')} "
                      f"({sample.get('start_date', 'N/A')})")
            print("Dry run complete — no database writes.")
        else:
            count = await run_ingestion_for_source(source, session)
            print(f"Ingested {count} events from {source_name}.")


async def run_all(dry_run: bool = False) -> None:
    """Run all ingesters in sequence."""
    for alias in SOURCE_ALIASES:
        print(f"\n{'='*40}")
        print(f"Running: {alias}")
        print(f"{'='*40}")
        await run_source(alias, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ingest",
        description="Run event ingestion scripts from the command line.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        choices=list(SOURCE_ALIASES),
        help="Ingester to run (e.g. calendarific, trakt)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available ingesters and exit",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all active ingesters",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and normalize only — no database writes",
    )

    args = parser.parse_args()

    if args.list:
        print("Available ingesters:")
        for alias, name in SOURCE_ALIASES.items():
            print(f"  {alias:20s} → {name}")
        return

    if not args.source and not args.all:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    if args.all:
        asyncio.run(run_all(dry_run=args.dry_run))
    else:
        asyncio.run(run_source(args.source, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
