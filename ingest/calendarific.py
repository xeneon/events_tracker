"""Calendarific US holiday ingester."""

import logging
import uuid
from collections import defaultdict
from datetime import date

import httpx

from .base import BaseIngester
from .config import settings

logger = logging.getLogger(__name__)

# primary_type → category slug (used for dedup priority and category mapping)
PRIMARY_TYPE_TO_SLUG: dict[str, str] = {
    "Federal Holiday": "federal-holiday",
    "State Holiday": "state-holiday",
    "State Legal Holiday": "state-holiday",
    "Local holiday": "state-holiday",
    "State Observance": "observance",
    "Local observance": "observance",
    "Observance": "observance",
    "United Nations observance": "observance",
    "Worldwide observance": "observance",
    "Annual Monthly Observance": "observance",
    "Season": "observance",
    "Clock change/Daylight Saving Time": "observance",
    "Christian": "religious",
    "Muslim": "religious",
    "Jewish holiday": "religious",
    "Jewish commemoration": "religious",
    "Hindu Holiday": "religious",
    "Orthodox": "religious",
    "Sporting event": "other",
}

# Dedup priority — lower = higher priority (kept when duplicates exist)
DEDUP_PRIORITY: dict[str, int] = {
    "Federal Holiday": 0,
    "State Legal Holiday": 1,
    "State Holiday": 2,
    "State Observance": 3,
    "Local holiday": 4,
    "Local observance": 5,
}

class CalendarificIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        api_key = settings.CALENDARIFIC_API_KEY
        if not api_key:
            logger.error("CALENDARIFIC_API_KEY not set — skipping ingestion")
            return []

        countries = [c.strip() for c in settings.calendarific_countries.split(",") if c.strip()]
        if not countries:
            countries = ["US"]

        current_year = date.today().year
        years = [current_year, current_year + 1]

        all_deduped: list[dict] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for country in countries:
                raw_events: list[dict] = []
                for year in years:
                    url = "https://calendarific.com/api/v2/holidays"
                    params = {
                        "api_key": api_key,
                        "country": country,
                        "year": year,
                    }
                    try:
                        resp = await client.get(url, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                        holidays = data.get("response", {}).get("holidays", [])
                        for h in holidays:
                            h["_country"] = country
                        raw_events.extend(holidays)
                    except Exception as exc:
                        logger.error(f"Calendarific fetch failed for {country}/{year}: {exc}")
                        continue

                # Deduplicate within this country: same holiday (by name+date) appears once.
                # Keying by name rather than urlid merges state/region variants
                # (e.g. rosh-hashana vs rosh-hashana-tx) into a single entry.
                grouped: dict[str, list[dict]] = defaultdict(list)
                for h in raw_events:
                    name_key = h.get("name", "unknown").lower()
                    date_iso = h.get("date", {}).get("iso", "")[:10]
                    key = f"{name_key}_{date_iso}"
                    grouped[key].append(h)

                deduped: list[dict] = []
                for entries in grouped.values():
                    entries.sort(
                        key=lambda x: DEDUP_PRIORITY.get(x.get("primary_type", ""), 99)
                    )
                    deduped.append(entries[0])

                logger.info(
                    f"Calendarific {country}: {len(raw_events)} raw → {len(deduped)} deduped"
                )
                all_deduped.extend(deduped)

        logger.info(
            f"Calendarific: {len(all_deduped)} total events across {len(countries)} countries"
        )
        return all_deduped

    def normalize(self, raw: dict) -> dict | None:
        holiday_date = raw.get("date", {}).get("iso", "")
        if not holiday_date:
            return None
        date_str = holiday_date[:10]

        name = raw.get("name", "Holiday")
        urlid = raw.get("urlid") or name.lower().replace(" ", "-")
        country = raw.get("_country", "US")

        primary_type = raw.get("primary_type", "")
        slug = PRIMARY_TYPE_TO_SLUG.get(primary_type, "other")
        category_id = self._slug_to_id.get(slug, self._slug_to_id.get("other"))

        # Build region from states — only for state-specific holidays
        states = raw.get("states")
        region = None
        if isinstance(states, list) and states:
            abbrevs = [s.get("abbrev", "") for s in states if isinstance(s, dict)]
            if abbrevs:
                region = ", ".join(abbrevs)
                if len(region) > 200:
                    region = region[:197] + "..."

        return {
            "id": uuid.uuid4(),
            "external_id": f"calendarific_{urlid}_{date_str}",
            "title": name,
            "description": raw.get("description"),
            "start_date": date_str,
            "end_date": None,
            "is_all_day": True,
            "category_id": category_id,
            "country_code": country,
            "region": region,
            "source_url": raw.get("canonical_url"),
            "image_url": None,
        }
