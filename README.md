# Events Tracker

A full-stack web application for aggregating and displaying notable events from multiple sources on a filterable calendar. Track US holidays, movie and TV releases, fashion weeks, and major music album releases all in one place.

## Features

- **Multi-Source Event Aggregation**: Automatically ingests events from 4 data sources (Calendarific, Trakt, Wikipedia/Last.fm, curated fashion weeks)
- **Interactive Calendar**: FullCalendar-based interface with day, week, month, and list views
- **Popularity-Based Filtering**: Smart client-side filtering shows only the most notable events per category (top 30 for movies/TV, 1M+ listeners for music)
- **Advanced Filtering**: Filter by category, date range, country, impact level, tags, and text search
- **Recurring Events**: Support for repeating events using RRULE specification
- **User Authentication**: JWT-based authentication with role-based access control
- **Event Management**: Create, update, and approve user-submitted events
- **Scheduled Ingestion**: Automated data fetching using APScheduler with configurable cron jobs
- **Responsive Design**: Modern UI built with React 19 and TailwindCSS

## Tech Stack

### Backend
- **Python 3.13** - Core language
- **FastAPI** - High-performance async web framework
- **SQLAlchemy 2.0** - Async ORM with asyncpg driver
- **PostgreSQL** - Primary database
- **fastapi-users** - Authentication and user management
- **APScheduler** - Automated task scheduling
- **Alembic** - Database migrations
- **BeautifulSoup4** - HTML parsing (Wikipedia scraping)
- **slowapi** - Rate limiting middleware

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type-safe development
- **Vite 6** - Build tool and dev server
- **FullCalendar v6** - Calendar component with RRULE support
- **Zustand** - State management
- **TailwindCSS** - Utility-first styling
- **Axios** - HTTP client
- **React Router v7** - Client-side routing

### Infrastructure
- **Docker Compose** - Container orchestration
- **PostgreSQL** (external) - Database at 192.168.1.103
- **Remote Docker** - Deployment via SSH to 192.168.1.102

## Architecture Overview

The application follows a service-oriented architecture with clear separation between data access, business logic, and API layers.

### Backend Architecture

**Request Flow**: API Route (`api/v1/`) → Service Layer (`services/`) → SQLAlchemy Models (`models/`)

**Authentication**: JWT tokens (1-hour expiry) with three access levels:
- `current_active_user` - Authenticated users
- `current_superuser` - Admin-only endpoints
- `current_optional_user` - Optional authentication

**Event Service**: Central business logic handling:
- Pagination and filtering (category, date range, country, impact, tags, text search)
- Recurring event expansion using dateutil.rrule
- Simplified calendar projections vs. full event objects

**Data Ingestion**: Four specialized ingesters inherit from `BaseIngester`:
- **Calendarific** — US holidays (federal, state, observance, religious) via API
- **Trakt** — Anticipated movies and TV shows via API
- **Fashion Weeks** — Curated fashion week schedule
- **Wikipedia Albums** — Music album releases scraped from Wikipedia, enriched with Last.fm listener data
- All ingesters: fetch → normalize → upsert (PostgreSQL ON CONFLICT on `data_source_id, external_id`)
- Scheduled via APScheduler cron jobs; admin can trigger manual sync

**Database**: External PostgreSQL instance (not containerized) with async access via asyncpg. Alembic manages schema migrations.

### Frontend Architecture

**State Management**: Zustand stores:
- `authStore` - User authentication, token, loading state
- `filterStore` - Calendar filter preferences
- `eventStore` - Categories cache

**API Layer**: Axios client with JWT interceptor and automatic 401 redirect handling

**Calendar**: FullCalendar v6 integration with:
- Dynamic event fetching via `/events/calendar` endpoint
- Filter-triggered refetch
- Category filter using empty array `[]` to represent "show all"

**Routing**: Protected routes using `ProtectedRoute` component with loading state management

## Prerequisites

- **Python 3.13+** (with `uv` package manager)
- **Node.js 18+** (recommended via nodeenv)
- **Docker** & Docker Compose
- **PostgreSQL 14+** (external instance)
- **Git**

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd events_tracker
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see Environment Variables section below).

### 3. Database Setup

The application expects an external PostgreSQL instance. Create the database and user:

```sql
CREATE DATABASE events_tracker;
CREATE USER events_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE events_tracker TO events_user;
```

Update the `DATABASE_URL` in your `.env` file accordingly.

### 4. Backend Setup (Local Development)

```bash
cd backend

# Install dependencies using uv
/home/dev/.local/bin/uv pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Seed initial data (categories, data sources, superuser)
python -m app.seed

# Start development server
uvicorn app.main:app --reload
```

The backend will be available at `http://localhost:8000`.

### 5. Frontend Setup (Local Development)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000` with API proxy configured.

### 6. Docker Deployment

The project is configured for remote Docker deployment via SSH:

```bash
# Build and start both services
docker compose up --build -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down
```

**Note**: Volume mounts are not supported with remote Docker context. Code changes require rebuilding:

```bash
docker compose build --no-cache frontend
docker compose up -d
```

Services are exposed at:
- **Backend**: http://192.168.1.102:8001 (container port 8000 mapped to 8001)
- **Frontend**: http://192.168.1.102:3000

## Environment Variables

Create a `.env` file in the project root. See `.env.example` for all available options:

