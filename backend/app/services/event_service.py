import uuid
from datetime import date, datetime, timedelta

from dateutil.rrule import rrulestr
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.tag import Tag


def _apply_filters(
    stmt: Select,
    *,
    category_id: int | None = None,
    category_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    country_code: str | None = None,
    impact_level_min: int | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
    is_approved: bool | None = None,
) -> Select:
    if category_id is not None:
        stmt = stmt.where(Event.category_id == category_id)
    if category_ids:
        stmt = stmt.where(Event.category_id.in_(category_ids))
    if start_date is not None:
        stmt = stmt.where(
            or_(Event.end_date >= start_date, Event.start_date >= start_date)
        )
    if end_date is not None:
        stmt = stmt.where(Event.start_date <= end_date)
    if country_code is not None:
        stmt = stmt.where(
            or_(Event.country_code == country_code, Event.country_code.is_(None))
        )
    if impact_level_min is not None:
        stmt = stmt.where(Event.impact_level >= impact_level_min)
    if is_approved is not None:
        stmt = stmt.where(Event.is_approved.is_(is_approved))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Event.title.ilike(pattern), Event.description.ilike(pattern))
        )
    if tags:
        stmt = stmt.join(Event.tags).where(Tag.slug.in_(tags))
    return stmt


async def list_events(
    session: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 25,
    **filters,
) -> tuple[list[Event], int]:
    base = select(Event).options(selectinload(Event.category), selectinload(Event.tags))
    base = _apply_filters(base, **filters).distinct()

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = base.order_by(Event.start_date.asc()).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(stmt)
    events = list(result.scalars().unique().all())
    return events, total


async def get_calendar_events(
    session: AsyncSession,
    *,
    start_date: date,
    end_date: date,
    category_ids: list[int] | None = None,
    country_code: str | None = None,
    search: str | None = None,
    is_approved: bool | None = True,
) -> list[dict]:
    stmt = select(Event).options(selectinload(Event.category))
    if is_approved is not None:
        stmt = stmt.where(Event.is_approved.is_(is_approved))
    if category_ids:
        stmt = stmt.where(Event.category_id.in_(category_ids))
    if country_code:
        stmt = stmt.where(
            or_(Event.country_code == country_code, Event.country_code.is_(None))
        )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Event.title.ilike(pattern), Event.description.ilike(pattern))
        )

    # Get non-recurring events in range
    non_recurring = stmt.where(Event.is_recurring.is_(False)).where(
        and_(
            or_(Event.end_date >= start_date, Event.start_date >= start_date),
            Event.start_date <= end_date,
        )
    )
    result = await session.execute(non_recurring)
    events = list(result.scalars().unique().all())

    # Get recurring events (may start before the range)
    recurring = stmt.where(Event.is_recurring.is_(True))
    result = await session.execute(recurring)
    recurring_events = list(result.scalars().unique().all())

    calendar_items = []

    # Add non-recurring events
    for ev in events:
        calendar_items.append(_event_to_calendar_item(ev))

    # Expand recurring events
    for ev in recurring_events:
        calendar_items.extend(_expand_recurring(ev, start_date, end_date))

    return calendar_items


def _event_to_calendar_item(ev: Event) -> dict:
    start = ev.start_date.isoformat()
    if ev.start_time and not ev.is_all_day:
        start = f"{ev.start_date.isoformat()}T{ev.start_time.isoformat()}"

    end = None
    if ev.end_date:
        end = ev.end_date.isoformat()
        if ev.end_time and not ev.is_all_day:
            end = f"{ev.end_date.isoformat()}T{ev.end_time.isoformat()}"

    return {
        "id": str(ev.id),
        "title": ev.title,
        "start": start,
        "end": end,
        "allDay": ev.is_all_day,
        "color": ev.category.color if ev.category else None,
        "category_id": ev.category_id,
        "category_name": ev.category.name if ev.category else None,
        "impact_level": ev.impact_level,
        "popularity_score": ev.popularity_score,
        "country_code": ev.country_code,
        "rrule": None,
    }


def _expand_recurring(ev: Event, range_start: date, range_end: date) -> list[dict]:
    if not ev.recurrence_rule:
        return [_event_to_calendar_item(ev)]

    try:
        rule = rrulestr(ev.recurrence_rule, dtstart=datetime.combine(ev.start_date, datetime.min.time()))
        occurrences = rule.between(
            datetime.combine(range_start, datetime.min.time()),
            datetime.combine(range_end, datetime.max.time()),
            inc=True,
        )
    except Exception:
        return [_event_to_calendar_item(ev)]

    items = []
    duration = timedelta(0)
    if ev.end_date:
        duration = ev.end_date - ev.start_date

    for occ in occurrences:
        occ_date = occ.date()
        start = occ_date.isoformat()
        if ev.start_time and not ev.is_all_day:
            start = f"{occ_date.isoformat()}T{ev.start_time.isoformat()}"

        end = None
        if duration:
            end_date = occ_date + duration
            end = end_date.isoformat()
            if ev.end_time and not ev.is_all_day:
                end = f"{end_date.isoformat()}T{ev.end_time.isoformat()}"

        items.append({
            "id": f"{ev.id}_{occ_date.isoformat()}",
            "title": ev.title,
            "start": start,
            "end": end,
            "allDay": ev.is_all_day,
            "color": ev.category.color if ev.category else None,
            "category_id": ev.category_id,
            "category_name": ev.category.name if ev.category else None,
            "impact_level": ev.impact_level,
            "popularity_score": ev.popularity_score,
            "country_code": ev.country_code,
            "rrule": None,
        })
    return items


async def get_event(session: AsyncSession, event_id: uuid.UUID) -> Event | None:
    stmt = (
        select(Event)
        .options(selectinload(Event.category), selectinload(Event.tags))
        .where(Event.id == event_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_event(
    session: AsyncSession,
    *,
    title: str,
    start_date: date,
    tag_ids: list[int] | None = None,
    **kwargs,
) -> Event:
    event = Event(title=title, start_date=start_date, **kwargs)

    if tag_ids:
        tag_result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        event.tags = list(tag_result.scalars().all())

    session.add(event)
    await session.commit()
    await session.refresh(event, attribute_names=["category", "tags"])
    return event


async def update_event(
    session: AsyncSession,
    event: Event,
    *,
    tag_ids: list[int] | None = None,
    **kwargs,
) -> Event:
    for key, value in kwargs.items():
        setattr(event, key, value)

    if tag_ids is not None:
        tag_result = await session.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        event.tags = list(tag_result.scalars().all())

    session.add(event)
    await session.flush()
    await session.commit()
    # Re-fetch the full event to ensure all attributes are loaded
    return await get_event(session, event.id)  # type: ignore[return-value]


async def delete_event(session: AsyncSession, event: Event) -> None:
    await session.delete(event)
    await session.commit()
