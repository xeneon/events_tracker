"""Home page: run buttons, status badges, live log panel."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .. import runner
from ingest.__main__ import SOURCE_ALIASES

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/")
async def home(request: Request):
    statuses = runner.get_all_statuses()
    return templates.TemplateResponse("home.html", {"request": request, "statuses": statuses})


@router.post("/run/{source}")
async def run_source(source: str):
    if source != "all" and source not in SOURCE_ALIASES:
        return JSONResponse({"error": f"Unknown source: {source}"}, status_code=404)
    run_id = runner.start_run(source_alias=None if source == "all" else source)
    return JSONResponse({"run_id": run_id})


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
