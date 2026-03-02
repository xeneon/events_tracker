# Events Tracker

**Events Tracker** automatically pulls upcoming events from the web — holidays, elections, movies, TV shows, video games, and music albums — stores them in a database, and can export a ranked list to a Google Sheet. You control everything from a simple browser-based dashboard.

---

## What it does

| Category | Where data comes from | What you get |
|---|---|---|
| **Holidays** | Calendarific API | US public holidays (federal, state, religious, observances) for the current and next year. Multi-country support available. |
| **Elections** | Ballotpedia (web scrape) | US statewide primary election dates. No API key required. |
| **Movies & TV** | Trakt API | Top 100 anticipated movies, top 100 anticipated TV shows, and upcoming season premieres (returning series only) |
| **Video Games** | IGDB / Twitch API | Upcoming games ranked by "Want to Play" count, filtered to games with active hype |
| **Music Albums** | Wikipedia + Last.fm | Upcoming album releases for the current year, enriched with Last.fm artist listener counts |

Each item is scored with an **impact level** (0–100) so you can compare popularity across categories. The score is calculated relative to the most-anticipated item in each batch — 100 means it's the most anticipated in its group.

You can export a filtered, ranked snapshot of all this data to a Google Sheet tab with one click.

---

## Quickstart

### What you need first

