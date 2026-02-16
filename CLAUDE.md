# CLAUDE.md

This file provides guidance to Claude Code when working with the Events Tracker ingestion CLI.

## Overview

This is a standalone CLI tool for ingesting events from multiple sources and exporting them to Google Sheets. The web UI and FastAPI backend have been removed - this repo contains only the ingestion scrapers.

## CLI Usage

```bash
# List available ingesters
python -m ingest --list

# Run a specific ingester
python -m ingest calendarific
python -m ingest trakt --dry-run

# Run all ingesters + export to Google Sheets
python -m ingest --all
```

## Package Structure

All code is in the `ingest/` package:
- `__main__.py` - CLI entry point
- `config.py` - Settings from .env
- `db.py` - Async SQLAlchemy connection
- `models.py` - Database models (Category, DataSource, Event)
- `base.py` - Base ingester class
- `calendarific.py` - US holidays ingester
- `trakt.py` - Movies & TV shows ingester
- `igdb.py` - Upcoming video game releases ingester (via IGDB/Twitch)
- `wikipedia_albums.py` - Album releases ingester (with Last.fm enrichment)
- `export_sheets.py` - Google Sheets exporter

## Database

- External PostgreSQL at `192.168.1.103:5432`, database `events_tracker`
- Schema is expected to already exist (categories, data_sources, events tables)
- Ingesters upsert events with deduplication on `(data_source_id, external_id)`
- All database access is async via `asyncpg`

## Environment Variables

Required in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `CALENDARIFIC_API_KEY` - For US holidays
- `TRAKT_CLIENT_ID` - For movies/TV shows
- `TWITCH_CLIENT_ID` - For IGDB video game releases (Twitch OAuth)
- `TWITCH_CLIENT_SECRET` - For IGDB video game releases (Twitch OAuth)
- `LASTFM_API_KEY` - For album release enrichment
- `GOOGLE_SHEET_ID` - Target spreadsheet ID
- `GOOGLE_SHEET_TAB` - Tab name (default: "Sheet1")
- `GOOGLE_CREDENTIALS_FILE` - Path to service account JSON

## Package Manager

Use `pip` for installing dependencies from `requirements.txt`.

## Popularity Scoring

Two fields track popularity:
- **`popularity_score`** (Integer) — raw metric value from the source (e.g. 6,751,421 Last.fm listeners, 1,584 IGDB Want-to-Play × 1M, 35,017 Trakt votes). Preserved as-is for transparency.
- **`impact_level`** (SmallInteger, 0-100) — log-scaled score computed by `BaseIngester._apply_log_scale()` after normalization. Formula: `log(1+value)/log(1+max_value)*100`. Preserves magnitude differences and enables cross-category comparison (100 = category leader).

## Key Conventions

- **Calendarific:** Deduplicates multiple entries per holiday in `fetch_events()` before normalizing. Uses `primary_type` (not `type` array) for category mapping. Region field uses state abbreviations to fit 200-char limit. No raw popularity metric (holidays have no anticipation data).
- **Trakt:** Handles anticipated movies, TV shows, and season premieres. Raw metric: `list_count` (anticipated) / `votes` (premieres), shown in description.
- **IGDB:** Fetches upcoming games, ranked by PopScore "Want to Play" metric (live anticipation data). Raw metric: Want to Play × 1M, `hypes` count shown in description. Auth via Twitch client credentials (fresh token per run). Category slug: `video-games`.
- **Wikipedia Albums:** Scrapes wikitables, enriches with Last.fm. 200ms rate limit between Last.fm requests. Raw metric: Last.fm listeners, shown in description.
- **Google Sheets export:** Runs automatically after `--all`, or standalone via `python -m ingest.export_sheets`. Preserves table formatting (filters, banding, conditional formatting). Export uses `impact_level` (log-scaled 0-100) for ranking: top 15 per category or score >= 50.

## IGDB API Reference

See `docs/igdb-api.md` for full API documentation (all endpoints, fields, popularity types, query syntax). Key points for working with `igdb.py`:

- Auth: Twitch OAuth2 client_credentials grant. Rate limit: 4 req/sec, max 500 results.
- Primary metric: PopScore "Want to Play" (popularity_type=2, covers all platforms).
- Steam Wishlists (popularity_type=10) is a strong anticipation signal but **PC-only** — console exclusives will have no data. Use alongside type=2, not as replacement.
- `/events` endpoint has gaming conventions (Summer Game Fest, etc.) with dates — potential new ingester category.

## Current Date

Today's date is 2026-02-16.
