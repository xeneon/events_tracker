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
from .config import settings
from .db import async_session_maker
from .models import DataSource
from .igdb import IGDBIngester
from .trakt import TraktIngester
from .wikipedia_albums import WikipediaAlbumsIngester
from .ballotpedia import BallotpediaIngester

logger = logging.getLogger(__name__)

INGESTERS: dict[str, type[BaseIngester]] = {
    "Calendarific": CalendarificIngester,
    "IGDB": IGDBIngester,
    "Trakt": TraktIngester,
    "Wikipedia Albums": WikipediaAlbumsIngester,
    "Ballotpedia": BallotpediaIngester,
}

SOURCE_ALIASES: dict[str, str] = {
    "calendarific": "Calendarific",
    "igdb": "IGDB",
    "trakt": "Trakt",
    "wikipedia-albums": "Wikipedia Albums",
    "ballotpedia": "Ballotpedia",
}


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

        ingester = ingester_cls(session, source)
        count = await ingester.run(dry_run=dry_run)
        if dry_run:
            print(f"Dry run complete — {count} events normalized from {source_name}.")
        else:
            print(f"Ingested {count} events from {source_name}.")


async def run_all(dry_run: bool = False) -> None:
    """Run all ingesters in sequence, then export to Google Sheets."""
    for alias in SOURCE_ALIASES:
        print(f"\n{'='*40}")
        print(f"Running: {alias}")
        print(f"{'='*40}")
        await run_source(alias, dry_run=dry_run)

    # Export to Google Sheets after all ingesters complete
    print(f"\n{'='*40}")
    print(f"Running: export-sheets")
    print(f"{'='*40}")
    if dry_run:
        from .export_sheets import fetch_rows
        rows = await fetch_rows()
        for row in rows[:10]:
            print(row)
        if len(rows) > 10:
            print(f"... and {len(rows) - 10} more rows")
        print("Dry run complete — no sheet writes.")
    else:
        from .export_sheets import fetch_rows, write_to_sheet
        rows = await fetch_rows()
        print(f"Fetched {len(rows)} rows from database.")
        count = write_to_sheet(rows)
        tab_name = settings.GOOGLE_SHEET_TAB
        print(f"Wrote {count} rows + header to '{tab_name}'.")


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
