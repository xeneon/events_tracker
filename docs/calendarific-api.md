# Calendarific API Reference

Full reference for the Calendarific Holiday API v2, used by `ingest/calendarific.py`.

Official docs: https://calendarific.com/api-documentation

## Authentication

All requests require `api_key` as a query parameter:

```
https://calendarific.com/api/v2/holidays?api_key=YOUR_KEY&country=US&year=2026
```

API keys are created at https://calendarific.com/account after signup.

## Rate Limits

| Plan | Limit |
|------|-------|
| Free | 1,000 requests / day |
| Basic | Based on subscription |
| Premium | Higher monthly limits |

429 status code when exceeded. Error responses use a `meta` wrapper:

```json
{ "meta": { "code": 429, "error_type": "rate limit", "error_detail": "..." }, "response": [] }
```

## Base URL

```
https://calendarific.com/api/v2
```

## Endpoints

### `GET /holidays` — Holiday data (primary endpoint)

#### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | string | API key |
| `country` | string | ISO 3166-1 alpha-2 country code (e.g. `US`, `GB`, `FR`) |
| `year` | integer | Year (up to 2049) |

#### Optional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `month` | integer | Filter to specific month (1-12) |
| `day` | integer | Filter to specific day (1-31) |
| `location` | string | ISO 3166-2 subdivision (e.g. `us-ny`, `gb-eng`). Filters to state/province. |
| `type` | string | Filter by type: `national`, `local`, `religious`, `observance` |
| `language` | string | 2-letter ISO 639 code (e.g. `fr`). **Premium plans only.** |
| `uuid` | boolean | Include UUID per holiday. **Professional plan+.** |

#### Response Structure

```json
{
  "meta": { "code": 200 },
  "response": {
    "holidays": [
      {
        "name": "New Year's Day",
        "description": "New Year's Day is the first day of the Gregorian calendar...",
        "country": { "id": "us", "name": "United States" },
        "date": {
          "iso": "2026-01-01",
          "datetime": { "year": 2026, "month": 1, "day": 1 }
        },
        "type": ["National holiday"],
        "primary_type": "Federal Holiday",
        "canonical_url": "https://calendarific.com/holiday/us/new-year-day",
        "urlid": "us/new-year-day",
        "locations": "All",
        "states": "All"
      }
    ]
  }
}
```

#### Holiday Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Holiday name |
| `description` | string | Full description |
| `country` | object | `{ "id": "us", "name": "United States" }` |
| `date.iso` | string | ISO date (`YYYY-MM-DD`), sometimes includes time for observances |
| `date.datetime` | object | `{ "year", "month", "day" }`, may include `"hour", "minute", "second"` |
| `type` | string[] | Array of type labels (e.g. `["National holiday"]`, `["Local holiday"]`) |
| `primary_type` | string | Single primary classification (see table below) |
| `canonical_url` | string | Link to calendarific.com holiday page |
| `urlid` | string | URL-safe identifier (e.g. `us/new-year-day`) |
| `locations` | string | `"All"` or comma-separated state abbreviations (e.g. `"MA, MS, NY, WI"`) |
| `states` | string or array | `"All"` for nationwide, or array of state objects |

#### State Object (when `states` is an array)

```json
{
  "id": 36,
  "abbrev": "NY",
  "name": "New York",
  "exception": null,
  "iso": "us-ny"
}
```

#### `primary_type` Values (US)

| primary_type | Description |
|--------------|-------------|
| `Federal Holiday` | US federal holidays (12 per year) |
| `State Holiday` | State-level holidays |
| `State Legal Holiday` | State legal holidays (same as State Holiday in practice) |
| `State Observance` | State-level observances |
| `Local holiday` | Local/city holidays |
| `Local observance` | Local observances |
| `Observance` | General observances (Earth Day, etc.) |
| `United Nations observance` | UN-designated days |
| `Worldwide observance` | Global observances |
| `Annual Monthly Observance` | Month-long observances (Black History Month, etc.) |
| `Season` | Seasonal markers (solstices, equinoxes) |
| `Clock change/Daylight Saving Time` | DST transitions |
| `Christian` | Christian holidays |
| `Muslim` | Islamic holidays |
| `Jewish holiday` | Jewish holidays |
| `Jewish commemoration` | Jewish commemorations |
| `Hindu Holiday` | Hindu holidays |
| `Orthodox` | Orthodox Christian holidays |
| `Sporting event` | Major sporting events (Super Bowl, etc.) |

#### `type` Array Values (US)

`National holiday`, `Local holiday`, `Local observance`, `Observance`, `Worldwide observance`, `United Nations observance`, `Christian`, `Orthodox`, `Hebrew`, `Muslim`, `Hinduism`, `Season`, `Clock change/Daylight Saving Time`, `Sporting event`.

**Note:** `type` is an array and can contain multiple values. `primary_type` is always a single string and is more specific (distinguishes Federal vs State holidays). The ingester uses `primary_type` for category mapping.

### `GET /languages` — Supported languages

Returns all languages available for holiday translations.

```json
{
  "meta": { "code": 200 },
  "response": {
    "languages": [
      { "code": "en", "name": "English", "nativeName": "English" },
      { "code": "fr", "name": "French", "nativeName": "Français" }
    ]
  }
}
```

54 languages supported.

### `GET /countries` — Supported countries

Returns all countries with holiday data.

```json
{
  "meta": { "code": 200 },
  "response": {
    "countries": [
      {
        "country_name": "United States",
        "iso-3166": "US",
        "total_holidays": 633,
        "supported_languages": 1,
        "uuid": "...",
        "flag_unicode": "🇺🇸"
      }
    ]
  }
}
```

230 countries supported.

## Error Codes

| HTTP Code | API Code | Description |
|-----------|----------|-------------|
| 200 | 200 | Success |
| 401 | 401 | Missing or invalid API key |
| 422 | 602 | Invalid query parameters |
| 422 | 603 | Feature requires higher subscription |
| 429 | 429 | Rate limit exceeded |
| 500 | 500 | Server error |
| 503 | 600 | Maintenance mode |

## Data Volume (US)

- Full year: ~633 raw holiday entries
- After deduplication (by urlid + date): ~250 unique holidays
- Federal holidays: 12
- With `type=national` filter: 12 results
- Per month: ~20-50 raw entries depending on month

## Deduplication Notes

The API returns the **same holiday multiple times** — once per state grouping. For example, "New Year's Day" appears as:
1. Federal Holiday (locations: "All")
2. State Holiday for TX
3. State Holiday for MA, MS, NY, WI
4. State Holiday for other state groupings

The ingester deduplicates by `urlid + date`, keeping the highest-priority entry (Federal > State Legal > State > State Observance > Local).

## How the Ingester Uses This API

- Queries `/holidays` for US, current year and next year
- No `type` or `location` filter — fetches all holidays
- Deduplicates in `fetch_events()` before normalization
- Maps `primary_type` to category slugs: `federal-holiday`, `state-holiday`, `observance`, `religious`, `other`
- Uses `states[].abbrev` to build region string
- No popularity metric (holidays have no anticipation data)

## Endpoint Relevance for Events Tracker

**Currently used:**
- `/holidays` with `country=US` — sole data source, fetching all US holidays for 2 years

**Could be useful:**
- Adding more countries (`country=GB`, `country=CA`, etc.) for international holiday tracking
- Using `type=national` filter to create a "major holidays only" tier
- Using `location` filter for state-specific holiday calendars
- `/countries` endpoint to dynamically list available countries for a multi-country expansion
