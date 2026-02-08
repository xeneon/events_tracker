import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import current_active_user, current_superuser
from app.database import get_async_session
from app.models.user import User
from app.schemas.event import (
    EventCalendarItem,
    EventCreate,
    EventRead,
    EventUpdate,
    PaginatedEvents,
)
from app.services import event_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=PaginatedEvents)
async def list_events(
    session: AsyncSession = Depends(get_async_session),
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    country_code: str | None = None,
    impact_level_min: int | None = None,
    tags: list[str] | None = Query(None),
    search: str | None = None,
    is_approved: bool | None = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    events, total = await event_service.list_events(
        session,
        page=page,
        per_page=per_page,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        country_code=country_code,
        impact_level_min=impact_level_min,
        tags=tags,
        search=search,
        is_approved=is_approved,
    )
    return PaginatedEvents(
        items=events,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/calendar", response_model=list[EventCalendarItem])
async def calendar_events(
    start_date: date,
    end_date: date,
    category_ids: list[int] | None = Query(None),
    country_code: str | None = None,
    search: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    items = await event_service.get_calendar_events(
        session,
        start_date=start_date,
        end_date=end_date,
        category_ids=category_ids,
        country_code=country_code,
        search=search,
    )
    return items


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    event = await event_service.get_event(session, event_id)
    if not event:
        raise NotFoundError("Event not found")
    return event


@router.post("", response_model=EventRead, status_code=201)
async def create_event(
    data: EventCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    event = await event_service.create_event(
        session,
        **data.model_dump(),
        created_by_user_id=user.id,
        is_approved=user.is_superuser,
    )
    return event


@router.put("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    event = await event_service.get_event(session, event_id)
    if not event:
        raise NotFoundError("Event not found")
    if not user.is_superuser and event.created_by_user_id != user.id:
        raise ForbiddenError("Not authorized to update this event")

    update_data = data.model_dump(exclude_unset=True)
    event = await event_service.update_event(session, event, **update_data)
    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_superuser),
):
    event = await event_service.get_event(session, event_id)
    if not event:
        raise NotFoundError("Event not found")
    await event_service.delete_event(session, event)


@router.post("/{event_id}/approve", response_model=EventRead)
async def approve_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_superuser),
):
    event = await event_service.get_event(session, event_id)
    if not event:
        raise NotFoundError("Event not found")
    event = await event_service.update_event(session, event, is_approved=True)
    return event
