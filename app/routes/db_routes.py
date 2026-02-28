"""Database viewer: schema browser and SQL query runner."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ingest.db import async_session_maker
from . import templates

router = APIRouter()


@router.get("/db")
async def db_viewer(request: Request):
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
        """))
        rows = result.fetchall()
    schema = {}
    for table_name, column_name, data_type, is_nullable in rows:
        schema.setdefault(table_name, []).append({
            "column": column_name,
            "type": data_type,
            "nullable": is_nullable == "YES",
        })
    return templates.TemplateResponse("db_viewer.html", {
        "request": request,
        "active_page": "db",
        "schema": schema,
    })


@router.post("/db/query")
async def run_query(request: Request):
    body = await request.json()
    sql = (body.get("sql") or "").strip()
    if not sql:
        return JSONResponse({"error": "No SQL provided"}, status_code=400)
    try:
        async with async_session_maker() as session:
            result = await session.execute(text(sql))
            if result.returns_rows:
                columns = list(result.keys())
                rows = [
                    [str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for v in row]
                    for row in result.fetchall()
                ]
                return JSONResponse({"columns": columns, "rows": rows})
            else:
                await session.commit()
                return JSONResponse({"message": f"{result.rowcount} row(s) affected"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
