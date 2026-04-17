from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import AllocationRule, AllocationRuleHistory


class RuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_rules(self) -> list[AllocationRule]:
        """Return all active allocation rules."""
        result = await self.db.execute(
            select(AllocationRule).order_by(AllocationRule.id)
        )
        return list(result.scalars().all())

    async def get_rule_by_id(self, rule_id: int) -> AllocationRule | None:
        """Return a single rule by id, or None if not found."""
        result = await self.db.execute(
            select(AllocationRule).where(AllocationRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def update_rule(self, rule_id: int, update_data: dict) -> AllocationRule:
        """Update a rule, recording the old value in allocation_rule_history."""
        rule = await self.get_rule_by_id(rule_id)
        if rule is None:
            raise ValueError(f"Rule {rule_id} not found")

        # Capture old value before mutation
        old_value = {
            "department": rule.department,
            "ratios": rule.ratios,
            "special_config": rule.special_config,
            "is_active": rule.is_active,
        }

        # Apply updates
        for field, value in update_data.items():
            if value is not None or field == "is_active":
                setattr(rule, field, value)

        rule.updated_at = datetime.now(tz=timezone.utc)

        # Write history entry
        new_value = {
            "department": rule.department,
            "ratios": rule.ratios,
            "special_config": rule.special_config,
            "is_active": rule.is_active,
        }
        history = AllocationRuleHistory(
            rule_id=rule_id,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_rule_by_tag(self, account_name: str, tag_value: str | None, business_module: str | None = None) -> AllocationRule | None:
        query = select(AllocationRule).where(
            AllocationRule.account_name == account_name,
            AllocationRule.is_active == True,  # noqa: E712
        )
        if tag_value is None:
            query = query.where(AllocationRule.tag_value.is_(None))
        else:
            query = query.where(AllocationRule.tag_value == tag_value)
        if business_module is not None:
            query = query.where(AllocationRule.business_module == business_module)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_rule(self, data: dict) -> AllocationRule:
        rule = AllocationRule(**data)
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule
