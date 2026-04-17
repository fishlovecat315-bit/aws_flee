from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AllocationRuleResponse(BaseModel):
    id: int
    account_name: str
    tag_value: str | None
    rule_type: str
    business_module: str | None
    department: str | None
    ratios: dict | None
    special_config: dict | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AllocationRuleUpdate(BaseModel):
    department: str | None = None
    ratios: dict | None = None
    special_config: dict | None = None
    is_active: bool | None = None


class AllocationRuleCreate(BaseModel):
    account_name: str
    tag_value: str | None = None
    rule_type: str = "shared"
    business_module: str | None = None
    department: str | None = None
    ratios: dict | None = None
    special_config: dict | None = None
    is_active: bool = True


class RecalculateRequest(BaseModel):
    start_date: date
    end_date: date
