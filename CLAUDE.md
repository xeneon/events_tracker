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
- `fashion_weeks.py` - Fashion weeks ingester (curated data)
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
- `LASTFM_API_KEY` - For album release enrichment
- `GOOGLE_SHEET_ID` - Target spreadsheet ID
- `GOOGLE_SHEET_TAB` - Tab name (default: "Sheet1")
- `GOOGLE_CREDENTIALS_FILE` - Path to service account JSON

## Package Manager

Use `pip` for installing dependencies from `requirements.txt`.

## Key Conventions

- **Calendarific:** Deduplicates multiple entries per holiday in `fetch_events()` before normalizing. Uses `primary_type` (not `type` array) for category mapping. Region field uses state abbreviations to fit 200-char limit.
- **Trakt:** Impact level 1-5 based on ranking position. Handles both movies and TV shows.
- **Fashion Weeks:** Static curated data. Manual sync recommended monthly.
- **Wikipedia Albums:** Scrapes wikitables, enriches with Last.fm. 200ms rate limit between Last.fm requests. Impact levels based on listener counts (5M+ → 5, 1M+ → 4, etc.).
- **Google Sheets export:** Runs automatically after `--all`, or standalone via `python -m ingest.export_sheets`. Preserves table formatting (filters, banding, conditional formatting).

## Current Date

Today's date is 2026-02-16.
