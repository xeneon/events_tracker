import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_active_user
from app.database import get_async_session
from app.models.tag import Tag
from app.models.user import User
from app.schemas.event import TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreateSchema(BaseModel):
    name: str = Field(..., max_length=100)


@router.get("", response_model=list[TagRead])
async def list_tags(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


@router.post("", response_model=TagRead, status_code=201)
async def create_tag(
    data: TagCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
    tag = Tag(name=data.name, slug=slug)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag
