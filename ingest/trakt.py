"""Trakt anticipated movies/TV shows and season premieres ingester."""

import asyncio
import logging
import uuid
from datetime import date, timedelta

import httpx

from .base import BaseIngester
from .config import settings

logger = logging.getLogger(__name__)

# Category slug mapping
CATEGORY_SLUGS = {
    "movie": "movies",
    "show": "tv-shows",
}

class TraktIngester(BaseIngester):
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
                for item in movies:
                    item["_type"] = "movie"
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
                for item in shows:
                    item["_type"] = "show"
                raw_events.extend(shows)
                logger.info(f"Trakt: fetched {len(shows)} anticipated TV shows")
            except Exception as exc:
                logger.error(f"Trakt shows fetch failed: {exc}")

            # Fetch season premieres by checking favorited + popular shows
            # for upcoming new seasons via /shows/{id}/next_episode
            try:
                today_str = date.today().isoformat()
                cutoff_str = (date.today() + timedelta(days=180)).isoformat()
                shows_to_check: dict[int, dict] = {}

                # Collect shows from favorited (all-time, 2 pages) and popular (current, 2 pages)
                for endpoint, wrapped in [
                    ("/shows/favorited/all", True),
                    ("/shows/popular", False),
                ]:
                    for page in range(1, 3):
                        try:
                            resp = await client.get(
                                f"https://api.trakt.tv{endpoint}",
                                params={"limit": 100, "page": page, "extended": "full"},
                            )
                            resp.raise_for_status()
                            for item in resp.json():
                                show = item["show"] if wrapped else item
                                sid = show.get("ids", {}).get("trakt")
                                if sid and sid not in shows_to_check and show.get("status") == "returning series":
                                    shows_to_check[sid] = show
                        except Exception:
                            continue

                # Check each returning series for an upcoming season premiere
                premieres = []
                for sid, show in shows_to_check.items():
                    try:
                        ep_resp = await client.get(
                            f"https://api.trakt.tv/shows/{sid}/next_episode",
                            params={"extended": "full"},
                        )
                        if ep_resp.status_code != 200 or not ep_resp.text.strip():
                            continue
                        ep = ep_resp.json()
                        aired = ep.get("first_aired", "")
                        if (aired and today_str <= aired[:10] <= cutoff_str
                                and ep.get("number") == 1 and ep.get("season", 0) > 1):
                            premieres.append({
                                "show": show,
                                "episode": ep,
                                "first_aired": aired,
                                "_type": "premiere",
                            })
                    except Exception:
                        continue
                    await asyncio.sleep(0.05)

                raw_events.extend(premieres)
                logger.info(f"Trakt: found {len(premieres)} season premieres (checked {len(shows_to_check)} returning series)")
            except Exception as exc:
                logger.error(f"Trakt season premieres fetch failed: {exc}")

        return raw_events

    def normalize(self, raw: dict) -> dict | None:
        item_type = raw.get("_type", "movie")

        if item_type == "premiere":
            return self._normalize_premiere(raw)

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
            "popularity_score": list_count,
            "country_code": content.get("country", "").upper()[:2] or None,
            "region": None,
            "source_url": source_url,
            "image_url": image_url,
        }

    def _normalize_premiere(self, raw: dict) -> dict | None:
        """Normalize a season premiere item (returning show with upcoming new season)."""
        show = raw.get("show")
        episode = raw.get("episode", {})
        if not show:
            return None

        # Date comes from top-level first_aired, not show.first_aired
        release_date_str = raw.get("first_aired")
        if not release_date_str:
            return None

        try:
            date_str = release_date_str[:10]
            date.fromisoformat(date_str)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse premiere date: {release_date_str}")
            return None

        trakt_id = show.get("ids", {}).get("trakt")
        imdb_id = show.get("ids", {}).get("imdb")
        if not trakt_id:
            return None

        season = episode.get("season", 1)
        show_title = show.get("title", "Unknown")
        title = f"{show_title} - Season {season}"

        # Category: tv-shows
        category_id = self._slug_to_id.get("tv-shows", self._slug_to_id.get("other"))

        votes = show.get("votes", 0) or 0

        # Source URL: prefer IMDB
        slug_name = show.get("ids", {}).get("slug", "")
        source_url = f"https://trakt.tv/shows/{slug_name}" if slug_name else None
        if imdb_id:
            source_url = f"https://www.imdb.com/title/{imdb_id}/"

        # Image
        images = show.get("images", {})
        poster_list = images.get("poster", [])
        image_url = None
        if poster_list and isinstance(poster_list, list) and poster_list[0]:
            poster_path = poster_list[0]
            if not poster_path.startswith("http"):
                image_url = f"https://{poster_path}"
            else:
                image_url = poster_path

        # Description
        overview = show.get("overview") or ""
        year = show.get("year", "")
        genres = show.get("genres", [])
        genre_str = ", ".join(g.replace("-", " ").title() for g in genres[:3]) if genres else ""

        description_parts = []
        description_parts.append(f"Season {season} Premiere")
        if year:
            description_parts.append(f"({year})")
        if genre_str:
            description_parts.append(f"• {genre_str}")
        if votes:
            description_parts.append(f"• {votes:,} Trakt ratings")
        description = " ".join(description_parts)
        if overview:
            description += f"\n\n{overview}"

        return {
            "id": uuid.uuid4(),
            "external_id": f"trakt_premiere_{trakt_id}_s{season}",
            "title": title,
            "description": description[:2000] if description else None,
            "start_date": date_str,
            "end_date": None,
            "is_all_day": True,
            "category_id": category_id,
            "popularity_score": votes,
            "country_code": show.get("country", "").upper()[:2] or None,
            "region": None,
            "source_url": source_url,
            "image_url": image_url,
        }
