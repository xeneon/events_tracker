# Events Tracker

**Events Tracker** automatically pulls upcoming events from the web — holidays, movies, TV shows, video games, and music albums — stores them in a database, and can export a ranked list to a Google Sheet. You control everything from a simple browser-based dashboard.

---

## What it does

| Category | Where data comes from | What you get |
|---|---|---|
| **Holidays** | Calendarific API | US holidays (federal, state, observances) for the current and next year |
| **Movies & TV** | Trakt API | Top 100 anticipated movies, top 100 anticipated TV shows, and upcoming season premieres |
| **Video Games** | IGDB / Twitch API | Upcoming games ranked by "Want to Play" count |
| **Music Albums** | Wikipedia + Last.fm | Upcoming album releases with artist listener counts |

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

You should see the Events Tracker dashboard. The database is empty at this point — you'll need to add API keys before running any scrapers.

### Step 3 — Get your API keys

Each data source requires a free API key. You only need the keys for the sources you want to use — everything is optional except what you actually want to run.

#### Holidays — Calendarific
1. Go to [calendarific.com/api](https://calendarific.com/api) and create a free account
2. Copy your **API Key** from the dashboard

#### Movies & TV — Trakt
1. Go to [trakt.tv/oauth/applications](https://trakt.tv/oauth/applications) and sign in (or create a free account)
2. Click **New Application**, give it any name, and set the Redirect URI to `urn:ietf:wg:oauth:2.0:oob`
3. Copy the **Client ID** (you don't need the Client Secret)

#### Video Games — IGDB (via Twitch)
IGDB uses Twitch for authentication. You need a Twitch developer app:
1. Go to [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps) and sign in with a Twitch account (free)
2. Click **Register Your Application**, give it any name, set the OAuth Redirect URL to `http://localhost`, and set the Category to "Application Integration"
3. Click **Manage** on your new app and copy the **Client ID** and **Client Secret**

#### Music Albums — Last.fm
1. Go to [last.fm/api/account/create](https://www.last.fm/api/account/create) and sign in (or create a free account)
2. Fill in the form (Application name: anything you like) and copy your **API key**

#### Google Sheets export *(optional)*
To export data to a Google Sheet, you need a **Google service account**:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project (or select an existing one)
2. Search for **"Google Sheets API"** and enable it
3. Go to **IAM & Admin → Service Accounts** and click **Create Service Account**
4. Give it any name, click through the steps, then open the service account and go to the **Keys** tab
5. Click **Add Key → Create new key → JSON** — this downloads a `.json` credentials file to your computer
6. Create a Google Sheet, click **Share**, and share it with the service account's email address (shown in the service account list) with **Editor** access
7. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/**SHEET_ID_HERE**/edit`

### Step 4 — Enter your API keys in the app

1. Open **http://localhost:8080/config** in your browser
2. Paste in your API keys for whichever sources you want to use
3. If using Google Sheets: paste the Sheet ID, set the tab name (e.g. `Sheet1`), and upload your credentials JSON file
4. Click **Save**

### Step 5 — Run the scrapers

Go back to **http://localhost:8080** (the home page).

- Click **Run** next to any individual source to fetch data for just that source
- Click **Run All** to fetch everything at once (this can take a few minutes — Wikipedia/Last.fm is slow due to rate limits)
- Watch the live log to see what's happening

Once data is collected, click **Export to Sheets** to push a ranked snapshot to your Google Sheet.

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

## Web UI pages

| Page | What it does |
|---|---|
| **Home** (`/`) | Run scrapers, see live logs, check per-source status |
| **Config** (`/config`) | Set API keys, Google Sheets credentials, customize the export SQL query |
| **DB Viewer** (`/db`) | Browse the raw database contents and run custom SQL queries |

---

## Google Sheets export details

The default export selects:
- The top 15 events per category by impact level
- All events with an impact level of 50 or higher
- Only events from the current month through the end of the current year

The export query is fully editable on the Config page. You can change the columns, filters, and sorting — whatever columns your query returns become the header row in the sheet.

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

In Docker, all keys except `DATABASE_URL` are configured via the Config page and stored in a persistent Docker volume — you don't touch `.env` files.

---

## Popularity scoring

Each event has two numeric fields:

- **`popularity_score`** — the raw number from the source (Last.fm listener count, IGDB Want-to-Play count × 1,000,000, Trakt list count, etc.)
- **`impact_level`** (0–100) — a normalized score relative to the most popular item in the same ingestion batch. Calculated as `√(value) / √(max_value) × 100`. A score of 100 means it's the most anticipated item in its category for that run.

---

## License

MIT
