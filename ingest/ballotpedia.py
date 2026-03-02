"""Ballotpedia US statewide primary election date scraper."""

import logging
import uuid
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from .base import BaseIngester, slugify

logger = logging.getLogger(__name__)

URL = "https://ballotpedia.org/Statewide_primary_elections_calendar"


class BallotpediaIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "events-tracker/1.0"}) as client:
            resp = await client.get(URL)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for table in soup.find_all("table", class_="wikitable"):
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all("th")]
            if "state" not in headers or "date" not in headers:
                continue
            state_idx = headers.index("state")
            date_idx = headers.index("date")
            max_idx = max(state_idx, date_idx)
            for row in table.find_all("tr")[1:]:  # skip header
                cells = row.find_all(["td", "th"])
                if len(cells) <= max_idx:
                    continue
                state = cells[state_idx].get_text(strip=True)
                date_str = cells[date_idx].get_text(strip=True)
                if state and date_str:
                    results.append({"state": state, "date_str": date_str})

        logger.info(f"Ballotpedia: found {len(results)} primary dates")
        return results

    def normalize(self, raw: dict) -> dict | None:
        state = raw.get("state", "")
        date_str = raw.get("date_str", "")
        if not state or not date_str:
            return None

        try:
            parsed = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            logger.warning(f"Ballotpedia: could not parse date '{date_str}' for {state}")
            return None

        if parsed < date.today():
            return None

        return {
            "id": uuid.uuid4(),
            "external_id": f"ballotpedia_primary_{slugify(state)}_{parsed.year}",
            "title": f"{state} Primary Election",
            "description": None,
            "start_date": parsed,
            "end_date": None,
            "is_all_day": True,
            "category_id": self._slug_to_id.get("elections"),
            "country_code": "US",
            "region": state,
            "source_url": URL,
            "image_url": None,
            "popularity_score": None,
        }
