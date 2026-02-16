"""Curated fashion week and major fashion events ingester."""

import logging
import uuid
from datetime import date

from .base import BaseIngester, slugify

logger = logging.getLogger(__name__)

# Curated fashion events for 2026.
# Sources: Fédération de la Haute Couture et de la Mode, Camera Nazionale
# della Moda Italiana, CFDA, British Fashion Council, and industry calendars.
FASHION_EVENTS_2026: list[dict] = [
    # ── January 2026 ──────────────────────────────────────────────
    {
        "name": "Pitti Uomo Florence",
        "description": (
            "Pitti Immagine Uomo — the world's leading menswear trade show "
            "featuring designer collections, emerging talent, and industry "
            "events in Florence's Fortezza da Basso."
        ),
        "start": "2026-01-13",
        "end": "2026-01-16",
        "city": "Florence",
        "country": "IT",
        "season": "Fall/Winter 2026-27 Menswear",
        "impact": 4,
        "popularity": 85,
        "url": "https://www.pittimmagine.com/en/corporate/fairs/pitti-uomo",
    },
    {
        "name": "Milan Men's Fashion Week",
        "description": (
            "Milano Moda Uomo — Fall/Winter 2026-27 menswear runway shows "
            "organized by Camera Nazionale della Moda Italiana."
        ),
        "start": "2026-01-16",
        "end": "2026-01-20",
        "city": "Milan",
        "country": "IT",
        "season": "Fall/Winter 2026-27 Menswear",
        "impact": 5,
        "popularity": 90,
        "url": "https://www.cameramoda.it/en/",
    },
    {
        "name": "Paris Men's Fashion Week",
        "description": (
            "Paris Fashion Week Homme — Fall/Winter 2026-27 menswear "
            "collections presented by the Fédération de la Haute Couture "
            "et de la Mode."
        ),
        "start": "2026-01-20",
        "end": "2026-01-25",
        "city": "Paris",
        "country": "FR",
        "season": "Fall/Winter 2026-27 Menswear",
        "impact": 5,
        "popularity": 92,
        "url": "https://www.fhcm.paris/en",
    },
    {
        "name": "Paris Haute Couture Week",
        "description": (
            "Spring/Summer 2026 Haute Couture shows — the pinnacle of "
            "fashion craftsmanship, featuring houses like Chanel, Dior, "
            "Valentino, and Schiaparelli."
        ),
        "start": "2026-01-26",
        "end": "2026-01-29",
        "city": "Paris",
        "country": "FR",
        "season": "Spring/Summer 2026 Couture",
        "impact": 5,
        "popularity": 95,
        "url": "https://www.fhcm.paris/en",
    },
    {
        "name": "Copenhagen Fashion Week",
        "description": (
            "Scandinavia's largest fashion event showcasing Nordic design, "
            "sustainability-focused collections, and emerging designers."
        ),
        "start": "2026-01-26",
        "end": "2026-01-30",
        "city": "Copenhagen",
        "country": "DK",
        "season": "Autumn/Winter 2026",
        "impact": 3,
        "popularity": 70,
        "url": "https://copenhagenfashionweek.com/",
    },
    # ── February–March 2026 ───────────────────────────────────────
    {
        "name": "New York Fashion Week",
        "description": (
            "NYFW Fall/Winter 2026 — one of the Big Four fashion weeks, "
            "featuring American and international designers at Spring Studios "
            "and other venues across Manhattan."
        ),
        "start": "2026-02-11",
        "end": "2026-02-16",
        "city": "New York",
        "country": "US",
        "season": "Fall/Winter 2026",
        "impact": 5,
        "popularity": 95,
        "url": "https://cfda.com/",
    },
    {
        "name": "London Fashion Week",
        "description": (
            "LFW Fall/Winter 2026 — organized by the British Fashion "
            "Council, showcasing British and international talent at "
            "180 The Strand and across London."
        ),
        "start": "2026-02-19",
        "end": "2026-02-23",
        "city": "London",
        "country": "GB",
        "season": "Fall/Winter 2026",
        "impact": 5,
        "popularity": 93,
        "url": "https://www.londonfashionweek.co.uk/",
    },
    {
        "name": "Milan Women's Fashion Week",
        "description": (
            "Milano Moda Donna — Fall/Winter 2026-27 womenswear runway "
            "shows featuring top Italian and international fashion houses."
        ),
        "start": "2026-02-24",
        "end": "2026-03-02",
        "city": "Milan",
        "country": "IT",
        "season": "Fall/Winter 2026-27",
        "impact": 5,
        "popularity": 94,
        "url": "https://www.cameramoda.it/en/",
    },
    {
        "name": "Paris Women's Fashion Week",
        "description": (
            "Paris Fashion Week Prêt-à-Porter — Fall/Winter 2026-27 "
            "womenswear collections, the climax of the Big Four fashion "
            "month circuit."
        ),
        "start": "2026-03-02",
        "end": "2026-03-10",
        "city": "Paris",
        "country": "FR",
        "season": "Fall/Winter 2026-27",
        "impact": 5,
        "popularity": 98,
        "url": "https://www.fhcm.paris/en",
    },
    # ── April 2026 ────────────────────────────────────────────────
    {
        "name": "NYFW Bridal",
        "description": (
            "New York Bridal Fashion Week — Spring 2027 bridal collections "
            "featuring major designers and emerging bridal labels."
        ),
        "start": "2026-04-08",
        "end": "2026-04-10",
        "city": "New York",
        "country": "US",
        "season": "Spring 2027 Bridal",
        "impact": 3,
        "popularity": 65,
        "url": "https://cfda.com/",
    },
    # ── May 2026 ──────────────────────────────────────────────────
    {
        "name": "Met Gala 2026",
        "description": (
            "The Metropolitan Museum of Art's annual Costume Institute "
            "Gala — 2026 theme: 'Costume Art'. Co-chaired by Beyoncé, "
            "Nicole Kidman, and Venus Williams."
        ),
        "start": "2026-05-04",
        "end": None,
        "city": "New York",
        "country": "US",
        "season": None,
        "impact": 5,
        "popularity": 100,
        "url": "https://www.metmuseum.org/about-the-met/collection-areas/the-costume-institute",
    },
    # ── June–July 2026 ────────────────────────────────────────────
    {
        "name": "Milan Men's Fashion Week",
        "description": (
            "Milano Moda Uomo — Spring/Summer 2027 menswear runway shows "
            "organized by Camera Nazionale della Moda Italiana."
        ),
        "start": "2026-06-19",
        "end": "2026-06-23",
        "city": "Milan",
        "country": "IT",
        "season": "Spring/Summer 2027 Menswear",
        "impact": 5,
        "popularity": 88,
        "url": "https://www.cameramoda.it/en/",
    },
    {
        "name": "Paris Men's Fashion Week",
        "description": (
            "Paris Fashion Week Homme — Spring/Summer 2027 menswear "
            "collections presented by the Fédération de la Haute Couture "
            "et de la Mode."
        ),
        "start": "2026-06-23",
        "end": "2026-06-28",
        "city": "Paris",
        "country": "FR",
        "season": "Spring/Summer 2027 Menswear",
        "impact": 5,
        "popularity": 90,
        "url": "https://www.fhcm.paris/en",
    },
    {
        "name": "Paris Haute Couture Week",
        "description": (
            "Fall/Winter 2026-27 Haute Couture shows — the pinnacle of "
            "fashion craftsmanship, featuring the world's most prestigious "
            "fashion houses."
        ),
        "start": "2026-07-06",
        "end": "2026-07-09",
        "city": "Paris",
        "country": "FR",
        "season": "Fall/Winter 2026-27 Couture",
        "impact": 5,
        "popularity": 95,
        "url": "https://www.fhcm.paris/en",
    },
    # ── September–October 2026 ────────────────────────────────────
    {
        "name": "New York Fashion Week",
        "description": (
            "NYFW Spring/Summer 2027 — runway shows and presentations "
            "featuring American and international designers across Manhattan."
        ),
        "start": "2026-09-09",
        "end": "2026-09-14",
        "city": "New York",
        "country": "US",
        "season": "Spring/Summer 2027",
        "impact": 5,
        "popularity": 95,
        "url": "https://cfda.com/",
    },
    {
        "name": "London Fashion Week",
        "description": (
            "LFW Spring/Summer 2027 — organized by the British Fashion "
            "Council, showcasing emerging and established British talent."
        ),
        "start": "2026-09-17",
        "end": "2026-09-21",
        "city": "London",
        "country": "GB",
        "season": "Spring/Summer 2027",
        "impact": 5,
        "popularity": 93,
        "url": "https://www.londonfashionweek.co.uk/",
    },
    {
        "name": "Milan Women's Fashion Week",
        "description": (
            "Milano Moda Donna — Spring/Summer 2027 womenswear collections "
            "from top Italian and international fashion houses."
        ),
        "start": "2026-09-22",
        "end": "2026-09-28",
        "city": "Milan",
        "country": "IT",
        "season": "Spring/Summer 2027",
        "impact": 5,
        "popularity": 94,
        "url": "https://www.cameramoda.it/en/",
    },
    {
        "name": "Paris Women's Fashion Week",
        "description": (
            "Paris Fashion Week Prêt-à-Porter — Spring/Summer 2027 "
            "womenswear collections, the grand finale of fashion month."
        ),
        "start": "2026-09-28",
        "end": "2026-10-06",
        "city": "Paris",
        "country": "FR",
        "season": "Spring/Summer 2027",
        "impact": 5,
        "popularity": 98,
        "url": "https://www.fhcm.paris/en",
    },
]