- **Docker Desktop** installed on your computer
  - Mac: [docs.docker.com/desktop/install/mac-install](https://docs.docker.com/desktop/install/mac-install/)
  - Windows: [docs.docker.com/desktop/install/windows-install](https://docs.docker.com/desktop/install/windows-install/)
  - Linux: [docs.docker.com/desktop/install/linux-install](https://docs.docker.com/desktop/install/linux-install/)
- **Git** (to download the code) — or you can download a ZIP from the repository page

### Step 1 — Download the code

Open a terminal (on Mac: Spotlight → "Terminal"; on Windows: search "Command Prompt" or "PowerShell") and run:

```bash
git clone <repo-url>
cd events_tracker
```

Or download the ZIP from the repository page, unzip it, and navigate into the folder in your terminal.

### Step 2 — Start the app

```bash
docker compose up -d
```

Docker will download everything it needs and start two containers: the web app and a database. This may take a few minutes the first time.

When it finishes, open your browser and go to:

**http://localhost:8080**

You should see the Events Tracker dashboard. The database is empty at this point — you'll need to add API keys before running most scrapers.

### Step 3 — Get your API keys

Each data source requires a free API key. You only need the keys for the sources you want to use — everything is optional.

> **Ballotpedia (Elections) requires no API key at all** — just click Run and it works.

#### Holidays — Calendarific
1. Go to [calendarific.com/api](https://calendarific.com/api) and create a free account
2. Copy your **API Key** from the dashboard

#### Movies & TV — Trakt
1. Go to [trakt.tv](https://trakt.tv) and sign in (or create a free account)
2. Open [trakt.tv/oauth/applications/new](https://trakt.tv/oauth/applications/new)
3. Enter any name, set the Redirect URI to `http://localhost`, and click **Save App**
4. Copy the **Client ID** shown on the page (you don't need the Client Secret)

#### Video Games — IGDB (via Twitch)
IGDB uses Twitch for authentication. You need a Twitch developer app:
1. Go to [dev.twitch.tv/console](https://dev.twitch.tv/console) and sign in with a Twitch account (free)
2. Click **Register Your Application**, give it any name, set the OAuth Redirect URL to `http://localhost`, and choose any Category
3. Click **Create**, then open the app you just created
4. Copy the **Client ID**, then click **New Secret** to generate and copy the **Client Secret**

#### Music Albums — Last.fm
1. Go to [last.fm](https://www.last.fm) and sign in (or create a free account)
2. Open [last.fm/api/account/create](https://www.last.fm/api/account/create)
3. Fill in any application name and submit the form
4. Copy the **API key** shown on the confirmation page

#### Google Sheets export *(optional)*
To export data to a Google Sheet, you need a **Google service account**:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project (or select an existing one)
2. Search for **"Google Sheets API"** and enable it
3. Go to **IAM & Admin → Service Accounts** and click **Create Service Account**
4. Give it any name, click through the steps, then open the service account and go to the **Keys** tab
5. Click **Add Key → Create new key → JSON** — this downloads a `.json` credentials file to your computer
6. Create a Google Sheet, click **Share**, and share it with the service account's email address (shown in the service account list) with **Editor** access
7. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/**SHEET_ID_HERE**/edit`

### Step 4 — Configure each scraper

Each scraper has its own settings page where you paste its API key and can adjust optional parameters.

1. From the dashboard at **http://localhost:8080**, click the name of any scraper to open its settings page
2. Paste in the API key and click **Save**
3. Repeat for each scraper you want to use

For the **Google Sheets export**, click **Export** in the sidebar to open the export settings page, where you enter the Sheet ID, tab name, and upload your credentials JSON file.

> Ballotpedia has no settings page — it needs no configuration.

### Step 5 — Run the scrapers

Go back to **http://localhost:8080** (the home page).

- Click **Run** next to any individual source to fetch data for just that source
- Click **Run All** to fetch everything at once (this can take a few minutes — Wikipedia/Last.fm is slow due to rate limits)
- Watch the live log to see what's happening

Once data is collected, click **Export** in the sidebar and then **Run Export** to push a ranked snapshot to your Google Sheet.

---

## Stopping and starting

```bash
# Stop the app (data is preserved)
docker compose down

# Start it again
docker compose up -d
```

> **Important:** Do not run `docker compose down -v` — the `-v` flag deletes your database and all saved config.

---

## Scraper details

### Calendarific — Holidays

Fetches US public holidays from the [Calendarific API](https://calendarific.com/api) for the current year and next year. Covers federal holidays, state holidays, religious observances, and more. Deduplicates ~630 raw entries per year down to ~250 by merging regional variants of the same holiday, keeping the highest-priority type (Federal > State > Observance).

**Configurable options (on the scraper settings page):**
- **Countries** — comma-separated ISO country codes (default: `US`). You can add others, e.g. `US,GB,CA`.

**Requires:** Calendarific API key

---

### Ballotpedia — Elections

Scrapes the [Ballotpedia statewide primary election calendar](https://ballotpedia.org/Statewide_primary_elections_calendar) directly — no API key or account needed. Fetches upcoming US statewide primary dates and skips any that have already passed.

**Requires:** Nothing — just click Run.

---

### Trakt — Movies & TV

Fetches data from the [Trakt API](https://trakt.tv):

- **Anticipated movies** — top 100 most-anticipated upcoming films, sorted by the number of Trakt members who have them on their watchlist. Uses US theatrical release dates where available.
- **Anticipated TV shows** — top 100 most-anticipated new shows
- **Season premieres** — upcoming Season 2+ premiere episodes for returning series within the next 180 days (configurable). Only includes shows with a confirmed air date.

**Configurable options:**
- **Anticipated limit** — how many movies/shows to fetch (default: 100)
- **Premiere window** — how many days ahead to look for season premieres (default: 180)

**Requires:** Trakt Client ID (free, no credit card)

---

### IGDB — Video Games

Fetches upcoming video game releases from [IGDB](https://www.igdb.com/) (owned by Twitch). Uses a two-step fetch: first retrieves games with active hype scores, then fetches "Want to Play" popularity scores and re-ranks. Only games with at least one "hype" point are included, which filters out unannounced or very obscure titles.

**Configurable options:**
- **Fetch limit** — how many games to fetch (default: 100)

**Requires:** Twitch Client ID + Client Secret (free Twitch developer account)

---

### Wikipedia Albums — Music

Parses the Wikipedia "List of [year] albums" article to find upcoming music releases. Then enriches each entry with Last.fm listener counts for the primary artist (one API call per unique artist, at a 200ms rate limit to be polite to Last.fm). This makes the scraper slow — expect 2–3 minutes for a full run.

Entries marked "TBA" (no confirmed date) are skipped. Only the current year is supported.

**Configurable options:**
- **Year** — which year's Wikipedia album list to fetch (default: current year)

**Requires:** Last.fm API key (used for popularity scoring; the scraper will run without it but events will have no impact level)

---

## Web UI pages

| Page | What it does |
|---|---|
| **Home** (`/`) | Run scrapers, see live logs, check per-source status |
| **Scraper settings** (`/scraper/<name>`) | Per-scraper API key entry, optional parameters, and run button |
| **Export** (`/export`) | Google Sheets credentials, SQL editor, run export |
| **DB Viewer** (`/db`) | Browse the raw database contents and run custom SQL queries |

---

## Google Sheets export details

The default export selects:
- The top 15 events per category by impact level
- All events with an impact level of 50 or higher
- Only events from the current month through the end of the current year

The export query is fully editable on the Export page. You can change the columns, filters, and sorting — whatever columns your query returns become the header row in the sheet.

---

## CLI usage (advanced)

If you prefer to run without Docker, you can use the `ingest` package directly:

```bash
pip install -r requirements.txt

# Copy and fill in your environment file
cp .env.example .env

python -m ingest --list                  # show available sources
python -m ingest calendarific            # run one source
python -m ingest trakt --dry-run         # preview without saving
python -m ingest ballotpedia             # no API key needed
python -m ingest --all                   # run all sources + export
python -m ingest.export_sheets           # export only
python -m ingest.export_sheets --dry-run
```

Requires a `.env` file at the project root. See `.env.example` for all variables. `DATABASE_URL` must point to a running PostgreSQL instance.

---

## Environment variables reference

| Variable | Required for | Description |
|---|---|---|
| `DATABASE_URL` | Everything | PostgreSQL connection string (`postgresql+asyncpg://...`) — set automatically in Docker |
| `CALENDARIFIC_API_KEY` | Holidays | [calendarific.com/api](https://calendarific.com/api) |
| `TRAKT_CLIENT_ID` | Movies & TV | [trakt.tv/oauth/applications](https://trakt.tv/oauth/applications) |
| `TWITCH_CLIENT_ID` | Games | Twitch developer app Client ID |
| `TWITCH_CLIENT_SECRET` | Games | Twitch developer app Client Secret |
| `LASTFM_API_KEY` | Albums | [last.fm/api](https://www.last.fm/api) |
| `GOOGLE_SHEET_ID` | Sheets export | The ID from your Google Sheet's URL |
| `GOOGLE_SHEET_TAB` | Sheets export | Tab name to write to (default: `Sheet1`) |
| `GOOGLE_CREDENTIALS_FILE` | Sheets export | Path to your service account JSON file |

Ballotpedia requires no API key and has no environment variable.

In Docker, all keys except `DATABASE_URL` are configured via the scraper settings pages and stored in a persistent Docker volume — you don't touch `.env` files.

---

## Popularity scoring

Each event has two numeric fields:

- **`popularity_score`** — the raw number from the source (Last.fm listener count, IGDB Want-to-Play count × 1,000,000, Trakt list count, etc.)
- **`impact_level`** (0–100) — a normalized score relative to the most popular item in the same ingestion batch. Calculated as `√(value) / √(max_value) × 100`. A score of 100 means it's the most anticipated item in its category for that run.

Ballotpedia events have no popularity score (primary election dates are not ranked by popularity).

---

## License

MIT
