"""Game release ingester using RAWG API."""

import uuid
from datetime import date, timedelta

import httpx

from app.config import settings
from app.services.ingestion.base import BaseIngester


class GameIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        api_key = settings.RAWG_API_KEY
        if not api_key:
            return []

        events = []
        today = date.today()
        end = today + timedelta(days=90)

        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(1, 4):
                url = (
                    f"{self.source.base_url}/games"
                    f"?key={api_key}"
                    f"&dates={today.isoformat()},{end.isoformat()}"
                    f"&ordering=-rating"
                    f"&page={page}"
                    f"&page_size=20"
                )
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    for game in data.get("results", []):
                        if game.get("rating", 0) > 3.0:
                            events.append(game)
                except Exception:
                    break
        return events

    def normalize(self, raw: dict) -> dict | None:
        release_date = raw.get("released")
        if not release_date:
            return None

        return {
            "id": uuid.uuid4(),
            "external_id": str(raw["id"]),
            "title": raw.get("name", "Unknown Game"),
            "description": None,
            "start_date": release_date,
            "end_date": None,
            "is_all_day": True,
            "category_id": 4,  # Game Release
            "impact_level": min(5, max(1, int(raw.get("rating", 0)))),
            "country_code": None,
            "source_url": f"https://rawg.io/games/{raw.get('slug', raw['id'])}",
            "image_url": raw.get("background_image"),
        }
