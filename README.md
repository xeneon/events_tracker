# Events Tracker

Ingests upcoming events from multiple sources into PostgreSQL and exports them to Google Sheets.

## Quickstart (Docker)

```bash
git clone <repo-url>
cd events_tracker
docker compose up -d
```

Web UI at **http://localhost:8080**. Postgres and all config persist across restarts via named Docker volumes.

Configure API keys at `http://localhost:8080/config`.

## Data Sources

| Ingester | Source | What it fetches |
|---|---|---|
| Calendarific | calendarific.com API | US holidays (federal, state, observances) — current + next year |
| Trakt | trakt.tv API | Top 100 anticipated movies & TV shows + season premieres |
| IGDB | igdb.com API (via Twitch OAuth) | Upcoming games ranked by "Want to Play" anticipation |
| Wikipedia Albums | Wikipedia + Last.fm | Music album releases with listener counts |

## Web UI

- **Home** — run individual ingesters or all at once, live log streaming, per-source status badges
- **Export to Sheets** — standalone button to push current DB contents to Google Sheets without re-running ingesters
- **Config** — set API keys, Google Sheets credentials, and customize the export SQL query

## Google Sheets Export

Exports a ranked subset of events to a configured sheet tab. The default query selects:
- Top 15 events per category by `impact_level`
- All events with `impact_level >= 50`
- Date range: current month through end of current year

The export SQL is fully editable in the Config page and can return any columns — column names from the query are used as the sheet header row.

## CLI Usage

The `ingest` package also works standalone without Docker:

```bash
pip install -r requirements.txt

python -m ingest --list
python -m ingest calendarific
python -m ingest trakt --dry-run
python -m ingest --all                   # all ingesters + export
python -m ingest.export_sheets --dry-run
```

Requires a `.env` file at project root. See `.env.example` for required variables.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `CALENDARIFIC_API_KEY` | For holidays | [calendarific.com](https://calendarific.com) |
| `TRAKT_CLIENT_ID` | For movies/TV | [trakt.tv/oauth/applications](https://trakt.tv/oauth/applications) |
| `TWITCH_CLIENT_ID` | For games | Twitch app credentials (used for IGDB OAuth) |
| `TWITCH_CLIENT_SECRET` | For games | Twitch app credentials |
| `LASTFM_API_KEY` | For albums | [last.fm/api](https://www.last.fm/api) |
| `GOOGLE_SHEET_ID` | For export | Sheet ID from the Google Sheets URL |
| `GOOGLE_SHEET_TAB` | For export | Tab name (default: `Sheet1`) |
| `GOOGLE_CREDENTIALS_FILE` | For export | Path to service account JSON |

In Docker, all keys except `DATABASE_URL` are set via the Config page and persisted to the `config_data` volume.

## Popularity Scoring

Each event stores two fields:

- **`popularity_score`** — raw metric from the source (Last.fm listeners, IGDB Want-to-Play × 1M, Trakt list count/votes). Preserved as-is.
- **`impact_level`** (0–100) — sqrt-scaled relative to the highest value in the same ingestion batch. Enables cross-category comparison; 100 = category leader.

## License

MIT
