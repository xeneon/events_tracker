import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    title: str = Field(..., max_length=300)
    description: str | None = None
    start_date: date
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    timezone: str | None = None
    is_all_day: bool = True
    category_id: int | None = None
    impact_level: int | None = Field(None, ge=1, le=5)
    popularity_score: int | None = None
    country_code: str | None = Field(None, max_length=2)
    region: str | None = None
    is_recurring: bool = False
    recurrence_rule: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    tag_ids: list[int] = []


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    timezone: str | None = None
    is_all_day: bool | None = None
    category_id: int | None = None
    impact_level: int | None = Field(None, ge=1, le=5)
    popularity_score: int | None = None
    country_code: str | None = Field(None, max_length=2)
    region: str | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    tag_ids: list[int] | None = None


class TagRead(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    color: str
    icon: str | None = None

    model_config = {"from_attributes": True}


class EventRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    start_date: date
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    timezone: str | None = None
    is_all_day: bool
    category_id: int | None = None
    category: CategoryRead | None = None
    impact_level: int | None = None
    popularity_score: int | None = None
    country_code: str | None = None
    region: str | None = None
    is_recurring: bool
    recurrence_rule: str | None = None
    data_source_id: int | None = None
    external_id: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    created_by_user_id: uuid.UUID | None = None
    is_approved: bool
    tags: list[TagRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventCalendarItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    start: str  # ISO datetime string
    end: str | None = None
    allDay: bool
    color: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    impact_level: int | None = None
    popularity_score: int | None = None
    country_code: str | None = None
    source_url: str | None = None
    rrule: str | None = None

    model_config = {"from_attributes": True}


class PaginatedEvents(BaseModel):
    items: list[EventRead]
    total: int
    page: int
    per_page: int
    pages: int
