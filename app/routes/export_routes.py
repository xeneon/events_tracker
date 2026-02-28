"""Export page: Google Sheets credentials, SQL editor, run + log."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import config_store

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/export")
async def export_get(request: Request, saved: bool = False):
    config = config_store.load_config()
    credentials_info = config_store.get_google_credentials_info()
    default_query = config_store._DEFAULT_EXPORT_QUERY
    is_custom_query = config["EXPORT_QUERY"].strip().replace("\r\n", "\n") != default_query.strip()
    return templates.TemplateResponse("export.html", {
        "request": request,
        "config": config,
        "credentials_info": credentials_info,
        "saved": saved,
        "default_query": default_query,
        "is_custom_query": is_custom_query,
        "active_page": "export",
    })


@router.post("/export/save")
async def export_save(request: Request):
    form = await request.form()
    config = config_store.load_config()
    for key in ("GOOGLE_SHEET_ID", "GOOGLE_SHEET_TAB", "EXPORT_QUERY"):
        config[key] = form.get(key, "")
    creds = (form.get("google_credentials_json", "") or "").strip()
    config_store.save_config(config, google_creds_json=creds if creds else None)
    return RedirectResponse("/export?saved=1", status_code=303)
