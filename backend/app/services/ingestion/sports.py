"""Sports ingester using TheSportsDB (free tier, key="1")."""

import uuid
from datetime import date

import httpx

from app.services.ingestion.base import BaseIngester

# League IDs in TheSportsDB
LEAGUES = {
    "4391": "NFL",
    "4387": "NBA",
    "4424": "MLB",
    "4380": "NHL",
    "4328": "Premier League",
    "4480": "Champions League",
}


class SportsIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            for league_id, league_name in LEAGUES.items():
                # Next 15 events per league
                url = f"{self.source.base_url}/1/eventsnextleague.php?id={league_id}"
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("events"):
                        for ev in data["events"]:
                            ev["_league_name"] = league_name
                            events.append(ev)
                except Exception:
                    continue
        return events

    def normalize(self, raw: dict) -> dict | None:
        event_date = raw.get("dateEvent")
        if not event_date:
            return None

        title = raw.get("strEvent", "")
        league = raw.get("_league_name", "")

        return {
            "id": uuid.uuid4(),
            "external_id": raw.get("idEvent", ""),
            "title": f"{title}" if title else f"{league} Game",
            "description": raw.get("strDescriptionEN") or f"{league} match",
            "start_date": event_date,
            "end_date": None,
            "start_time": raw.get("strTime") or None,
            "is_all_day": not bool(raw.get("strTime")),
            "category_id": 2,  # Sports
            "impact_level": 3,
            "country_code": raw.get("strCountry", "")[:2].upper() if raw.get("strCountry") else None,
            "source_url": None,
            "image_url": raw.get("strThumb"),
        }
