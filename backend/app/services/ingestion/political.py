"""Political events ingester using GDELT API (light touch)."""

import uuid
from datetime import date, timedelta

import httpx

from app.services.ingestion.base import BaseIngester


class PoliticalIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        events = []
        async with httpx.AsyncClient(timeout=60) as client:
            # Use GDELT DOC API for recent high-impact political events
            url = (
                "https://api.gdeltproject.org/api/v2/doc/doc"
                "?query=political OR election OR summit OR treaty"
                "&mode=artlist"
                "&maxrecords=50"
                "&format=json"
                "&sourcelang=english"
                "&sort=hybridrel"
            )
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for article in data.get("articles", []):
                    events.append(article)
            except Exception:
                pass
        return events

    def normalize(self, raw: dict) -> dict | None:
        title = raw.get("title", "")
        if not title:
            return None

        # Use seendate as event date
        seen = raw.get("seendate", "")
        if seen:
            # Format: "20260207T120000Z" -> "2026-02-07"
            event_date = f"{seen[:4]}-{seen[4:6]}-{seen[6:8]}"
        else:
            event_date = date.today().isoformat()

        return {
            "id": uuid.uuid4(),
            "external_id": raw.get("url", title)[:300],
            "title": title[:300],
            "description": raw.get("title"),
            "start_date": event_date,
            "end_date": None,
            "is_all_day": True,
            "category_id": 5,  # Political
            "impact_level": 3,
            "country_code": raw.get("sourcecountry", "")[:2].upper() or None,
            "source_url": raw.get("url"),
            "image_url": raw.get("socialimage"),
            "is_approved": False,  # Political events need manual review
        }
