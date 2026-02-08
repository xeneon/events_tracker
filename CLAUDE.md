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

**Data ingestion** (`services/ingestion/`): Single `CalendarificIngester` inherits from `BaseIngester`. Fetches US holidays from the Calendarific API (2 calls per sync: current year + next year, ~1030 events total). The API returns duplicate entries per holiday (federal + per-state); the ingester deduplicates by `urlid+date`, keeping the highest-priority variant (Federal > State Legal > State > Observance). Uses `primary_type` field for category mapping. `scheduler.py` registers one APScheduler cron job (daily 2 AM UTC). Ingested events default to `is_approved=True`; user-submitted events default to `False`. Admin can trigger manual sync via `POST /api/v1/admin/data-sources/{id}/sync`.

**Database:** External PostgreSQL at `192.168.1.103:5432`, database `events_tracker`, user `events_user`. Not containerized. Single Alembic migration for the initial schema. The Event model has a unique constraint on `(data_source_id, external_id)` for deduplication. The `region` column is `VARCHAR(200)` — ingester truncates long state lists to fit.

### Frontend (React 19 + Vite + TypeScript)

**State:** Zustand stores in `store/` — `authStore` (user/token/loading), `filterStore` (calendar filters), `eventStore` (categories cache).

**API layer:** Axios client in `api/client.ts` with JWT interceptor and 401 redirect logic (skips auth endpoints). All API functions in `api/auth.ts` and `api/events.ts`.

**Calendar:** FullCalendar v6 in `components/calendar/EventCalendar.tsx`. Fetches events via the `/events/calendar` endpoint. Filter changes trigger `calendarRef.current.getApi().refetchEvents()`. Category filter uses empty array `[]` to mean "show all" — the `toggleCategory` store action handles the transition to/from this state by accepting all category IDs.

**Routing:** React Router v7. Protected routes use `components/auth/ProtectedRoute.tsx` which shows a spinner while `loading` is true (initialized to `!!localStorage.getItem("token")` to avoid race conditions).

**Vite proxy:** `/api` requests are proxied to the backend. In Docker, uses `VITE_API_URL` env var (`http://backend:8000`). The proxy target is set in `vite.config.ts` server config.

### Key Conventions

- **US holidays focus.** The app tracks US holidays only via the Calendarific API (free tier: 1000 req/day). Frontend defaults `countryCode` to `"US"` and the sidebar shows a static "United States" label instead of a country picker.
- **Categories:** Federal Holiday, State Holiday, Observance, Religious, Other. Seed script upserts (updates existing slugs on re-run).
- **Data sources:** Calendarific (API) and Manual. `.env` key: `CALENDARIFIC_API_KEY`.
- **Calendarific API quirks:** Returns multiple entries per holiday (one federal + per-state breakdowns). Ingester deduplicates in `fetch_events()` before normalizing. The `primary_type` field (not `type` array) is used for category mapping. Some holidays have `urlid: null` (e.g. Daylight Saving Time). Region field uses state abbreviations to stay within 200-char column limit.
- Backend schemas in `schemas/` mirror but don't duplicate models. `EventCalendarItem.id` is `str` (not UUID) to support recurring instance IDs like `{uuid}_{date}`.
- Ingester `_coerce_types()` converts string dates/times to Python objects before database insertion.
- Rate limiting via `slowapi` middleware (30/min global).
- CORS origins configured in `.env` as comma-separated list.
- Superuser credentials seeded from `SUPERUSER_EMAIL`/`SUPERUSER_PASSWORD` env vars.
