from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SyncLogResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    accounts_synced: Optional[str]
    records_count: Optional[int]
    error_message: Optional[str]
    model_config = ConfigDict(from_attributes=True)
