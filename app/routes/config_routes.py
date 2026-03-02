"""Redirect /config → /export (301 permanent)."""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/config")
async def config_redirect():
    return RedirectResponse("/export", status_code=301)
