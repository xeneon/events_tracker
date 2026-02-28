"""Per-scraper pages: run + inline log + configurable settings."""

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .. import config_store, runner
from . import templates

router = APIRouter()

SCRAPER_META: dict[str, dict] = {
    "calendarific": {
        "name": "Calendarific",
        "description": "Public holidays from the Calendarific API.",
        "guide": {
            "title": "How to get a Calendarific API key",
            "steps": [
                'Go to <a href="https://calendarific.com" target="_blank" rel="noopener">calendarific.com</a> and create a free account.',
                'After signing in, open your <strong>Dashboard</strong>.',
                'Copy the <strong>API key</strong> shown there and paste it into the field below.',
            ],
        },
        "fields": [
            {"name": "CALENDARIFIC_API_KEY", "label": "API Key", "type": "text",
             "placeholder": "Your Calendarific API key", "hint": ""},
            {"name": "CALENDARIFIC_COUNTRIES", "label": "Countries", "type": "text",
             "placeholder": "US", "hint": "Comma-separated ISO 3166-1 alpha-2 country codes, e.g. US,GB,CA. Defaults to US only."},
        ],
    },
    "igdb": {
        "name": "IGDB",
        "description": "Upcoming video game releases via IGDB (Twitch auth).",
        "guide": {
            "title": "How to get Twitch / IGDB credentials",
            "steps": [
                'Go to <a href="https://dev.twitch.tv/console" target="_blank" rel="noopener">dev.twitch.tv/console</a> and sign in (create a free Twitch account if needed).',
                'Click <strong>Register Your Application</strong>.',
                'Enter any name (e.g. "Events Tracker"), set the OAuth Redirect URL to <code>http://localhost</code>, and choose any Category.',
                'Click <strong>Create</strong>, then open the app you just created.',
                'Copy the <strong>Client ID</strong>. Then click <strong>New Secret</strong> to generate and copy the <strong>Client Secret</strong>.',
            ],
        },
        "fields": [
            {"name": "TWITCH_CLIENT_ID", "label": "Twitch Client ID", "type": "text",
             "placeholder": "Your Twitch client ID", "hint": "IGDB uses Twitch for authentication. Both fields are required."},
            {"name": "TWITCH_CLIENT_SECRET", "label": "Twitch Client Secret", "type": "password",
             "placeholder": "Your Twitch client secret", "hint": ""},
            {"name": "IGDB_LIMIT", "label": "Fetch limit", "type": "number",
             "placeholder": "100", "hint": "Maximum number of games to fetch, sorted by hype score. Default: 100."},
        ],
    },
    "trakt": {
        "name": "Trakt",
        "description": "Anticipated movies and season premieres from Trakt.",
        "guide": {
            "title": "How to get a Trakt Client ID",
            "steps": [
                'Go to <a href="https://trakt.tv" target="_blank" rel="noopener">trakt.tv</a> and sign in (create a free account if needed).',
                'Open <a href="https://trakt.tv/oauth/applications/new" target="_blank" rel="noopener">trakt.tv/oauth/applications/new</a>.',
                'Enter any name and set Redirect URI to <code>http://localhost</code>. Click <strong>Save App</strong>.',
                'Copy the <strong>Client ID</strong> shown on the page.',
            ],
        },
        "fields": [
            {"name": "TRAKT_CLIENT_ID", "label": "Client ID", "type": "text",
             "placeholder": "Your Trakt client ID", "hint": ""},
            {"name": "TRAKT_ANTICIPATED_LIMIT", "label": "Anticipated limit", "type": "number",
             "placeholder": "100", "hint": "Maximum number of anticipated movies and shows to fetch. Default: 100."},
            {"name": "TRAKT_PREMIERE_WINDOW", "label": "Premiere window (days)", "type": "number",
             "placeholder": "180", "hint": "How many days ahead to look for upcoming season premieres. Default: 180."},
        ],
    },
    "wikipedia-albums": {
        "name": "Wikipedia Albums",
        "description": "Upcoming music releases from Wikipedia + Last.fm listener counts.(Slow API, due to rate limits - takes about 2-3 minutes to run)",
        "guide": {
            "title": "How to get a Last.fm API key",
            "steps": [
                'Go to <a href="https://www.last.fm" target="_blank" rel="noopener">last.fm</a> and sign in (create a free account if needed).',
                'Open <a href="https://www.last.fm/api/account/create" target="_blank" rel="noopener">last.fm/api/account/create</a>.',
                'Fill in any application name and submit the form.',
                'Copy the <strong>API key</strong> shown on the confirmation page.',
            ],
        },
        "fields": [
            {"name": "LASTFM_API_KEY", "label": "Last.fm API Key", "type": "text",
             "placeholder": "Your Last.fm API key", "hint": "Used to fetch listener counts for each artist. Without this key, popularity scores will be missing."},
            {"name": "WIKIPEDIA_ALBUMS_YEAR", "label": "Year", "type": "number",
             "placeholder": str(date.today().year), "hint": "Leave blank to use the current year."},
        ],
    },
}


@router.get("/scraper/{alias}")
async def scraper_get(request: Request, alias: str, saved: bool = False):
    if alias not in SCRAPER_META:
        return RedirectResponse("/", status_code=302)
    meta = SCRAPER_META[alias]
    config = config_store.load_config()
    statuses = runner.get_all_statuses()
    return templates.TemplateResponse("scraper.html", {
        "request": request,
        "alias": alias,
        "meta": meta,
        "config": config,
        "status": statuses.get(alias, {"state": "idle"}),
        "saved": saved,
        "active_page": f"scraper_{alias}",
    })


@router.post("/scraper/{alias}/save")
async def scraper_save(request: Request, alias: str):
    if alias not in SCRAPER_META:
        return RedirectResponse("/", status_code=302)
    meta = SCRAPER_META[alias]
    form = await request.form()
    # Load full config, overwrite only this scraper's fields
    config = config_store.load_config()
    for field in meta["fields"]:
        key = field["name"]
        config[key] = form.get(key, "")
    config_store.save_config(config)
    return RedirectResponse(f"/scraper/{alias}?saved=1", status_code=303)
