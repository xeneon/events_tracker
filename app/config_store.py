"""Read/write /config/config.json and generate .env for ingest settings."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/config"))

_CONFIG_KEYS = [
    "CALENDARIFIC_API_KEY",
    "TRAKT_CLIENT_ID",
    "TWITCH_CLIENT_ID",
    "TWITCH_CLIENT_SECRET",
    "LASTFM_API_KEY",
    "GOOGLE_SHEET_ID",
    "GOOGLE_SHEET_TAB",
]


def load_config() -> dict:
    """Read config.json, returning empty strings for missing keys."""
    config_path = CONFIG_DIR / "config.json"
    if not config_path.exists():
        return {key: "" for key in _CONFIG_KEYS}
    with open(config_path) as f:
        data = json.load(f)
    return {key: data.get(key, "") for key in _CONFIG_KEYS}


def save_config(data: dict, google_creds_json: str | None = None) -> None:
    """Write config.json and regenerate .env; optionally save Google credentials."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config_data = {key: data.get(key, "") for key in _CONFIG_KEYS}
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
