"""Movie ingester using TMDB API."""

import uuid
from datetime import date, timedelta

import httpx

from app.config import settings
from app.services.ingestion.base import BaseIngester


class MovieIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        api_key = settings.TMDB_API_KEY
        if not api_key:
            return []

        events = []
        today = date.today()
        end = today + timedelta(days=90)

        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(1, 4):  # First 3 pages
                url = (
                    f"{self.source.base_url}/discover/movie"
                    f"?api_key={api_key}"
                    f"&primary_release_date.gte={today.isoformat()}"
                    f"&primary_release_date.lte={end.isoformat()}"
                    f"&sort_by=popularity.desc"
                    f"&page={page}"
                )
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    for movie in data.get("results", []):
                        if movie.get("popularity", 0) > 10:
                            events.append(movie)
                except Exception:
                    break
        return events

    def normalize(self, raw: dict) -> dict | None:
        release_date = raw.get("release_date")
        if not release_date:
            return None

        poster = raw.get("poster_path")
        image_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None

        return {
            "id": uuid.uuid4(),
            "external_id": str(raw["id"]),
            "title": raw.get("title", "Unknown Movie"),
            "description": raw.get("overview"),
            "start_date": release_date,
            "end_date": None,
            "is_all_day": True,
            "category_id": 3,  # Movie Release
            "impact_level": min(5, max(1, int(raw.get("popularity", 0) / 100) + 1)),
            "country_code": None,
            "source_url": f"https://www.themoviedb.org/movie/{raw['id']}",
            "image_url": image_url,
        }
