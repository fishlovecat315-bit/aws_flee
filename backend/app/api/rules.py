from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.repositories.rule_repository import RuleRepository
from backend.app.schemas.rule import (
    AllocationRuleCreate,
    AllocationRuleResponse,
    AllocationRuleUpdate,
    RecalculateRequest,
)
from backend.app.services.allocation_engine import AllocationEngine

router = APIRouter()


@router.get("/rules", response_model=list[AllocationRuleResponse])
async def get_rules(db: AsyncSession = Depends(get_db)):
    """Return all allocation rules."""
    repo = RuleRepository(db)
    rules = await repo.get_all_rules()
    return rules


@router.post("/rules", response_model=AllocationRuleResponse, status_code=200)
async def upsert_rule(
    body: AllocationRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建或更新分摊规则（按 account_name + tag_value 唯一确定）。"""
    if body.ratios is not None:
        total = sum(float(v) for v in body.ratios.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail=f"ratios 之和必须为 1.0，当前为 {total:.4f}")

    repo = RuleRepository(db)
    existing = await repo.get_rule_by_tag(body.account_name, body.tag_value, body.business_module)
    if existing:
        update_data = {k: v for k, v in body.model_dump().items()
                       if k not in ("account_name", "tag_value") and v is not None}
        return await repo.update_rule(existing.id, update_data)
    return await repo.create_rule(body.model_dump())


@router.put("/rules/{rule_id}", response_model=AllocationRuleResponse)
async def update_rule(
    rule_id: int,
    body: AllocationRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an allocation rule. Validates that ratios sum to 1.0 if provided."""
    if body.ratios is not None:
        total = sum(float(v) for v in body.ratios.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail="ratios must sum to 1.0")

    repo = RuleRepository(db)
    try:
        updated = await repo.update_rule(rule_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return updated


@router.post("/rules/{rule_id}/recalculate", status_code=202)
async def recalculate_rule(
    rule_id: int,
    body: RecalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger historical recalculation for the given date range."""
    repo = RuleRepository(db)
    rule = await repo.get_rule_by_id(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

    engine = AllocationEngine(db)
    await engine.allocate_date_range(body.start_date, body.end_date)
    return {"message": "Recalculation completed", "rule_id": rule_id}
