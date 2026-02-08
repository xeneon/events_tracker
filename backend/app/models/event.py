import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.tag import event_tags


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Temporal
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    timezone: Mapped[str | None] = mapped_column(String(50))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=True)

    # Classification
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL")
    )
    impact_level: Mapped[int | None] = mapped_column(SmallInteger)  # 1-5
    popularity_score: Mapped[int | None] = mapped_column(Integer)  # Raw metric (e.g. list_count)

    # Location
    country_code: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(200))

    # Recurrence
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))

    # Source tracking
    data_source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    external_id: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(Text)

    # Media
    image_url: Mapped[str | None] = mapped_column(Text)

    # Moderation
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="events")  # noqa: F821
    data_source: Mapped["DataSource"] = relationship(back_populates="events")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(secondary=event_tags, back_populates="events")  # noqa: F821

    __table_args__ = (
        Index("ix_events_date_range", "start_date", "end_date"),
        Index("ix_events_category", "category_id"),
        Index("ix_events_country", "country_code"),
        Index("ix_events_approved", "is_approved", postgresql_where=(is_approved == False)),  # noqa: E712
        UniqueConstraint("data_source_id", "external_id", name="uq_events_source_external"),
    )
