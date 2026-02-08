from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import current_superuser
from app.database import get_async_session
from app.models.data_source import DataSource
from app.models.event import Event
from app.models.user import User
from app.schemas.data_source import DataSourceRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/data-sources", response_model=list[DataSourceRead])
async def list_data_sources(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_superuser),
):
    result = await session.execute(select(DataSource).order_by(DataSource.name))
    return list(result.scalars().all())


@router.post("/data-sources/{source_id}/sync")
async def trigger_sync(
    source_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_superuser),
):
    result = await session.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise NotFoundError("Data source not found")

    # Import here to avoid circular imports
    from app.services.ingestion.scheduler import run_ingestion_for_source

    count = await run_ingestion_for_source(source, session)
    return {"status": "ok", "source": source.name, "events_processed": count}


@router.get("/events/pending", response_model=list)
async def pending_events(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_superuser),
):
    from app.schemas.event import EventRead
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Event)
        .options(selectinload(Event.category), selectinload(Event.tags))
        .where(Event.is_approved == False)  # noqa: E712
        .order_by(Event.created_at.desc())
    )
    result = await session.execute(stmt)
    events = list(result.scalars().unique().all())
    return [EventRead.model_validate(e) for e in events]
