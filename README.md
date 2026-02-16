# Events Tracker - Ingestion CLI

A standalone CLI tool for ingesting events from multiple sources and exporting them to Google Sheets.

## Features

- **Four data ingesters:**
  - **Calendarific** - US holidays via API (federal, state, observances)
  - **Trakt** - Anticipated movies and TV shows
  - **Fashion Weeks** - Curated fashion week events
  - **Wikipedia Albums** - Music album releases with Last.fm enrichment

- **Database storage:** PostgreSQL with SQLAlchemy async models
- **Google Sheets export:** Top events query exported to configured sheet/tab

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL database (existing schema required)
- API keys for data sources (see `.env.example`)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd events_tracker

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://events_user:events_password@192.168.1.103:5432/events_tracker

# API Keys
CALENDARIFIC_API_KEY=your_key_here
TRAKT_CLIENT_ID=your_client_id_here
LASTFM_API_KEY=your_key_here

# Google Sheets Export
GOOGLE_SHEET_ID=your_sheet_id_here
GOOGLE_SHEET_TAB=Sheet1
GOOGLE_CREDENTIALS_FILE=path/to/service-account.json
```

## Usage

### Run Individual Ingesters

```bash
# List available ingesters
python -m ingest --list

# Run a specific ingester
python -m ingest calendarific
python -m ingest trakt
python -m ingest fashion-weeks
python -m ingest wikipedia-albums

# Dry run (fetch & normalize without DB writes)
python -m ingest trakt --dry-run
```

### Run All Ingesters

```bash
# Run all ingesters + Google Sheets export
python -m ingest --all

# Dry run all
python -m ingest --all --dry-run
```

### Export to Google Sheets

The export happens automatically after `--all` completes, or run standalone:

```bash
python -m ingest.export_sheets
python -m ingest.export_sheets --dry-run  # Print rows without writing
```

## Ingester Details

### Calendarific
- Fetches US holidays for current year + next year (~1030 events)
- Deduplicates by `urlid + date`, keeping highest priority variant
- Maps `primary_type` to categories (Federal Holiday, State Holiday, Observance, Religious)
- Handles state-level breakdowns, truncates region field to 200 chars

### Trakt
- Fetches top 100 anticipated movies and TV shows
- Impact level based on ranking position (1-5)
- Handles both movies and TV show premieres
- Season premiere dates normalized from air dates

### Fashion Weeks
- Curated static data with country codes and cities
- Major fashion weeks: New York, London, Milan, Paris
- Manual sync recommended (monthly schedule)

### Wikipedia Albums
- Scrapes `List_of_{year}_albums` via MediaWiki API
- Parses wikitables with BeautifulSoup (handles rowspan dates)
- Enriches with Last.fm `artist.getinfo` for:
  - Listener counts (→ popularity_score)
  - Artist images
  - URLs
- Impact levels based on listeners: 5M+ → 5, 1M+ → 4, 250k+ → 3, 50k+ → 2, <50k → 1
- 200ms rate limit between Last.fm requests
- Skips "TBA" table (caption contains "sometime")

## Database Schema

The ingesters expect an existing PostgreSQL database with the following tables:

- `categories` - Event categories (Federal Holiday, Movies, TV Shows, Music Releases, etc.)
- `data_sources` - Data source configurations (Calendarific, Trakt, Fashion Weeks, Wikipedia Albums)
- `events` - Events with deduplication on `(data_source_id, external_id)`

See `ingest/models.py` for the complete schema definition.

## Google Sheets Export

Exports the following query to the configured sheet/tab:

- Top 15 events per category by `popularity_score`
- All events with `popularity_score >= 1,000,000`
- Date range: current month through end of 2026
- Preserves existing table formatting (filters, banded ranges, conditional formatting)

## Architecture

The `ingest` package is fully self-contained:
- No dependencies on web framework (FastAPI removed)
- Standalone config, DB connection, and models
- CLI entry point at `ingest/__main__.py`
- Base ingester class in `ingest/base.py` handles:
  - Category mapping
  - Upsert with deduplication
  - Last synced timestamp updates

## License

MIT
