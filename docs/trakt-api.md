# Trakt API Reference

Full reference for the Trakt API v2, used by `ingest/trakt.py`.

Official docs: https://trakt.docs.apiary.io/
OpenAPI spec: https://api.apis.guru/v2/specs/trakt.tv/1.0.0/openapi.json
GitHub: https://github.com/trakt/trakt-api

## Authentication

No OAuth needed for public data. All requests require these headers:

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `trakt-api-key` | Your `client_id` from [Trakt app settings](https://trakt.tv/oauth/applications) |
| `trakt-api-version` | `2` |

OAuth (Bearer token) is only required for user-specific endpoints (`/sync/*`, `/users/me/*`, `/recommendations/*`, `/checkin`, `/scrobble`).

## Rate Limits

| Name | Verb | Limit |
|------|------|-------|
| `AUTHED_API_GET_LIMIT` | GET | 1000 calls / 5 minutes |
| `UNAUTHED_API_GET_LIMIT` | GET | 1000 calls / 5 minutes |
| `AUTHED_API_POST_LIMIT` | POST, PUT, DELETE | 1 call / second |

429 responses include `X-Ratelimit` header (JSON with `remaining`, `limit`, `until`) and `Retry-After` (seconds).

## Base URL

```
https://api.trakt.tv
```

Staging: `https://api-staging.trakt.tv` (separate environment, separate API keys).

## Pagination

Methods tagged with Pagination return 10 items per page by default. Query params:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page` | `1` | Page number |
| `limit` | `10` | Items per page |

Response headers: `X-Pagination-Page`, `X-Pagination-Limit`, `X-Pagination-Page-Count`, `X-Pagination-Item-Count`.

Calendar endpoints are **not** paginated — they return all results in a single response for the given date range.

## Extended Info

By default, responses return minimal objects (title, year, ids). Add `?extended=full` for complete info.

**Movie full fields:** `tagline`, `overview`, `released`, `runtime`, `country`, `trailer`, `homepage`, `status`, `rating`, `votes`, `comment_count`, `language`, `available_translations`, `genres`, `certification`, `updated_at`.

**Show full fields:** `overview`, `first_aired`, `runtime`, `certification`, `network`, `country`, `trailer`, `homepage`, `status`, `rating`, `votes`, `comment_count`, `language`, `available_translations`, `genres`, `aired_episodes`, `airs` (day/time/timezone), `updated_at`.

**Episode full fields:** `overview`, `first_aired`, `runtime`, `rating`, `votes`, `comment_count`, `updated_at`.

**Show status values:** `returning series`, `continuing`, `in production`, `planned`, `upcoming`, `pilot`, `canceled`, `ended`.

**Movie status values:** `released`, `in production`, `post production`, `planned`, `rumored`, `canceled`.

## Filters

Methods tagged with Filters accept query parameters to refine results. Multiples are comma-separated.

#### Common Filters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `query` | `batman` | Search titles and descriptions |
| `years` | `2026` | 4-digit year or range (e.g. `2024-2026`) |
| `genres` | `action,drama` | Genre slugs |
| `languages` | `en` | 2-char language code |
| `countries` | `us` | 2-char country code |
| `runtimes` | `30-90` | Range in minutes |
| `studios` | `marvel-studios` | Studio slugs |

#### Rating Filters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `ratings` | `75-100` | Trakt rating range (0-100) |
| `votes` | `5000-10000` | Trakt vote count range |
| `tmdb_ratings` | `7.0-10.0` | TMDB rating (0.0-10.0) |
| `imdb_ratings` | `7.0-10.0` | IMDB rating (0.0-10.0) |
| `rt_meters` | `80-100` | Rotten Tomatoes meter (0-100, movies only) |
| `metascores` | `70-100` | Metacritic score (0-100, movies only) |

#### Show-Specific Filters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `certifications` | `tv-pg,tv-14` | US content certification |
| `networks` | `HBO,Netflix` | Network name |
| `status` | `returning series` | Show status (see values above) |

## Standard Media Objects (Minimal)

```json
// movie
{ "title": "Batman Begins", "year": 2005,
  "ids": { "trakt": 1, "slug": "batman-begins-2005", "imdb": "tt0372784", "tmdb": 272 } }

// show
{ "title": "Breaking Bad", "year": 2008,
  "ids": { "trakt": 1, "slug": "breaking-bad", "tvdb": 81189, "imdb": "tt0903747", "tmdb": 1396 } }

// episode
{ "season": 1, "number": 1, "title": "Pilot",
  "ids": { "trakt": 16, "tvdb": 349232, "imdb": "tt0959621", "tmdb": 62085 } }
```

## Images

Trakt does **not** serve images directly. Use the IDs to fetch images from TMDB, TVDB, Fanart.tv, or OMDB. TMDB is the most common choice — use `tmdb` ID with the [TMDB API](https://developers.themoviedb.org/3).

## Endpoints Currently Used

### `/movies/anticipated` — Most anticipated movies
Pagination, Extended Info, Filters. Ranked by number of user lists containing the movie.

```json
[{ "list_count": 5362, "movie": { "title": "...", "year": 2026, "ids": {...} } }]
```
- **`list_count`** — number of Trakt users with this on a list. **Currently used as `popularity_score`.**

### `/shows/anticipated` — Most anticipated shows
Same structure as movies: `list_count` + `show` object.

### `/shows/favorited/{period}` — Most favorited shows (all time)
Used to find popular returning series. Wrapped response: `{ "user_count": N, "show": {...} }`.

### `/shows/popular` — Popular shows
Returns show objects directly (no wrapper). Popularity = rating percentage × number of ratings.

### `/shows/{id}/next_episode` — Next episode to air
Returns episode object or `204 No Content` if none scheduled. Used to detect upcoming season premieres (`episode.number == 1 && episode.season > 1`).

## All Available Endpoints (170 total)

### Movies

| Endpoint | Description | Wrapper field | Supports |
|----------|-------------|---------------|----------|
| `/movies/trending` | Currently being watched | `watchers` (int) | Pagination, Extended, Filters |
| `/movies/popular` | Most popular (rating × votes) | none (direct array) | Pagination, Extended, Filters |
| `/movies/anticipated` | Most anticipated (list count) | `list_count` (int) | Pagination, Extended, Filters |
| `/movies/boxoffice` | US weekend box office (top 10) | `revenue` (int, USD) | Extended |
| `/movies/recommended/{period}` | Most recommended | `user_count` (int) | Pagination, Extended, Filters |
| `/movies/played/{period}` | Most played | `play_count`, `watcher_count`, `collected_count` | Pagination, Extended, Filters |
| `/movies/watched/{period}` | Most watched (unique users) | `watcher_count`, `play_count`, `collected_count` | Pagination, Extended, Filters |
| `/movies/collected/{period}` | Most collected | `collected_count`, `watcher_count`, `play_count` | Pagination, Extended, Filters |
| `/movies/updates/{start_date}` | Recently updated movies | full movie object | Pagination, Extended |
| `/movies/updates/id/{start_date}` | Recently updated Trakt IDs | ID array | Pagination |
| `/movies/{id}` | Single movie details | full movie object | Extended |
| `/movies/{id}/aliases` | Alternative titles | — | — |
| `/movies/{id}/releases/{country}` | Release dates by country | — | — |
| `/movies/{id}/translations/{language}` | Translations | — | — |
| `/movies/{id}/comments/{sort}` | User comments | — | Pagination |
| `/movies/{id}/lists/{type}/{sort}` | Lists containing this movie | — | Pagination |
| `/movies/{id}/people` | Cast and crew | — | Extended |
| `/movies/{id}/ratings` | Rating distribution | — | — |
| `/movies/{id}/related` | Related movies | — | Pagination, Extended |
| `/movies/{id}/stats` | Aggregate stats | — | — |
| `/movies/{id}/studios` | Production studios | — | — |
| `/movies/{id}/watching` | Users watching right now | — | Extended |

**Period values:** `daily`, `weekly` (default), `monthly`, `yearly`, `all`.

### Shows

| Endpoint | Description | Wrapper field | Supports |
|----------|-------------|---------------|----------|
| `/shows/trending` | Currently being watched | `watchers` (int) | Pagination, Extended, Filters |
| `/shows/popular` | Most popular (rating × votes) | none (direct array) | Pagination, Extended, Filters |
| `/shows/anticipated` | Most anticipated (list count) | `list_count` (int) | Pagination, Extended, Filters |
| `/shows/recommended/{period}` | Most recommended | `user_count` (int) | Pagination, Extended, Filters |
| `/shows/played/{period}` | Most played | `play_count`, `watcher_count`, `collected_count`, `collector_count` | Pagination, Extended, Filters |
| `/shows/watched/{period}` | Most watched (unique users) | `watcher_count`, `play_count`, `collected_count`, `collector_count` | Pagination, Extended, Filters |
| `/shows/collected/{period}` | Most collected | `collected_count`, `collector_count`, `watcher_count`, `play_count` | Pagination, Extended, Filters |
| `/shows/updates/{start_date}` | Recently updated shows | — | Pagination, Extended |
| `/shows/updates/id/{start_date}` | Recently updated Trakt IDs | — | Pagination |
| `/shows/{id}` | Single show details | — | Extended |
| `/shows/{id}/aliases` | Alternative titles | — | — |
| `/shows/{id}/certifications` | Content ratings | — | — |
| `/shows/{id}/translations/{language}` | Translations | — | — |
| `/shows/{id}/comments/{sort}` | User comments | — | Pagination |
| `/shows/{id}/lists/{type}/{sort}` | Lists containing this show | — | Pagination |
| `/shows/{id}/people` | Cast and crew | — | Extended |
| `/shows/{id}/ratings` | Rating distribution | — | — |
| `/shows/{id}/related` | Related shows | — | Pagination, Extended |
| `/shows/{id}/stats` | Aggregate stats | — | — |
| `/shows/{id}/studios` | Production studios | — | — |
| `/shows/{id}/watching` | Users watching right now | — | Extended |
| `/shows/{id}/next_episode` | Next scheduled episode | — | Extended |
| `/shows/{id}/last_episode` | Last aired episode | — | Extended |
| `/shows/{id}/seasons` | All seasons | — | Extended |
| `/shows/{id}/seasons/{season}` | Single season episodes | — | Extended |
| `/shows/{id}/seasons/{season}/episodes/{episode}` | Single episode | — | Extended |
| `/shows/{id}/progress/watched` | Watch progress (OAuth) | — | — |
| `/shows/{id}/progress/collection` | Collection progress (OAuth) | — | — |

### Calendars

All calendar endpoints accept `{start_date}` (YYYY-MM-DD) and `{days}` (1-33). Default: today + 7 days. Not paginated — returns all results in the date range. Support Extended Info and Filters.

| Endpoint | Description | Response structure |
|----------|-------------|-------------------|
| `/calendars/all/movies/{start_date}/{days}` | Theatrical releases | `{ "released": "YYYY-MM-DD", "movie": {...} }` |
| `/calendars/all/dvd/{start_date}/{days}` | DVD/Blu-ray releases | `{ "released": "YYYY-MM-DD", "movie": {...} }` |
| `/calendars/all/shows/{start_date}/{days}` | All airing episodes | `{ "first_aired": "ISO8601", "episode": {...}, "show": {...} }` |
| `/calendars/all/shows/new/{start_date}/{days}` | New series (S01E01 only) | Same as shows |
| `/calendars/all/shows/premieres/{start_date}/{days}` | Season premieres (any S, E01) | Same as shows |
| `/calendars/my/*` | Same 5 endpoints, filtered to user's watchlist/collection (OAuth required) | Same structures |

Response headers: `X-Start-Date`, `X-End-Date`. Cache: ~8 hours.

**Note:** `/calendars/all/shows/` returns ALL episodes (thousands per week). Use `/premieres/` or `/new/` for manageable results, or filter client-side.

### Search

| Endpoint | Description |
|----------|-------------|
| `/search/{type}?query=...` | Text search across titles/overviews. Type: `movie`, `show`, `episode`, `person`, `list` (comma-separated for multiple). Returns `{ "type": "movie", "score": 26.0, "movie": {...} }` |
| `/search/{id_type}/{id}?type=...` | ID lookup. id_type: `trakt`, `imdb`, `tmdb`, `tvdb`. Returns matching media objects. |

### People

| Endpoint | Description |
|----------|-------------|
| `/people/{id}` | Person details (name, bio, birthday, death, gender, hometown, images via TMDB) |
| `/people/{id}/movies` | Movie credits (cast + crew roles) |
| `/people/{id}/shows` | Show credits (cast + crew roles) |
| `/people/updates/{start_date}` | Recently updated people |

### Lists

| Endpoint | Description |
|----------|-------------|
| `/lists/popular` | Popular user-created lists |
| `/lists/trending` | Trending lists |
| `/lists/{id}` | List details |
| `/lists/{id}/items/{type}` | Items on a list |

### Other

| Endpoint | Description |
|----------|-------------|
| `/genres/{type}` | All genres for movies or shows |
| `/certifications/{type}` | Content certifications (US) |
| `/countries/{type}` | Country codes |
| `/languages/{type}` | Language codes |
| `/networks` | TV networks |

### User/Sync Endpoints (OAuth required, not used by ingester)

`/sync/watchlist`, `/sync/history`, `/sync/collection`, `/sync/ratings`, `/sync/watched`, `/sync/recommendations`, `/users/{id}/lists`, `/users/{id}/history`, `/users/{id}/ratings`, `/users/{id}/watchlist`, `/users/{id}/stats`, `/checkin`, `/scrobble/*`.

## Stats Object

`GET /movies/{id}/stats` and `GET /shows/{id}/stats` return:

```json
{
  "watchers": 39204,      // unique users who watched
  "plays": 51033,         // total play count
  "collectors": 27379,    // users who collected
  "comments": 36,
  "lists": 4561,          // lists containing this item
  "votes": 7866,
  "recommended": 54321    // users who recommended
}
```

For shows, also includes `collected_episodes` (total episodes collected across all users).

## Popularity Metrics Summary

| Endpoint | Metric | What it measures |
|----------|--------|-----------------|
| `/movies/anticipated` | `list_count` | Users with movie on a list (anticipation) |
| `/movies/trending` | `watchers` | Users watching right now |
| `/movies/boxoffice` | `revenue` | US weekend box office (USD) |
| `/movies/recommended/{period}` | `user_count` | Users who recommended |
| `/movies/played/{period}` | `play_count` | Total plays in period |
| `/movies/watched/{period}` | `watcher_count` | Unique watchers in period |
| `/movies/collected/{period}` | `collected_count` | Users who collected in period |
| `/shows/anticipated` | `list_count` | Users with show on a list |
| `/shows/trending` | `watchers` | Users watching right now |
| `/shows/recommended/{period}` | `user_count` | Users who recommended |
| `/{type}/{id}/stats` | multiple | Aggregate all-time stats |

## Endpoint Relevance for Events Tracker

**Currently used:**
- `/movies/anticipated` and `/shows/anticipated` — primary source for upcoming content with anticipation ranking
- `/shows/favorited/all` + `/shows/popular` — find returning series, then `/shows/{id}/next_episode` for season premiere dates

**High value, not yet used:**
- `/calendars/all/movies/{start_date}/{days}` — direct calendar of theatrical releases with exact dates. Could replace or supplement anticipated endpoint for near-term movies.
- `/calendars/all/shows/premieres/{start_date}/{days}` — season premieres with dates, much simpler than the current favorited→next_episode approach.
- `/calendars/all/shows/new/{start_date}/{days}` — brand new series premieres (S01E01). Currently not tracked separately.
- `/movies/boxoffice` — weekend box office revenue. Could enrich active movies with financial performance data.
- `/movies/trending` + `/shows/trending` — real-time watching data, useful for "what's hot right now" signals.

**Lower priority but interesting:**
- `/movies/{id}/stats` + `/shows/{id}/stats` — rich aggregate stats (watchers, plays, collectors, votes, lists). Could improve popularity scoring.
- `/search/{type}` — cross-reference or deduplicate with other ingesters.
- `/people/{id}/movies` + `/people/{id}/shows` — cast/crew data for enrichment.
- `/calendars/all/dvd/{start_date}/{days}` — home media releases.
