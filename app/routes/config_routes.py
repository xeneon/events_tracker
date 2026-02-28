"""Config page: GET/POST for API key settings."""

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import config_store

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/config")
async def config_get(request: Request, saved: bool = False):
    config = config_store.load_config()
    has_credentials = config_store.has_google_credentials()
    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "config": config,
            "has_credentials": has_credentials,
            "saved": saved,
        },
    )


@router.post("/config")
async def config_post(
    CALENDARIFIC_API_KEY: str = Form(default=""),
    TRAKT_CLIENT_ID: str = Form(default=""),
    TWITCH_CLIENT_ID: str = Form(default=""),
    TWITCH_CLIENT_SECRET: str = Form(default=""),
    LASTFM_API_KEY: str = Form(default=""),
    GOOGLE_SHEET_ID: str = Form(default=""),
    GOOGLE_SHEET_TAB: str = Form(default=""),
    google_credentials_json: str = Form(default=""),
):
    data = {
        "CALENDARIFIC_API_KEY": CALENDARIFIC_API_KEY,
        "TRAKT_CLIENT_ID": TRAKT_CLIENT_ID,
        "TWITCH_CLIENT_ID": TWITCH_CLIENT_ID,
        "TWITCH_CLIENT_SECRET": TWITCH_CLIENT_SECRET,
        "LASTFM_API_KEY": LASTFM_API_KEY,
        "GOOGLE_SHEET_ID": GOOGLE_SHEET_ID,
        "GOOGLE_SHEET_TAB": GOOGLE_SHEET_TAB,
    }
    creds = google_credentials_json.strip() if google_credentials_json else None
    config_store.save_config(data, google_creds_json=creds if creds else None)
    return RedirectResponse(url="/config?saved=1", status_code=303)
