# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Events Tracker ingests events from multiple sources into PostgreSQL and exports them to Google Sheets. It has two interfaces:
- **Web UI** (`app/`) — FastAPI + Jinja2, runs via Docker, provides a browser-based control panel
- **CLI** (`ingest/`) — standalone, runs directly with `python -m ingest`

## Running with Docker (primary deployment)

```bash
docker compose build
docker compose up -d

# On remote Docker context
docker --context remote-server compose build web
docker --context remote-server compose up -d web
```

Web UI is at `http://localhost:8080`. Postgres runs as a container on a named volume (`pg_data`). Config (API keys) persists on a named volume (`config_data` → `/config`). Schema and seed data are created automatically on first startup.

**Do not run `docker compose down -v`** — this deletes both volumes (DB and config).

## CLI Usage (standalone, outside Docker)

```bash
python -m ingest --list
python -m ingest calendarific
python -m ingest trakt --dry-run
python -m ingest ballotpedia
python -m ingest --all                   # all ingesters + export
python -m ingest.export_sheets           # export only
python -m ingest.export_sheets --dry-run
```

Requires `.env` at project root (or `CONFIG_DIR/.env` in Docker). `DATABASE_URL` must be set; all API keys are optional per-ingester. Ballotpedia requires no API key.

## Architecture

### `ingest/` package

Self-contained ingestion library used by both the CLI and the web UI.

- `config.py` — pydantic-settings `Settings` singleton. Searches for `.env` starting at `CONFIG_DIR/.env`, then CWD, then walking up. **All submodules do `from .config import settings`** — they hold a reference to the same object. Configurable per-ingester parameters: `calendarific_countries`, `igdb_limit`, `trakt_anticipated_limit`, `trakt_premiere_window`, `wikipedia_albums_year`.
- `db.py` — async SQLAlchemy engine and `async_session_maker`, created at import time from `DATABASE_URL`.
- `models.py` — `Category`, `DataSource`, `Event` models. Upsert key: constraint `uq_events_source_external` on `(data_source_id, external_id)`.
- `base.py` — `BaseIngester` ABC. `run()` calls `fetch_events()` → `normalize()` → `_apply_log_scale()` → `upsert_events()`. All ingesters take `(session, source)` as constructor args.
- `export_sheets.py` — `fetch_rows()` returns `(headers, rows)` (column names come from query result, not hardcoded). `write_to_sheet(rows, headers)` uses those headers for the sheet header row and column count.
- `__main__.py` — CLI entry point. `SOURCE_ALIASES` maps CLI alias → ingester name. `INGESTERS` maps name → class.

### `app/` package

FastAPI web UI layered on top of `ingest/`.

- `main.py` — FastAPI app with lifespan that calls `seed.run_seed()` (idempotent `create_all` + seed categories/data_sources).
- `seed.py` — Seeds 10 categories and 5 data sources with `ON CONFLICT DO NOTHING`. Categories: federal-holiday, state-holiday, observance, religious, other, movies, tv-shows, video-games, music-releases, elections. Data sources: Calendarific, IGDB, Trakt, Wikipedia Albums, Ballotpedia.
- `config_store.py` — Reads/writes `/config/config.json` and regenerates `/config/.env`. `EXPORT_QUERY` is stored in `config.json` only (not `.env`, because multiline SQL breaks `.env` format). Exposes `_DEFAULT_EXPORT_QUERY` (from `ingest.export_sheets.QUERY.text`).
- `runner.py` — `start_run(source_alias)` creates an `asyncio.Queue`, launches a background task, returns a `run_id`. `_QueueHandler` attaches to root logger before each run and removes in `finally`. Runs are serialized via `asyncio.Semaphore(1)`. `stream_run(run_id)` is an async generator yielding raw SSE strings. **Settings reload**: `_reload_settings()` mutates `config_mod.settings` attributes in-place so all submodules see updated values; `DATABASE_URL` comes from the environment and is unaffected.
- `routes/home.py` — `GET /`, `POST /run/{source}`, `GET /stream/{run_id}`, `GET /api/status`.
- `routes/scraper_routes.py` — `GET /scraper/{alias}`, `POST /scraper/{alias}/save`. Per-scraper settings pages with API key fields, optional parameters, run button, and inline log. `SCRAPER_META` defines name, description, guide steps, and configurable fields for: calendarific, igdb, trakt, wikipedia-albums. Ballotpedia has no settings page (no API key needed).
- `routes/export_routes.py` — `GET /export`, `POST /export/save`. Google Sheets credentials (Sheet ID, tab name, credentials JSON upload), SQL editor for the export query, and run button.
- `routes/config_routes.py` — `GET /config` redirects 301 → `/export` (legacy redirect).
- `routes/db_routes.py` — `GET /db`, `POST /db/query`. Schema browser and raw SQL query runner.
- `templates/` — PicoCSS + vanilla JS. SSE log streaming uses `EventSource` on the client, `[DONE]` sentinel closes the stream.

### Settings priority

`DATABASE_URL` is set in `docker-compose.yml` environment (highest priority — never overwritten by config reload). All other keys come from `CONFIG_DIR/.env` (generated by `config_store.save_config()`).

## Popularity Scoring

Two fields:
- **`popularity_score`** (Integer) — raw metric as-is: Last.fm listeners, IGDB Want-to-Play × 1M, Trakt list_count/votes.
- **`impact_level`** (SmallInteger, 0-100) — sqrt-scaled relative to category max. Formula: `sqrt(value) / sqrt(max_value) * 100`. Computed by `BaseIngester._apply_log_scale()` after normalization.

Ballotpedia events have `popularity_score = None` and no impact_level (elections are not ranked by popularity).

## Hardcoded Ingester Parameters

- **Calendarific:** years = current + next; default country=`US` (configurable via `calendarific_countries`)
- **Trakt:** `limit=100` for anticipated movies/shows (configurable); premiere search window = 180 days (configurable); only `returning series` with `episode_number==1 & season>1` (no series premieres)
- **IGDB:** candidates must have `hypes > 0`; `limit=100` (configurable); PopScore type 2 (Want to Play) only
- **Wikipedia Albums:** current year only (configurable via `wikipedia_albums_year`); skips entries with "TBA"
- **Ballotpedia:** scrapes `https://ballotpedia.org/Statewide_primary_elections_calendar`; skips past dates; no configurable parameters

## Key Conventions

- **Calendarific:** Deduplicates ~633 raw entries per year to ~250 using `name + date` key, keeping highest `DEDUP_PRIORITY` variant. Uses `primary_type` (not `type` array) for category mapping.
- **IGDB:** Two-step fetch — first get games with `hypes > 0`, then batch-fetch Want-to-Play scores, re-sort, and attach scores. Fresh Twitch token per run.
- **Wikipedia Albums:** `_parse_html_tables()` handles `rowspan` on date `<th>` cells. Last.fm enrichment is per unique primary artist (deduplicated), 200ms rate limit.
- **Ballotpedia:** Parses `wikitable` tables from Ballotpedia HTML. Looks for columns named "state" and "date". External ID: `ballotpedia_primary_{slugified_state}_{year}`. Category: `elections`.
- **Export query:** Custom SQL stored in `config.json`. Loaded by `export_sheets._load_custom_query()` at export time. `fetch_rows()` returns `(headers, rows)` — column names derived from `result.keys()`, not hardcoded.

## API Reference Docs

- `docs/calendarific-api.md` — endpoints, holiday types, dedup notes
- `docs/igdb-api.md` — all endpoints, popularity types, query syntax
- `docs/trakt-api.md` — 170 endpoints, filters, extended info, pagination
