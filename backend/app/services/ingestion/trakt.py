"""Trakt anticipated movies and TV shows ingester."""

import logging
import uuid
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import Category
from app.models.data_source import DataSource
from app.services.ingestion.base import BaseIngester

logger = logging.getLogger(__name__)

# Category slug mapping
CATEGORY_SLUGS = {
    "movie": "movies",
    "show": "tv-shows",
}

# Impact level based on list_count ranking (position in results)
def get_impact_level(position: int, total: int) -> int:
    """Map position to impact level 1-5 (top items get highest impact)."""
    if position <= total * 0.1:  # Top 10%
        return 5
    elif position <= total * 0.25:  # Top 25%
        return 4
    elif position <= total * 0.5:  # Top 50%
        return 3
    elif position <= total * 0.75:  # Top 75%
        return 2
    return 1


class TraktIngester(BaseIngester):
    def __init__(self, session: AsyncSession, source: DataSource):
        super().__init__(session, source)
        self._slug_to_id: dict[str, int] = {}

    async def _load_category_map(self):
        result = await self.session.execute(select(Category))
        for cat in result.scalars():
            self._slug_to_id[cat.slug] = cat.id

    async def fetch_events(self) -> list[dict]:
        client_id = settings.TRAKT_CLIENT_ID
        if not client_id:
            logger.error("TRAKT_CLIENT_ID not set — skipping ingestion")
            return []

        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": client_id,
        }

        raw_events: list[dict] = []

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            # Fetch anticipated movies
            try:
                resp = await client.get(
                    "https://api.trakt.tv/movies/anticipated",
                    params={"limit": 100, "extended": "full"},
                )
                resp.raise_for_status()
                movies = resp.json()
                for idx, item in enumerate(movies):
                    item["_type"] = "movie"
                    item["_position"] = idx
                    item["_total"] = len(movies)
                raw_events.extend(movies)
                logger.info(f"Trakt: fetched {len(movies)} anticipated movies")
            except Exception as exc:
                logger.error(f"Trakt movies fetch failed: {exc}")

            # Fetch anticipated TV shows
            try:
                resp = await client.get(
                    "https://api.trakt.tv/shows/anticipated",
                    params={"limit": 100, "extended": "full"},
                )
                resp.raise_for_status()
                shows = resp.json()
                for idx, item in enumerate(shows):
                    item["_type"] = "show"
                    item["_position"] = idx
                    item["_total"] = len(shows)
                raw_events.extend(shows)
                logger.info(f"Trakt: fetched {len(shows)} anticipated TV shows")
            except Exception as exc:
                logger.error(f"Trakt shows fetch failed: {exc}")

        return raw_events

    def normalize(self, raw: dict) -> dict | None:
        item_type = raw.get("_type", "movie")
        position = raw.get("_position", 0)
        total = raw.get("_total", 100)
        
        # Get the movie or show object
        content = raw.get("movie") or raw.get("show")
        if not content:
            return None

        # Get release date
        if item_type == "movie":
            release_date_str = content.get("released")
        else:
            release_date_str = content.get("first_aired")
        
        if not release_date_str:
            # Skip items without a release date
            return None
        
        # Parse date (format: "2026-12-18" or "2026-03-06T00:00:00.000Z")
        try:
            date_str = release_date_str[:10]
            release_date = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {release_date_str}")
            return None

        title = content.get("title", "Unknown")
        trakt_id = content.get("ids", {}).get("trakt")
        imdb_id = content.get("ids", {}).get("imdb")
        
        if not trakt_id:
            return None

        # Category mapping
        slug = CATEGORY_SLUGS.get(item_type, "other")
        category_id = self._slug_to_id.get(slug, self._slug_to_id.get("other"))

        # Build image URL from Trakt images
        images = content.get("images", {})
        poster_list = images.get("poster", [])
        image_url = None
        if poster_list and isinstance(poster_list, list) and poster_list[0]:
            # Trakt returns relative URLs, prepend https://
            poster_path = poster_list[0]
            if not poster_path.startswith("http"):
                image_url = f"https://{poster_path}"
            else:
                image_url = poster_path

        # Build source URL
        slug_name = content.get("ids", {}).get("slug", "")
        if item_type == "movie":
            source_url = f"https://trakt.tv/movies/{slug_name}" if slug_name else None
        else:
            source_url = f"https://trakt.tv/shows/{slug_name}" if slug_name else None

        # Use IMDB URL if available (more recognizable to users)
        if imdb_id:
            source_url = f"https://www.imdb.com/title/{imdb_id}/"

        # Build description
        overview = content.get("overview") or ""
        list_count = raw.get("list_count", 0)
        year = content.get("year", "")
        genres = content.get("genres", [])
        genre_str = ", ".join(g.replace("-", " ").title() for g in genres[:3]) if genres else ""
        
        description_parts = []
        if year:
            description_parts.append(f"({year})")
        if genre_str:
            description_parts.append(f"• {genre_str}")
        if list_count:
            description_parts.append(f"• {list_count:,} users anticipating")
        if overview:
            description_parts.append(f"\n\n{overview}")
        
        description = " ".join(description_parts[:3])
        if overview:
            description += f"\n\n{overview}"

        return {
            "id": uuid.uuid4(),
            "external_id": f"trakt_{item_type}_{trakt_id}",
            "title": title,
            "description": description[:2000] if description else None,  # Truncate if too long
            "start_date": date_str,
            "end_date": None,
            "is_all_day": True,
            "category_id": category_id,
            "impact_level": get_impact_level(position, total),
            "popularity_score": list_count,
            "country_code": content.get("country", "").upper()[:2] or None,
            "region": None,
            "source_url": source_url,
            "image_url": image_url,
        }

    async def run(self) -> int:
        await self._load_category_map()
        return await super().run()
