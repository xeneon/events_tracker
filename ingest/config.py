"""Standalone settings for the ingest CLI."""

from pathlib import Path

from pydantic_settings import BaseSettings

# Search for .env: CWD, next to this package, then walk up to 3 levels
_this_dir = Path(__file__).resolve().parent
_candidates = [
    Path.cwd() / ".env",             # current working directory
    _this_dir / ".env",              # inside the ingest/ folder
    _this_dir.parent / ".env",       # one level up (e.g. backend/)
    _this_dir.parents[1] / ".env",   # two levels up (e.g. project root)
]
_env_file = next((p for p in _candidates if p.exists()), ".env")


class Settings(BaseSettings):
    DATABASE_URL: str
    CALENDARIFIC_API_KEY: str = ""
    TRAKT_CLIENT_ID: str = ""
    LASTFM_API_KEY: str = ""
    GOOGLE_SHEET_ID: str = ""
    GOOGLE_SHEET_TAB: str = "Sheet1"
    GOOGLE_CREDENTIALS_FILE: str = ""

    model_config = {"env_file": str(_env_file), "extra": "ignore"}


settings = Settings()
