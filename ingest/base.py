"""Abstract base class for data ingesters."""

import logging
import math
import re
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Category, DataSource, Event

logger = logging.getLogger(__name__)


def scaled_score(value: float, max_value: float) -> int:
    """Normalize a raw metric to 0-100 using square-root scale relative to the category max.

    sqrt preserves magnitude gaps better than log: a dominant item (100) shows a
    clear gap from mid-tier items (~40-60), while niche items stay low (<20).
    """
    if max_value <= 0 or value <= 0:
        return 0
    score = math.sqrt(value) / math.sqrt(max_value) * 100
    return max(0, min(100, round(score)))


def slugify(text: str, separator: str = "-") -> str:
    """Create a slug from text, using the given separator for non-alphanumeric runs."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", separator, text)
    return text.strip(separator)[:80]


class BaseIngester(ABC):
    def __init__(self, session: AsyncSession, source: DataSource):
        self.session = session
        self.source = source
        self._slug_to_id: dict[str, int] = {}

    async def _load_category_map(self):
        result = await self.session.execute(select(Category))
        for cat in result.scalars():
            self._slug_to_id[cat.slug] = cat.id

    @abstractmethod
    async def fetch_events(self) -> list[dict]:
        """Fetch raw event data from the external source. Returns list of raw dicts."""
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> dict | None:
        """Normalize a raw event dict into our Event model fields.
        Return None to skip the event."""
        ...

    @staticmethod
    def _coerce_types(data: dict) -> dict:
        """Ensure date/time fields are proper Python objects, not strings."""
        for field in ("start_date", "end_date"):
            val = data.get(field)
            if isinstance(val, str):
                data[field] = date.fromisoformat(val)
        for field in ("start_time", "end_time"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    parsed = time.fromisoformat(val)
                    # Strip timezone info for TIME WITHOUT TIME ZONE column
                    data[field] = parsed.replace(tzinfo=None)
                except (ValueError, AttributeError):
                    data[field] = None
        return data

    async def upsert_events(self, events: list[dict]) -> int:
        """Upsert events using ON CONFLICT on (data_source_id, external_id)."""
        count = 0
        now = datetime.now(tz=timezone.utc)
        for event_data in events:
            event_data["data_source_id"] = self.source.id
            event_data.setdefault("is_approved", True)
            try:
                self._coerce_types(event_data)
            except Exception as exc:
                logger.warning(f"Skipping event (type coercion failed): {exc}")
                continue

            stmt = pg_insert(Event).values(**event_data)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_events_source_external",
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "start_date": stmt.excluded.start_date,
                    "end_date": stmt.excluded.end_date,
                    "start_time": stmt.excluded.start_time,
                    "end_time": stmt.excluded.end_time,
                    "is_all_day": stmt.excluded.is_all_day,
                    "category_id": stmt.excluded.category_id,
                    "impact_level": stmt.excluded.impact_level,
                    "popularity_score": stmt.excluded.popularity_score,
                    "country_code": stmt.excluded.country_code,
                    "region": stmt.excluded.region,
                    "timezone": stmt.excluded.timezone,
                    "image_url": stmt.excluded.image_url,
                    "source_url": stmt.excluded.source_url,
                    "updated_at": now,
                },
            )
            try:
                await self.session.execute(stmt)
                count += 1
            except Exception as exc:
                logger.warning(f"Skipping event (upsert failed): {exc}")
                await self.session.rollback()

        await self.session.commit()
        return count

    @staticmethod
    def _apply_log_scale(events: list[dict]) -> None:
        """Set impact_level to log-scaled 0-100 based on raw popularity_score.

        popularity_score is preserved as-is (raw value).
        impact_level is overwritten with the log-scaled score for cross-category comparison.
        """
        scores = [e.get("popularity_score") or 0 for e in events]
        max_score = max(scores) if scores else 0
        if max_score <= 0:
            return
        for event in events:
            raw = event.get("popularity_score") or 0
            event["impact_level"] = scaled_score(raw, max_score)

    async def run(self, dry_run: bool = False) -> int:
        """Fetch, normalize, and upsert events."""
        logger.info(f"Starting ingestion for {self.source.name}")
        try:
            await self._load_category_map()

            raw_events = await self.fetch_events()
            logger.info(f"Fetched {len(raw_events)} raw events from {self.source.name}")

            normalized = []
            for raw in raw_events:
                result = self.normalize(raw)
                if result:
                    normalized.append(result)

            self._apply_log_scale(normalized)

            if dry_run:
                logger.info(f"Dry run: {len(normalized)} normalized events from {self.source.name}")
                return len(normalized)

            count = await self.upsert_events(normalized)

            # Update last_synced_at
            self.source.last_synced_at = datetime.now(tz=timezone.utc)
            await self.session.commit()

            logger.info(f"Ingested {count} events from {self.source.name}")
            return count
        except Exception as e:
            logger.error(f"Ingestion failed for {self.source.name}: {e}")
            raise
