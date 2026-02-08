from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    color: str = Field("#6366f1", max_length=7)
    icon: str | None = None
    description: str | None = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    slug: str | None = Field(None, max_length=100)
    color: str | None = Field(None, max_length=7)
    icon: str | None = None
    description: str | None = None
    sort_order: int | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    color: str
    icon: str | None = None
    description: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}
