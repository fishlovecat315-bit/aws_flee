from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DailyCostItem(BaseModel):
    date: date
    department: str
    account_name: str
    tag_value: str | None
    business_module: str | None
    amount_usd: Decimal


class DailyCostsResponse(BaseModel):
    data: list[DailyCostItem]
    total: int
    page: int
    page_size: int


class MonthlyCostItem(BaseModel):
    year_month: str  # "2024-01"
    department: str
    amount_usd: Decimal


class MonthlyCostsResponse(BaseModel):
    data: list[MonthlyCostItem]
    total: int


class SummaryByDept(BaseModel):
    department: str
    total_amount: Decimal


class SummaryByAccount(BaseModel):
    account_name: str
    total_amount: Decimal


class SummaryByTag(BaseModel):
    tag_value: str | None
    total_amount: Decimal


class SummaryResponse(BaseModel):
    by_department: list[SummaryByDept]
    by_account: list[SummaryByAccount]
    by_tag: list[SummaryByTag]
