from fastapi import APIRouter

from app.api.v1 import auth, categories, data_sources, events, tags, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(events.router)
api_router.include_router(categories.router)
api_router.include_router(tags.router)
api_router.include_router(data_sources.router)
