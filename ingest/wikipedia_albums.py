"""Wikipedia album releases ingester with Last.fm enrichment."""

import asyncio
import logging
import re
import uuid
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from .base import BaseIngester, slugify
from .config import settings

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
LASTFM_API = "https://ws.audioscrobbler.com/2.0/"


class WikipediaAlbumsIngester(BaseIngester):
    def __init__(self, session, source):
        super().__init__(session, source)
        self._lastfm_cache: dict[str, dict | None] = {}

    async def fetch_events(self) -> list[dict]:
        year = date.today().year
        page_title = f"List_of_{year}_albums"

        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch rendered HTML from MediaWiki API
            resp = await client.get(WIKIPEDIA_API, params={
                "action": "parse",
                "page": page_title,
                "prop": "text",
                "format": "json",
            }, headers={"User-Agent": "EventsTracker/1.0 (album ingester)"})
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                logger.error(f"Wikipedia API error: {data['error']}")
                return []

            html = data["parse"]["text"]["*"]
            albums = self._parse_html_tables(html, year)
            logger.info(f"Wikipedia: parsed {len(albums)} albums from {page_title}")

            # Enrich with Last.fm data
            await self._enrich_with_lastfm(client, albums)

        return albums

    def _parse_html_tables(self, html: str, year: int) -> list[dict]:
        """Parse all monthly wikitables from the page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        albums: list[dict] = []

        for table in tables:
            caption = table.find("caption")
            if not caption:
                continue

            caption_text = caption.get_text(strip=True)

            # Skip TBA table
            if "sometime" in caption_text.lower():
                logger.debug(f"Skipping TBA table: {caption_text}")
                continue

            # Extract month from caption like "List of albums released in January 2025"
            month_name = None
            for m in MONTH_NAMES:
                if m in caption_text:
                    month_name = m
                    break

            if not month_name:
                logger.warning(f"Could not extract month from caption: {caption_text}")
                continue

            month_albums = self._parse_monthly_table(table, month_name, year)
            albums.extend(month_albums)

        return albums

    def _parse_monthly_table(self, table: Tag, month_name: str, year: int) -> list[dict]:
        """Parse a single monthly table, handling rowspan on date cells."""
        albums: list[dict] = []
        rows = table.find_all("tr")
        current_date_text = None
        rowspan_remaining = 0

        for row in rows:
            # Skip nav rows (td with colspan)
            first_td = row.find("td")
            if first_td and first_td.get("colspan"):
                continue

            # Skip header rows
            ths = row.find_all("th", scope="col")
            if ths:
                continue

            # Check for a date <th> cell (scope="row")
            date_th = row.find("th", scope="row")
            cells = row.find_all("td")

            if date_th:
                # This row has a date header
                current_date_text = self._extract_text(date_th)
                rowspan = date_th.get("rowspan")
                rowspan_remaining = int(rowspan) - 1 if rowspan else 0

                # Cells after the th: artist, album, genre, label, ref
                if len(cells) < 4:
                    continue
                artist_cell, album_cell, genre_cell, label_cell = cells[0], cells[1], cells[2], cells[3]
            elif rowspan_remaining > 0:
                # Continuation row (no date th, uses previous date)
                rowspan_remaining -= 1
                if len(cells) < 4:
                    continue
                artist_cell, album_cell, genre_cell, label_cell = cells[0], cells[1], cells[2], cells[3]
            else:
                continue

            if not current_date_text:
                continue

            # Parse date
            release_date = self._parse_date(current_date_text, month_name, year)
            if not release_date:
                continue

            artist = self._extract_text(artist_cell)
            album_title = self._extract_album_title(album_cell)
            genre = self._extract_text(genre_cell)
            label = self._extract_text(label_cell)

            if not artist or not album_title:
                continue

            # Skip TBA album titles
            if album_title.upper() == "TBA":
                continue

            # Extract URLs
            album_url = self._extract_wiki_url(album_cell)
            artist_url = self._extract_wiki_url(artist_cell)

            albums.append({
                "artist": artist,
                "album": album_title,
                "genre": genre,
                "label": label,
                "release_date": release_date,
                "album_url": album_url,
                "artist_url": artist_url,
                "_primary_artist": self._extract_primary_artist(artist),
                "_listeners": None,
                "_lastfm_url": None,
                "_lastfm_image": None,
            })

        return albums

    def _parse_date(self, text: str, month_name: str, year: int) -> date | None:
        """Parse date text like 'January 10' or 'January10' into a date object."""
        # The text from the th cell typically looks like "January\n10" or "January 10"
        # Extract the day number
        day_match = re.search(r"(\d+)", text)
        if not day_match:
            return None
        day = int(day_match.group(1))
        month = MONTH_NAMES.index(month_name) + 1
        try:
            return date(year, month, day)
        except ValueError:
            logger.warning(f"Invalid date: {month_name} {day}, {year}")
            return None

    @staticmethod
    def _extract_text(cell: Tag) -> str:
        """Extract clean text from a cell, removing reference superscripts."""
        # Remove <sup class="reference"> elements
        for sup in cell.find_all("sup", class_="reference"):
            sup.decompose()
        # Use separator to avoid concatenation of adjacent inline elements
        text = cell.get_text(separator=" ", strip=True)
        # Clean up spacing artifacts: collapse multiple spaces, fix " ,"
        text = re.sub(r" +", " ", text)
        text = re.sub(r" ([,;])", r"\1", text)
        return text

    @staticmethod
    def _extract_album_title(cell: Tag) -> str:
        """Extract album title from the <i> tag in a cell."""
        # Remove reference superscripts first
        for sup in cell.find_all("sup", class_="reference"):
            sup.decompose()

        italic = cell.find("i")
        if italic:
            return italic.get_text(strip=True)
        # Fallback to cell text
        return cell.get_text(strip=True)

    @staticmethod
    def _extract_wiki_url(cell: Tag) -> str | None:
        """Extract the first Wikipedia article URL from a cell."""
        link = cell.find("a", href=True)
        if link:
            href = link["href"]
            if href.startswith("/wiki/") and ":" not in href:
                return f"https://en.wikipedia.org{href}"
        return None

    @staticmethod
    def _extract_primary_artist(text: str) -> str:
        """Extract the primary artist name for Last.fm lookup.
        Strips parentheticals and takes the first artist from collaborations."""
        # Remove parentheticals like "(band)" or "(musician)"
        text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()
        # Split on collaboration markers and take the first
        for sep in [" featuring ", " feat. ", " ft. ", " and ", " & ", " with ", " x "]:
            if sep in text.lower():
                idx = text.lower().index(sep)
                text = text[:idx].strip()
                break
        return text

    async def _enrich_with_lastfm(self, client: httpx.AsyncClient, albums: list[dict]):
        """Enrich albums with Last.fm artist data (listeners, URL, image)."""
        api_key = settings.LASTFM_API_KEY
        if not api_key:
            logger.warning("LASTFM_API_KEY not set — skipping Last.fm enrichment")
            return

        # Collect unique primary artists
        unique_artists = set()
        for album in albums:
            unique_artists.add(album["_primary_artist"])

        logger.info(f"Last.fm: enriching {len(unique_artists)} unique artists")
        enriched = 0

        for artist_name in unique_artists:
            if artist_name in self._lastfm_cache:
                continue

            try:
                resp = await client.get(LASTFM_API, params={
                    "method": "artist.getinfo",
                    "artist": artist_name,
                    "api_key": api_key,
                    "format": "json",
                })
                resp.raise_for_status()
                data = resp.json()

                artist_data = data.get("artist")
                if artist_data:
                    listeners = int(artist_data.get("stats", {}).get("listeners", 0))
                    url = artist_data.get("url")
                    # Get extralarge image
                    images = artist_data.get("image", [])
                    image_url = None
                    for img in images:
                        if img.get("size") == "extralarge" and img.get("#text"):
                            image_url = img["#text"]
                            break

                    self._lastfm_cache[artist_name] = {
                        "listeners": listeners,
                        "url": url,
                        "image": image_url,
                    }
                    enriched += 1
                else:
                    self._lastfm_cache[artist_name] = None

            except Exception as exc:
                logger.debug(f"Last.fm lookup failed for '{artist_name}': {exc}")
                self._lastfm_cache[artist_name] = None

            # Rate limit: 200ms between requests
            await asyncio.sleep(0.2)

        logger.info(f"Last.fm: enriched {enriched}/{len(unique_artists)} artists")

        # Attach enrichment data to albums
        for album in albums:
            cached = self._lastfm_cache.get(album["_primary_artist"])
            if cached:
                album["_listeners"] = cached["listeners"]
                album["_lastfm_url"] = cached["url"]
                album["_lastfm_image"] = cached["image"]

    def normalize(self, raw: dict) -> dict | None:
        artist = raw.get("artist", "")
        album = raw.get("album", "")
        release_date = raw.get("release_date")

        if not artist or not album or not release_date:
            return None

        artist_slug = slugify(artist, separator="_")
        album_slug = slugify(album, separator="_")
        external_id = f"wiki_album_{artist_slug}_{album_slug}_{release_date.isoformat()}"

        title = f"{album} – {artist}"
        if len(title) > 300:
            title = title[:297] + "..."

        # Build description
        desc_parts = []
        genre = raw.get("genre")
        label = raw.get("label")
        listeners = raw.get("_listeners")
        if genre:
            desc_parts.append(genre)
        if label:
            desc_parts.append(label)
        if listeners:
            desc_parts.append(f"{listeners:,} Last.fm listeners")
        description = " | ".join(desc_parts) if desc_parts else None

        # Category
        category_id = self._slug_to_id.get("music-releases", self._slug_to_id.get("other"))

        # Source URL: prefer album Wikipedia URL, then Last.fm
        source_url = raw.get("album_url") or raw.get("_lastfm_url") or raw.get("artist_url")

        return {
            "id": uuid.uuid4(),
            "external_id": external_id[:300],
            "title": title,
            "description": description[:2000] if description else None,
            "start_date": release_date.isoformat(),
            "end_date": None,
            "is_all_day": True,
            "category_id": category_id,
            "popularity_score": listeners or 0,
            "country_code": None,
            "region": None,
            "source_url": source_url,
            "image_url": raw.get("_lastfm_image"),
        }
