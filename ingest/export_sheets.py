"""Export top events query to a Google Sheet tab.

Usage:
    cd backend
    python -m ingest.export_sheets              # Export to configured sheet/tab
    python -m ingest.export_sheets --dry-run    # Print rows without writing
"""

import argparse
import asyncio
import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from sqlalchemy import text

from .config import settings
from .db import async_session_maker

QUERY = text("""
WITH dataset AS (
    SELECT
        to_char(start_date, 'YYYY-MM') AS year_month,
        start_date,
        c.name AS category,
        title,
        e.description,
        popularity_score,
        source_url,
        dense_rank() OVER (
            PARTITION BY c.name
            ORDER BY popularity_score DESC
        ) AS dense_rank
    FROM public.events e
    INNER JOIN public.categories c ON e.category_id = c.id
    WHERE start_date < '2027-01-01'
      AND start_date >= date_trunc('month', current_date)
    ORDER BY start_date
)
SELECT
    year_month,
    start_date,
    category,
    title,
    description,
    popularity_score,
    source_url
FROM dataset
WHERE dense_rank <= 15 OR popularity_score >= 1000000
ORDER BY start_date, category
""")

HEADERS = [
    "year_month",
    "start_date",
    "category",
    "title",
    "description",
    "popularity_score",
    "source_url",
]


async def fetch_rows() -> list[list]:
    """Run the query and return rows as lists of strings."""
    async with async_session_maker() as session:
        result = await session.execute(QUERY)
        rows = []
        for row in result:
            rows.append([
                str(v) if v is not None else ""
                for v in row
            ])
    return rows


def _resolve_credentials_path() -> Path:
    """Find the credentials JSON file."""
    raw = settings.GOOGLE_CREDENTIALS_FILE
    if not raw:
        print("Error: GOOGLE_CREDENTIALS_FILE not set in .env")
        sys.exit(1)

    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path

    # Check relative to ingest/ folder, then CWD
    this_dir = Path(__file__).resolve().parent
    candidates = [
        this_dir / raw,
        Path.cwd() / raw,
        this_dir.parent / raw,
        this_dir.parents[1] / raw,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    print(f"Error: Credentials file '{raw}' not found")
    sys.exit(1)


def _resize_table_and_filter(gc, spreadsheet_id: str, sheet_id: int, total_rows: int, num_cols: int):
    """Resize the table, basicFilter, and bandedRanges to match the new row count."""
    # Fetch current metadata for this sheet
    resp = gc.http_client.request(
        "get",
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
        params={"fields": "sheets(properties(sheetId),basicFilter,bandedRanges,tables)"},
    )
    data = resp.json()

    target_sheet = None
    for sheet in data.get("sheets", []):
        if sheet["properties"]["sheetId"] == sheet_id:
            target_sheet = sheet
            break

    if not target_sheet:
        return

    new_range = {
        "sheetId": sheet_id,
        "startRowIndex": 0,
        "endRowIndex": total_rows,
        "startColumnIndex": 0,
        "endColumnIndex": num_cols,
    }

    def batch(requests):
        if requests:
            gc.http_client.request(
                "post",
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                json={"requests": requests},
            )

    # Step 1: Clear filter first (required before resizing table/banding)
    if target_sheet.get("basicFilter"):
        batch([{"clearBasicFilter": {"sheetId": sheet_id}}])

    # Step 2: Resize table and banded ranges
    requests = []
    for table in target_sheet.get("tables", []):
        table_range = table.get("range", {})
        if table_range.get("startColumnIndex", 0) == 0 and table_range.get("endColumnIndex") == num_cols:
            requests.append({
                "updateTable": {
                    "table": {"tableId": table["tableId"], "range": new_range},
                    "fields": "range",
                }
            })

    for banded in target_sheet.get("bandedRanges", []):
        br = banded.get("range", {})
        if br.get("startColumnIndex", 0) == 0 and br.get("endColumnIndex") == num_cols:
            requests.append({
                "updateBanding": {
                    "bandedRange": {"bandedRangeId": banded["bandedRangeId"], "range": new_range},
                    "fields": "range",
                }
            })
    batch(requests)

    # Step 3: Re-set the filter with new range
    batch([{"setBasicFilter": {"filter": {"range": new_range}}}])


def write_to_sheet(rows: list[list]) -> int:
    """Write rows to the configured Google Sheet tab, preserving formatting."""
    creds_path = _resolve_credentials_path()
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    gc = gspread.authorize(creds)

    sheet_id = settings.GOOGLE_SHEET_ID
    tab_name = settings.GOOGLE_SHEET_TAB

    if not sheet_id:
        print("Error: GOOGLE_SHEET_ID not set in .env")
        sys.exit(1)

    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(tab_name)

    # Clear only values (preserves conditional formatting, borders, colors)
    worksheet.clear()

    # Write header + data
    all_rows = [HEADERS] + rows
    total_rows = len(all_rows)
    num_cols = len(HEADERS)
    worksheet.update(range_name="A1", values=all_rows)

    # Resize table, filter, and banded ranges to match new row count
    _resize_table_and_filter(gc, sheet_id, worksheet.id, total_rows, num_cols)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m ingest.export_sheets",
        description="Export top events to Google Sheets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print rows without writing to Google Sheets",
    )
    args = parser.parse_args()

    rows = asyncio.run(fetch_rows())
    print(f"Fetched {len(rows)} rows from database.")

    if args.dry_run:
        for row in rows[:10]:
            print(row)
        if len(rows) > 10:
            print(f"... and {len(rows) - 10} more rows")
        print("Dry run complete — no sheet writes.")
    else:
        count = write_to_sheet(rows)
        tab = settings.GOOGLE_SHEET_TAB
        print(f"Wrote {count} rows + header to '{tab}'.")


if __name__ == "__main__":
    main()