class FashionWeeksIngester(BaseIngester):
    """Ingests curated fashion week and major fashion event data."""

    async def fetch_events(self) -> list[dict]:
        """Return curated static event data."""
        logger.info(
            f"Fashion Weeks: returning {len(FASHION_EVENTS_2026)} curated events"
        )
        return list(FASHION_EVENTS_2026)

    def normalize(self, raw: dict) -> dict | None:
        name = raw.get("name", "")
        start = raw.get("start")
        if not start:
            return None

        slug = slugify(name)
        category_id = self._slug_to_id.get(
            "fashion", self._slug_to_id.get("other")
        )

        season = raw.get("season")
        description = raw.get("description", "")
        if season:
            description = f"{season}.\n\n{description}"

        city = raw.get("city", "")
        region = city if city else None

        return {
            "id": uuid.uuid4(),
            "external_id": f"fashion_{slug}_{start}",
            "title": f"{name} ({season})" if season else name,
            "description": description,
            "start_date": start,
            "end_date": raw.get("end"),
            "is_all_day": True,
            "category_id": category_id,
            "impact_level": raw.get("impact", 3),
            "popularity_score": raw.get("popularity"),
            "country_code": raw.get("country"),
            "region": region,
            "source_url": raw.get("url"),
            "image_url": None,
        }
