# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

### Docker (primary workflow — remote context via SSH to 192.168.1.102)

```bash
docker compose up --build -d          # Build and start both services
docker compose down                   # Stop all
docker compose build --no-cache frontend  # Force frontend rebuild after changes
docker compose logs -f backend        # Tail backend logs
```

Volume mounts do NOT work with this remote Docker context. Every code change requires a `docker compose up --build -d` to take effect.

- Backend: http://192.168.1.102:8001 (mapped 8001 → container 8000; port 8000 used by Portainer)
- Frontend: http://192.168.1.102:3000 (Vite dev server with proxy to backend)

### Backend (local)

```bash
cd backend
uvicorn app.main:app --reload         # Dev server on :8000
alembic upgrade head                  # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
python -m app.seed                    # Seed categories, data sources, superuser
python -m app.cleanup_old_data        # One-time: remove old sources/events/categories
```

Package manager: `uv` (pip is not available). Example: `/home/dev/.local/bin/uv pip install -e ".[dev]"`

### Frontend (local)

Node.js installed via nodeenv at `/home/dev/.nodeenv`. Activate with `source /home/dev/.nodeenv/bin/activate`.

```bash
cd frontend
npm run dev                           # Vite dev server on :3000
npm run build                         # Production build to dist/
```

### Tests

```bash
cd backend && pytest                  # Backend tests (pytest-asyncio)
```

## Architecture

### Backend (FastAPI + async SQLAlchemy)

All database access is async via `asyncpg`. The app entrypoint is `backend/app/main.py`.

**Request flow:** Route handler (`api/v1/`) → Service layer (`services/`) → SQLAlchemy models (`models/`)

**Auth:** `fastapi-users` with JWT (1-hour tokens). Three dependency levels: `current_active_user`, `current_superuser`, `current_optional_user` defined in `core/security.py`.

**Event service** (`services/event_service.py`): Central business logic for events. Handles pagination, filtering (category, date range, country, impact, tags, text search via ILIKE), and recurring event expansion (RRULE via `dateutil.rrule`). The calendar endpoint returns a simplified projection; the list endpoint returns full event objects.

**Data ingestion** (`services/ingestion/`): Four ingesters inherit from `BaseIngester`. Each implements `fetch_events()` → `normalize()`, and the base class handles upsert with dedup on `(data_source_id, external_id)`. Ingested events default to `is_approved=True`; user-submitted events default to `False`. Admin can trigger manual sync via `POST /api/v1/admin/data-sources/{id}/sync`.

- **CalendarificIngester** — US holidays. 2 API calls per sync (current year + next year, ~1030 events). Deduplicates by `urlid+date`, keeping highest-priority variant (Federal > State Legal > State > Observance). Uses `primary_type` for category mapping. Schedule: weekly Monday 4am UTC.
- **TraktIngester** — Anticipated movies and TV shows. Fetches top 100 anticipated from Trakt API. Impact level based on position ranking. Schedule: daily 3am UTC.
- **FashionWeeksIngester** — Curated fashion week events. Static data with country codes and cities. Schedule: on-demand (sync_interval: monthly).
- **WikipediaAlbumsIngester** — Music album releases. Scrapes `List_of_{year}_albums` via MediaWiki API, parses wikitables with BeautifulSoup (handles rowspan dates, skips TBA table). Enriches with Last.fm `artist.getinfo` for listener counts, images, and URLs (200ms rate limit between requests, cached per artist). Impact levels: 5M+ listeners→5, 1M+→4, 250k+→3, 50k+→2, <50k→1. Schedule: weekly Wednesday 5am UTC.

**Database:** External PostgreSQL at `192.168.1.103:5432`, database `events_tracker`, user `events_user`. Not containerized. Single Alembic migration for the initial schema. The Event model has a unique constraint on `(data_source_id, external_id)` for deduplication. The `region` column is `VARCHAR(200)` — ingester truncates long state lists to fit.

### Frontend (React 19 + Vite + TypeScript)

**State:** Zustand stores in `store/` — `authStore` (user/token/loading), `filterStore` (calendar filters), `eventStore` (categories cache).

**API layer:** Axios client in `api/client.ts` with JWT interceptor and 401 redirect logic (skips auth endpoints). All API functions in `api/auth.ts` and `api/events.ts`.

**Calendar:** FullCalendar v6 in `components/calendar/EventCalendar.tsx`. Fetches events via the `/events/calendar` endpoint. Filter changes trigger `calendarRef.current.getApi().refetchEvents()`. Category filter uses empty array `[]` to mean "show all" — the `toggleCategory` store action handles the transition to/from this state by accepting all category IDs.

**Routing:** React Router v7. Protected routes use `components/auth/ProtectedRoute.tsx` which shows a spinner while `loading` is true (initialized to `!!localStorage.getItem("token")` to avoid race conditions).

**Vite proxy:** `/api` requests are proxied to the backend. In Docker, uses `VITE_API_URL` env var (`http://backend:8000`). The proxy target is set in `vite.config.ts` server config.

### Key Conventions

- **Country filter behavior.** Frontend defaults `countryCode` to `"US"`. The backend filter includes events matching the country code OR with `country_code IS NULL` (global events like albums, movies, TV shows always appear regardless of country filter).
- **Popularity-based calendar filtering.** The frontend pre-fetches all events to compute per-category-per-year popularity thresholds. Music Releases use a fixed 1M listener floor. Other categories use a top-30 cutoff. Events without `popularity_score` (e.g. holidays) always display.
- **Categories:** Federal Holiday, State Holiday, Observance, Religious, Movies, TV Shows, Fashion, Music Releases, Other. Seed script upserts (updates existing slugs on re-run).
- **Data sources:** Calendarific (API), Trakt (API), Fashion Weeks (curated), Wikipedia Albums (scrape), Manual. `.env` keys: `CALENDARIFIC_API_KEY`, `TRAKT_CLIENT_ID`, `LASTFM_API_KEY`.
- **Calendarific API quirks:** Returns multiple entries per holiday (one federal + per-state breakdowns). Ingester deduplicates in `fetch_events()` before normalizing. The `primary_type` field (not `type` array) is used for category mapping. Some holidays have `urlid: null` (e.g. Daylight Saving Time). Region field uses state abbreviations to stay within 200-char column limit.
- **Wikipedia Albums quirks:** Tables use `rowspan` on date `<th>` cells for multiple albums on the same day. TBA table (caption contains "sometime") is skipped. Reference `<sup>` elements are decomposed before text extraction. `get_text(separator=" ")` used to avoid concatenation of adjacent inline elements.
- Backend schemas in `schemas/` mirror but don't duplicate models. `EventCalendarItem.id` is `str` (not UUID) to support recurring instance IDs like `{uuid}_{date}`.
- Ingester `_coerce_types()` converts string dates/times to Python objects before database insertion.
- Rate limiting via `slowapi` middleware (30/min global).
- CORS origins configured in `.env` as comma-separated list.
- Superuser credentials seeded from `SUPERUSER_EMAIL`/`SUPERUSER_PASSWORD` env vars.
