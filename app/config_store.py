"""Read/write /config/config.json and generate .env for ingest settings."""

import json
import os
from pathlib import Path

from ingest.export_sheets import QUERY as _DEFAULT_QUERY_OBJ

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/config"))

DEFAULT_EXPORT_QUERY = _DEFAULT_QUERY_OBJ.text.strip()


def is_custom_export_query(config: dict) -> bool:
    """Return True if config's EXPORT_QUERY differs from the built-in default."""
    return config["EXPORT_QUERY"] != DEFAULT_EXPORT_QUERY

_CONFIG_KEYS = [
    "CALENDARIFIC_API_KEY",
    "CALENDARIFIC_COUNTRIES",
    "TRAKT_CLIENT_ID",
    "TRAKT_ANTICIPATED_LIMIT",
    "TRAKT_PREMIERE_WINDOW",
    "TWITCH_CLIENT_ID",
    "TWITCH_CLIENT_SECRET",
    "IGDB_LIMIT",
    "LASTFM_API_KEY",
    "WIKIPEDIA_ALBUMS_YEAR",
    "GOOGLE_SHEET_ID",
    "GOOGLE_SHEET_TAB",
]


def load_config() -> dict:
    """Read config.json, returning empty strings for missing keys."""
    config_path = CONFIG_DIR / "config.json"
    if not config_path.exists():
        result = {key: "" for key in _CONFIG_KEYS}
        result["EXPORT_QUERY"] = DEFAULT_EXPORT_QUERY
        return result
    with open(config_path) as f:
        data = json.load(f)
    result = {key: data.get(key, "") for key in _CONFIG_KEYS}
    result["EXPORT_QUERY"] = data.get("EXPORT_QUERY", DEFAULT_EXPORT_QUERY) or DEFAULT_EXPORT_QUERY
    return result


def save_config(data: dict, google_creds_json: str | None = None) -> None:
    """Write config.json and regenerate .env; optionally save Google credentials."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config_data = {key: data.get(key, "") for key in _CONFIG_KEYS}
    export_query = (data.get("EXPORT_QUERY") or "").strip().replace("\r\n", "\n")
    config_data["EXPORT_QUERY"] = export_query if export_query else DEFAULT_EXPORT_QUERY
    with open(CONFIG_DIR / "config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    env_lines = []
    for key in _CONFIG_KEYS:
        value = config_data.get(key, "")
        if value:
            env_lines.append(f"{key}={value}")

    if google_creds_json and google_creds_json.strip():
        with open(CONFIG_DIR / "google_credentials.json", "w") as f:
            f.write(google_creds_json)
        env_lines.append("GOOGLE_CREDENTIALS_FILE=/config/google_credentials.json")
    elif (CONFIG_DIR / "google_credentials.json").exists():
        env_lines.append("GOOGLE_CREDENTIALS_FILE=/config/google_credentials.json")

    with open(CONFIG_DIR / ".env", "w") as f:
        f.write("\n".join(env_lines) + "\n" if env_lines else "")


def has_google_credentials() -> bool:
    return (CONFIG_DIR / "google_credentials.json").exists()


def get_google_credentials_info() -> dict | None:
    """Return client_email and project_id from saved credentials, or None."""
    creds_path = CONFIG_DIR / "google_credentials.json"
    if not creds_path.exists():
        return None
    try:
        with open(creds_path) as f:
            data = json.load(f)
        return {
            "client_email": data.get("client_email", ""),
            "project_id": data.get("project_id", ""),
        }
    except Exception:
        return None
