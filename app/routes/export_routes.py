"""Export page: Google Sheets credentials, SQL editor, run + log."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from .. import config_store
from . import templates

router = APIRouter()


@router.get("/export")
async def export_get(request: Request, saved: bool = False):
    config = config_store.load_config()
    credentials_info = config_store.get_google_credentials_info()
    return templates.TemplateResponse("export.html", {
        "request": request,
        "config": config,
        "credentials_info": credentials_info,
        "saved": saved,
        "default_query": config_store.DEFAULT_EXPORT_QUERY,
        "is_custom_query": config_store.is_custom_export_query(config),
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
