# IGDB API Reference

Full reference for the IGDB (Internet Game Database) API v4, used by `ingest/igdb.py`.

Official docs: https://api-docs.igdb.com/

## Authentication

- Twitch OAuth2 client credentials: `POST https://id.twitch.tv/oauth2/token` with `client_id`, `client_secret`, `grant_type=client_credentials`
- Tokens valid 60 days, max 25 concurrent
- All requests require headers: `Client-ID: {twitch_client_id}`, `Authorization: Bearer {token}`

## Request Format

Base URL: `https://api.igdb.com/v4`

All requests are **POST** with Apicalypse query syntax in the body. Rate limit: 4 req/sec, 8 concurrent. Max 500 results per request. Caching explicitly permitted.

### Query Syntax (Apicalypse)

```
fields name, cover.url, genres.name;   -- field selection, use .* to expand nested objects
where first_release_date > 1771270800 & hypes > 0;  -- Unix timestamps, & for AND, | for OR
sort hypes desc;
limit 100;
offset 0;
search "Zelda";  -- only works on games, characters, collections, platforms, themes
```

## Endpoints Currently Used

- **`/games`** — core game data. Fields we use: `name, hypes, first_release_date, cover.url, genres.name, platforms.name, summary, involved_companies.company.name, involved_companies.publisher, release_dates.human, release_dates.date, url`.
- **`/popularity_primitives`** — PopScore metrics. Fields: `game_id, value, popularity_type, popularity_source`. We query `where popularity_type = 2` (Want to Play) for anticipation ranking.

## Popularity Primitives (all 11 types)

Updated daily. Values are normalized floats (not absolute counts). Source 121 = IGDB, source 1 = Steam, source 14 = Twitch.

| Type ID | Name | Source | Notes |
|---------|------|--------|-------|
| 1 | Visits | IGDB | Page views on igdb.com |
| 2 | Want to Play | IGDB | Users marking "want to play" — **currently used as primary metric** |
| 3 | Playing | IGDB | Users currently playing |
| 4 | Played | IGDB | Users who have played |
| 5 | 24hr Peak Players | Steam | Live concurrent player count — **PC-only** |
| 6 | Positive Reviews | Steam | Positive review count — **PC-only** |
| 7 | Negative Reviews | Steam | Negative review count — **PC-only** |
| 8 | Total Reviews | Steam | Total review count — **PC-only** |
| 9 | Global Top Sellers | Steam | Current top sellers — **PC-only** |
| 10 | Most Wishlisted Upcoming | Steam | Wishlist count for unreleased games — **PC-only, upcoming games only** |
| 34 | 24hr Hours Watched | Twitch | Viewership hours in last 24h |

### Steam Wishlists (type 10)

Strong anticipation signal for upcoming PC games but **only covers titles with a Steam page**. Console-exclusive games (e.g., GTA VI launching on PS5/Xbox only) will have zero Steam wishlist data. Use alongside "Want to Play" (type 2) which covers all platforms — not as a replacement.

Example query:
```
fields game_id, value; where popularity_type = 10; sort value desc; limit 50;
```

## Available Game Fields (not currently used)

| Field | Type | Description |
|-------|------|-------------|
| `storyline` | String | Full story/plot synopsis |
| `rating` | Double | IGDB user rating (0-100) |
| `rating_count` | Integer | Number of user ratings |
| `aggregated_rating` | Double | External critic score average (Metacritic-like) |
| `aggregated_rating_count` | Integer | Number of critic scores |
| `total_rating` | Double | Combined user + critic average |
| `themes.name` | Expanded | Action, Fantasy, Sci-fi, Horror, Open World, Sandbox, etc. |
| `keywords.name` | Expanded | Detailed tags (e.g., "vehicular combat", "crime") |
| `game_modes.name` | Expanded | Single player, Multiplayer, Co-op, MMO, Battle Royale, Split screen |
| `player_perspectives.name` | Expanded | First person, Third person, Isometric, VR, etc. |
| `franchises.name` | Expanded | Series info (e.g., "Grand Theft Auto") |
| `game_engines.name` | Expanded | Engine tech (e.g., "RAGE", "Unreal Engine 5") |
| `similar_games.name` | Expanded | Related titles (up to 10) |
| `collections.name` | Expanded | Game series groupings |
| `videos.*` | Expanded | YouTube trailers — `video_id` field is the YouTube ID |
| `websites.url` | Expanded | Official site, Wikipedia, Reddit, Twitter, Discord, store links |
| `websites.category` | Integer | 1=official, 2=wikia, 3=wikipedia, 4=facebook, 5=twitter, 13=steam, 14=reddit, 17=gog, 18=discord |
| `external_games.category` | Integer | Cross-platform IDs: 1=steam, 5=gog, 26=epic, 36=psn, 31=xbox |
| `multiplayer_modes.*` | Expanded | onlinemax, offlinemax, lancoop, splitscreen booleans |
| `language_supports.language.name` | Expanded | Localization info |
| `artworks.url` | Expanded | Official artwork images |
| `screenshots.url` | Expanded | In-game screenshot images |

