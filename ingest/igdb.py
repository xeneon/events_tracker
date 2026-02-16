"""IGDB (Internet Game Database) ingester for upcoming video game releases."""

import logging
import re
import uuid
from datetime import date, datetime, timezone

import httpx

from .base import BaseIngester
from .config import settings

logger = logging.getLogger(__name__)

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_API_URL = "https://api.igdb.com/v4"

# PopScore popularity_type 2 = "Want to Play" (the live "Wants" metric on igdb.com)
WANT_TO_PLAY_TYPE = 2


def _want_to_play_to_impact(score: float) -> int:
    """Map Want to Play score (0-1 normalized) to impact level 1-5.

    Thresholds based on observed distribution of upcoming games:
      GTA VI ≈ 0.00158, top titles ≈ 0.0004-0.0006, mid ≈ 0.0001-0.0003
    """
    if score >= 0.001:
        return 5
    if score >= 0.0004:
        return 4
    if score >= 0.0002:
        return 3
    if score >= 0.0001:
        return 2
    return 1


def _get_date_qualifier(release_dates: list[dict], first_release_ts: int) -> str | None:
    """Return a qualifier like 'TBD', '2026', 'Q3 2026' if the date is approximate, else None."""
    # Find the release_date entry matching first_release_date
    human = None
    for rd in release_dates:
        if rd.get("date") == first_release_ts:
            human = rd.get("human", "")
            break

    if not human:
        # Fallback: use the first entry's human string
        if release_dates:
            human = release_dates[0].get("human", "")

    if not human:
        return None

    human = human.strip()
    if human.upper() == "TBD":
        return "release date TBD"
    # Year only, e.g. "2026"
    if re.fullmatch(r"\d{4}", human):
        return f"expected {human}"
    # Quarter, e.g. "Q3 2026"
    if re.fullmatch(r"Q[1-4]\s+\d{4}", human):
        return f"expected {human}"
    # Full date — no qualifier needed
    return None


async def _get_twitch_token(client: httpx.AsyncClient) -> str:
    """Fetch a fresh Twitch OAuth2 client credentials token."""
    resp = await client.post(TWITCH_TOKEN_URL, params={
        "client_id": settings.TWITCH_CLIENT_ID,
        "client_secret": settings.TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


class IGDBIngester(BaseIngester):
    async def fetch_events(self) -> list[dict]:
        client_id = settings.TWITCH_CLIENT_ID
        client_secret = settings.TWITCH_CLIENT_SECRET
        if not client_id or not client_secret:
            logger.error("TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET not set — skipping IGDB ingestion")
            return []

        async with httpx.AsyncClient(timeout=30) as client:
            token = await _get_twitch_token(client)
            headers = {
                "Client-ID": client_id,
                "Authorization": f"Bearer {token}",
            }

            today_ts = int(datetime.combine(date.today(), datetime.min.time(),
                                            tzinfo=timezone.utc).timestamp())

            # Step 1: Get upcoming games with hype (used as candidate filter)
            body = (
                "fields name, hypes, first_release_date, cover.url, "
                "genres.name, platforms.name, summary, "
                "involved_companies.company.name, involved_companies.publisher, "
                "release_dates.human, release_dates.date, "
                "url; "
                f"where first_release_date > {today_ts} & hypes > 0; "
                "sort hypes desc; "
                "limit 100;"
            )

            try:
                resp = await client.post(
                    f"{IGDB_API_URL}/games",
                    content=body,
                    headers=headers,
                )
                resp.raise_for_status()
                games = resp.json()
                logger.info(f"IGDB: fetched {len(games)} upcoming games")
            except Exception as exc:
                logger.error(f"IGDB games fetch failed: {exc}")
                return []

            # Step 2: Fetch "Want to Play" PopScore for these games
            game_ids = [g["id"] for g in games]
            want_to_play: dict[int, float] = {}

            # Batch in groups of 50 (IGDB where-in limit)
            for i in range(0, len(game_ids), 50):
                batch_ids = ",".join(str(gid) for gid in game_ids[i:i + 50])
                try:
                    resp = await client.post(
                        f"{IGDB_API_URL}/popularity_primitives",
                        content=(
                            "fields game_id, value; "
                            f"where popularity_type = {WANT_TO_PLAY_TYPE} "
                            f"& game_id = ({batch_ids}); "
                            "limit 100;"
                        ),
                        headers=headers,
                    )
                    resp.raise_for_status()
                    for p in resp.json():
                        want_to_play[p["game_id"]] = p["value"]
                except Exception as exc:
                    logger.warning(f"IGDB PopScore fetch failed for batch: {exc}")

            logger.info(f"IGDB: fetched Want to Play scores for {len(want_to_play)}/{len(games)} games")

            # Attach scores to games
            for game in games:
                game["_want_to_play"] = want_to_play.get(game["id"], 0.0)

            # Re-sort by Want to Play score (best metric), falling back to hypes
            games.sort(key=lambda g: (g["_want_to_play"], g.get("hypes", 0)), reverse=True)

        return games

    def normalize(self, raw: dict) -> dict | None:
        name = raw.get("name")
        igdb_id = raw.get("id")
        release_ts = raw.get("first_release_date")

        if not name or not igdb_id or not release_ts:
            return None

        release_date = datetime.fromtimestamp(release_ts, tz=timezone.utc).date()
        want_to_play = raw.get("_want_to_play", 0.0)

        # Scale to integer for storage (multiply by 1M for readable values)
        popularity_score = int(want_to_play * 1_000_000)

        # Detect date precision from the human-readable release date string
        date_qualifier = _get_date_qualifier(raw.get("release_dates") or [], release_ts)

        # Cover URL: IGDB returns //images.igdb.com/... — prepend https:
        cover = raw.get("cover")
        image_url = None
        if cover and cover.get("url"):
            url = cover["url"]
            # Upgrade to larger image (t_thumb -> t_cover_big)
            url = url.replace("t_thumb", "t_cover_big")
            image_url = f"https:{url}" if url.startswith("//") else url

        # Genres
        genres = raw.get("genres") or []
        genre_str = ", ".join(g["name"] for g in genres[:3])

        # Platforms
        platforms = raw.get("platforms") or []
        platform_str = ", ".join(p["name"] for p in platforms[:5])

        # Publisher
        publishers = [
            ic["company"]["name"]
            for ic in (raw.get("involved_companies") or [])
            if ic.get("publisher") and ic.get("company")
        ]
        publisher_str = ", ".join(publishers[:2])

        # Description
        summary = raw.get("summary") or ""
        desc_parts = []
        if genre_str:
            desc_parts.append(genre_str)
        if platform_str:
            desc_parts.append(platform_str)
        if publisher_str:
            desc_parts.append(publisher_str)
        description = " | ".join(desc_parts)
        if summary:
            description += f"\n\n{summary}"

        # Category
        category_id = self._slug_to_id.get("video-games", self._slug_to_id.get("other"))

        # Source URL
        source_url = raw.get("url")

        # Annotate title if release date is approximate
        title = name
        if date_qualifier:
            title = f"{name} ({date_qualifier})"

        return {
            "id": uuid.uuid4(),
            "external_id": f"igdb_{igdb_id}",
            "title": title,
            "description": description[:2000] if description else None,
            "start_date": release_date.isoformat(),
            "end_date": None,
            "is_all_day": True,
            "category_id": category_id,
            "impact_level": _want_to_play_to_impact(want_to_play),
            "popularity_score": popularity_score,
            "country_code": None,
            "region": None,
            "source_url": source_url,
            "image_url": image_url,
        }
