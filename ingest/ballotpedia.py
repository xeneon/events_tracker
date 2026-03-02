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
            desc_idx = headers.index("description") if "description" in headers else None
            max_idx = max(state_idx, date_idx)
            for row in table.find_all("tr")[1:]:  # skip header
                cells = row.find_all(["td", "th"])
                if len(cells) <= max_idx:
                    continue
                state = cells[state_idx].get_text(strip=True)
                date_str = cells[date_idx].get_text(strip=True)
                description = cells[desc_idx].get_text(strip=True) if desc_idx is not None else ""
                if state and date_str:
                    results.append({"state": state, "date_str": date_str, "description": description})

        logger.info(f"Ballotpedia: found {len(results)} primary dates")
        return results

    def normalize(self, raw: dict) -> dict | None:
        state = raw.get("state", "")
        date_str = raw.get("date_str", "")
        description = raw.get("description", "")
        if not state or not date_str:
            return None

        # Skip party conventions and other non-primary events.
        # The table mixes primary elections with party conventions, Green/Libertarian
        # party events, etc. — we only want rows that are actual primary elections.
        if description and "primary" not in description.lower():
            return None

        try:
            parsed = datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            logger.warning(f"Ballotpedia: could not parse date '{date_str}' for {state}")
            return None

        if parsed < date.today():
            return None

        is_runoff = "runoff" in description.lower()
        id_suffix = "runoff" if is_runoff else "primary"
        title = f"{state} Primary Runoff Election" if is_runoff else f"{state} Primary Election"

        return {
            "id": uuid.uuid4(),
            "external_id": f"ballotpedia_{id_suffix}_{slugify(state)}_{parsed.year}",
            "title": title,
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
