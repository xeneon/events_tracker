"""Holiday ingester using Nager.Date API (no key required)."""

import uuid
from datetime import date

import httpx

from app.services.ingestion.base import BaseIngester

COUNTRIES = ["US", "GB", "CA", "DE", "FR", "AU", "JP", "BR", "IN", "MX"]


class HolidayIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        events = []
        current_year = date.today().year
        years = [current_year, current_year + 1]

        async with httpx.AsyncClient(timeout=30) as client:
            for country in COUNTRIES:
                for year in years:
                    url = f"{self.source.base_url}/PublicHolidays/{year}/{country}"
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        for holiday in resp.json():
                            holiday["_country"] = country
                            events.append(holiday)
                    except Exception:
                        continue
        return events

    def normalize(self, raw: dict) -> dict | None:
        return {
            "id": uuid.uuid4(),
            "external_id": f"{raw['_country']}_{raw['date']}_{raw.get('localName', '')}",
            "title": raw.get("localName") or raw.get("name", "Holiday"),
            "description": raw.get("name"),
            "start_date": raw["date"],
            "end_date": None,
            "is_all_day": True,
            "category_id": 1,  # Public Holiday
            "impact_level": 3,
            "country_code": raw["_country"],
            "source_url": None,
            "image_url": None,
        }
