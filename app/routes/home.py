"""Home page: run buttons, status badges, live log panel."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .. import runner, config_store
from ingest.__main__ import SOURCE_ALIASES
from . import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def home(request: Request):
    statuses = runner.get_all_statuses()
    return templates.TemplateResponse("home.html", {
        "request": request,
        "statuses": statuses,
        "active_page": "home",
    })


@router.post("/run/{source}")
async def run_source(source: str, request: Request):
    if source not in ("all", "export") and source not in SOURCE_ALIASES:
        return JSONResponse({"error": f"Unknown source: {source}"}, status_code=404)
    export_query = None
    if source == "export":
        try:
            form = await request.form()
            query = (form.get("EXPORT_QUERY") or "").strip()
            if query:
                cfg = config_store.load_config()
                cfg["EXPORT_QUERY"] = query
                config_store.save_config(cfg)
                export_query = query
        except Exception:
            logger.exception("Failed to read/save export query from request")
    run_id = runner.start_run(source_alias=None if source == "all" else source, export_query=export_query)
    return JSONResponse({"run_id": run_id})


@router.get("/api/status")
async def api_status():
    return JSONResponse(runner.get_all_statuses())


@router.get("/stream/{run_id}")
async def stream(run_id: str):
    return StreamingResponse(
        runner.stream_run(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