## Other Useful Endpoints

- **`/events`** — Gaming conventions/showcases (E3, Summer Game Fest, Gamescom, PAX, etc.). Fields: `name, description, start_time, end_time, time_zone, event_logo.url, event_networks.url, games.name, live_stream_url, videos.*`. Has future events with dates. Could be a new ingester category.
- **`/game_time_to_beats`** — Completion times. Fields: `game_id, hastily` (speedrun), `normally` (average), `completely` (100%), all in seconds.
- **`/franchises`** — Series groupings. Fields: `name, slug, games, url`.
- **`/collections`** — Game series. Fields: `name, slug, games, url, type`.
- **`/characters`** — Game characters with mugshots, gender, species, descriptions.
- **`/release_dates`** — Platform-specific release dates. Fields: `date, human, platform, region, status`. Status: 0=released, 2=alpha, 3=beta, 4=early_access, 5=offline, 6=cancelled, 7=rumored.
- **`/genres`** — 22 genres: Point-and-click, Fighting, Shooter, Music, Platform, Puzzle, Racing, RTS, RPG, Simulator, Sport, Strategy, TBS, Tactical, Hack-and-slash, Quiz, Pinball, Adventure, Indie, Arcade, Visual Novel, Card & Board, MOBA.
- **`/themes`** — 22 themes: Action, Fantasy, Sci-fi, Horror, Thriller, Survival, Historical, Stealth, Comedy, Business, Drama, Non-fiction, Sandbox, Educational, Kids, Open World, Warfare, Party, 4X, Erotic, Mystery, Romance.
- **`/dumps/{endpoint}`** — Bulk CSV download via S3 presigned URL (valid 5 min). Available for all endpoints.
- **`/webhooks`** — Real-time push notifications on create/update/delete for any endpoint.

## Image URLs

IGDB returns URLs like `//images.igdb.com/igdb/image/upload/t_thumb/{image_id}.jpg`. Prepend `https:` and swap the size token.

Available sizes: `t_thumb`, `t_cover_small`, `t_cover_big`, `t_screenshot_med`, `t_screenshot_big`, `t_720p`, `t_1080p`.

## Enum Reference

### Game Category (deprecated, use game_type)
0=main_game, 1=dlc_addon, 2=expansion, 3=bundle, 4=standalone_expansion, 5=mod, 6=episode, 7=season, 8=remake, 9=remaster, 10=expanded_game, 11=port, 12=fork, 13=pack, 14=update

### Release Date Category (date precision)
0=YYYYMMDD (exact), 1=YYYYMM (month), 2=YYYY (year only), 3-6=YYYYQ1-Q4 (quarter), 7=TBD

### Website Category
1=official, 2=wikia, 3=wikipedia, 4=facebook, 5=twitter, 6=twitch, 8=instagram, 9=youtube, 10=iphone, 11=ipad, 12=android, 13=steam, 14=reddit, 15=itch.io, 16=epicgames, 17=gog, 18=discord, 19=bluesky

### External Game Source
1=steam, 5=gog, 10=youtube, 11=microsoft, 13=apple, 14=twitch, 15=android, 20=amazon_asin, 26=epic_game_store, 31=xbox_marketplace, 36=playstation_store_us