### Required Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://events_user:events_password@192.168.1.103:5432/events_tracker

# Authentication
JWT_SECRET=change-me-to-a-random-secret-key

# Initial Superuser (created by seed script)
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=changeme123
```

### Optional Variables

```env
# API Keys (required for specific ingesters)
CALENDARIFIC_API_KEY=your_key           # US holidays (https://calendarific.com)
TRAKT_CLIENT_ID=your_client_id         # Movies & TV (https://trakt.tv/oauth/applications)
LASTFM_API_KEY=your_key                # Music album enrichment (https://www.last.fm/api/account/create)

# Application
APP_ENV=development
CORS_ORIGINS=http://localhost:3000,http://192.168.1.102:3000,http://192.168.1.102
```

## API Overview

The API is accessible at `/api/v1/` with the following endpoint groups:

### Authentication (`/auth`)
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login with email/password (returns JWT)
- `POST /auth/logout` - Logout current user
- `GET /auth/me` - Get current user profile

### Events (`/events`)
- `GET /events` - List events (paginated, filterable)
- `GET /events/calendar` - Get calendar events (with recurring expansion)
- `GET /events/{id}` - Get single event
- `POST /events` - Create event (authenticated)
- `PUT /events/{id}` - Update event (owner or admin)
- `DELETE /events/{id}` - Delete event (admin only)
- `POST /events/{id}/approve` - Approve event (admin only)

### Categories (`/categories`)
- `GET /categories` - List all event categories
- `POST /categories` - Create category (admin only)
- `PUT /categories/{id}` - Update category (admin only)
- `DELETE /categories/{id}` - Delete category (admin only)

### Data Sources (`/data-sources`)
- `GET /data-sources` - List data sources
- `PUT /data-sources/{id}` - Update data source (admin only)
- `POST /data-sources/{id}/ingest` - Trigger manual ingestion (admin only)

### Tags (`/tags`)
- `GET /tags` - List all tags
- `GET /tags/search` - Search tags by name

### Users (`/users`)
- `GET /users/me` - Get current user
- `PATCH /users/me` - Update current user

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Data Ingestion

The application automatically fetches events from four data sources using scheduled jobs.

### Data Sources

| Source | Categories | Type | Schedule | Description |
|--------|-----------|------|----------|-------------|
| **Calendarific** | Federal/State Holiday, Observance, Religious | API | Weekly Mon 4am UTC | US holidays via Calendarific API |
| **Trakt** | Movies, TV Shows | API | Daily 3am UTC | Top 100 anticipated movies & shows |
| **Fashion Weeks** | Fashion | Curated | On-demand | Major fashion week events |
| **Wikipedia Albums** | Music Releases | Scrape | Weekly Wed 5am UTC | Album releases from Wikipedia, enriched with Last.fm listener data |

### Ingestion Process

1. **Scheduled Execution**: APScheduler runs cron jobs defined in `services/ingestion/scheduler.py`
2. **Data Fetching**: Each ingester fetches events from its source (API, scrape, or curated data)
3. **Normalization**: Data is normalized to the common Event schema with impact levels and popularity scores
4. **Deduplication**: Upsert based on `(data_source_id, external_id)` unique constraint
5. **Auto-Approval**: Ingested events are automatically approved (`is_approved=True`)

### Manual Ingestion

Trigger ingestion manually via API (admin only):

```bash
POST /api/v1/admin/data-sources/{id}/sync
```

## Development

### Backend Development

```bash
cd backend

# Run tests
pytest

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Start dev server with auto-reload
uvicorn app.main:app --reload
```

**Package Manager**: Use `uv` instead of pip:
```bash
/home/dev/.local/bin/uv pip install package-name
```

### Frontend Development

```bash
cd frontend

# Start dev server (with HMR)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

**Node.js**: Activate nodeenv before running npm commands:
```bash
source /home/dev/.nodeenv/bin/activate
```

### Code Quality

**Backend**:
- Type hints throughout codebase
- Async/await for all database operations
- Service layer pattern for business logic
- Pydantic schemas for request/response validation

**Frontend**:
- TypeScript strict mode enabled
- Component-based architecture
- Custom hooks for reusable logic
- Zustand for predictable state management

### Rate Limiting

The API has rate limiting enabled via slowapi:
- **Global limit**: 30 requests per minute per IP

## Project Structure

```
events_tracker/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/           # API route handlers
│   │   ├── core/             # Configuration and security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic
│   │       └── ingestion/    # Data ingestion services
│   ├── tests/                # Backend tests
│   ├── pyproject.toml        # Python dependencies
│   └── Dockerfile            # Backend container
├── frontend/
│   ├── src/
│   │   ├── api/              # API client functions
│   │   ├── components/       # React components
│   │   │   ├── auth/         # Authentication components
│   │   │   ├── calendar/     # Calendar components
│   │   │   ├── events/       # Event components
│   │   │   └── layout/       # Layout components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── pages/            # Page components
│   │   ├── store/            # Zustand stores
│   │   ├── styles/           # Global styles
│   │   └── types/            # TypeScript types
│   ├── package.json          # Node dependencies
│   └── Dockerfile            # Frontend container
├── docker-compose.yml        # Docker orchestration
├── .env.example              # Environment template
└── CLAUDE.md                 # Development guide
```

---

Built with FastAPI, React, and PostgreSQL.
