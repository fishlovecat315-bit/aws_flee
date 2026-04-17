from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AlertThresholdResponse(BaseModel):
    id: int
    department: str
    monthly_threshold_usd: Decimal
    is_active: bool
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AlertThresholdUpdate(BaseModel):
    monthly_threshold_usd: Decimal
    is_active: bool = True
