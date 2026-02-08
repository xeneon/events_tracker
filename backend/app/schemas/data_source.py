from datetime import datetime

from pydantic import BaseModel


class DataSourceRead(BaseModel):
    id: int
    name: str
    source_type: str
    base_url: str | None = None
    is_active: bool
    last_synced_at: datetime | None = None
    sync_interval: int | None = None

    model_config = {"from_attributes": True}
