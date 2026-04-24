from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import AllocatedCostRecord


class CostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_daily_costs(
        self,
        start_date: date,
        end_date: date,
        department: str | None = None,
        account_name: str | None = None,
        tag_value: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[AllocatedCostRecord], int]:
        """Query allocated_cost_records with optional filters, returns (records, total_count)."""
        base_query = select(AllocatedCostRecord).where(
            AllocatedCostRecord.date >= start_date,
            AllocatedCostRecord.date <= end_date,
        )

        if department is not None:
            base_query = base_query.where(AllocatedCostRecord.department == department)
        if account_name is not None:
            base_query = base_query.where(AllocatedCostRecord.account_name == account_name)
        if tag_value is not None:
            base_query = base_query.where(AllocatedCostRecord.tag_value == tag_value)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count: int = total_result.scalar_one()

        offset = (page - 1) * page_size
        paginated_query = (
            base_query.order_by(AllocatedCostRecord.date.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(paginated_query)
        records = list(result.scalars().all())

        return records, total_count

    async def get_monthly_costs(
        self,
        year: int,
        month: int | None = None,
        department: str | None = None,
        account_name: str | None = None,
    ) -> list[dict]:
        """Aggregate costs by year_month and department.
        Returns list of {year_month, department, amount_usd}.
        """
        year_month_expr = func.date_trunc("month", AllocatedCostRecord.date).label("year_month")

        query = (
            select(
                year_month_expr,
                AllocatedCostRecord.department,
                func.sum(AllocatedCostRecord.amount_usd).label("amount_usd"),
            )
            .where(func.extract("year", AllocatedCostRecord.date) == year)
        )

        if month is not None:
            query = query.where(func.extract("month", AllocatedCostRecord.date) == month)
        if department is not None:
            query = query.where(AllocatedCostRecord.department == department)
        if account_name is not None:
            query = query.where(AllocatedCostRecord.account_name == account_name)

        query = query.group_by(year_month_expr, AllocatedCostRecord.department).order_by(
            year_month_expr, AllocatedCostRecord.department
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "year_month": row.year_month,
                "department": row.department,
                "amount_usd": Decimal(str(row.amount_usd)) if row.amount_usd is not None else Decimal("0"),
            }
            for row in rows
        ]

    async def get_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Return multi-dimensional summary: by_department, by_account, by_tag."""
        base_filter = (
            AllocatedCostRecord.date >= start_date,
            AllocatedCostRecord.date <= end_date,
        )

        # By department
        dept_query = (
            select(
                AllocatedCostRecord.department,
                func.sum(AllocatedCostRecord.amount_usd).label("total_amount"),
            )
            .where(*base_filter)
            .group_by(AllocatedCostRecord.department)
            .order_by(func.sum(AllocatedCostRecord.amount_usd).desc())
        )
        dept_result = await self.db.execute(dept_query)
        by_department = [
            {
                "department": row.department,
                "total_amount": Decimal(str(row.total_amount)) if row.total_amount is not None else Decimal("0"),
            }
            for row in dept_result.all()
        ]

        # By account
        account_query = (
            select(
                AllocatedCostRecord.account_name,
                func.sum(AllocatedCostRecord.amount_usd).label("total_amount"),
            )
            .where(*base_filter)
            .group_by(AllocatedCostRecord.account_name)
            .order_by(func.sum(AllocatedCostRecord.amount_usd).desc())
        )
        account_result = await self.db.execute(account_query)
        by_account = [
            {
                "account_name": row.account_name,
                "total_amount": Decimal(str(row.total_amount)) if row.total_amount is not None else Decimal("0"),
            }
            for row in account_result.all()
        ]

        # By tag
        tag_query = (
            select(
                AllocatedCostRecord.tag_value,
                func.sum(AllocatedCostRecord.amount_usd).label("total_amount"),
            )
            .where(*base_filter)
            .group_by(AllocatedCostRecord.tag_value)
            .order_by(func.sum(AllocatedCostRecord.amount_usd).desc())
        )
        tag_result = await self.db.execute(tag_query)
        by_tag = [
            {
                "tag_value": row.tag_value,
                "total_amount": Decimal(str(row.total_amount)) if row.total_amount is not None else Decimal("0"),
            }
            for row in tag_result.all()
        ]

        return {
            "by_department": by_department,
            "by_account": by_account,
            "by_tag": by_tag,
        }

    async def get_business_summary(
        self,
        months: list[tuple[int, int]],  # [(year, month), ...]
        account_name: str | None = None,
    ) -> list[dict]:
        """
        按业务模块（tag_value + department）汇总多个月的费用。
        返回 [{tag_value, department, account_name, month_costs: {YYYY-MM: amount}}, ...]
        """
        from sqlalchemy import text
        from datetime import date as date_type
        import calendar

        results: dict[tuple, dict] = {}  # key: (account_name, tag_value, department)

        for year, month in months:
            last_day = calendar.monthrange(year, month)[1]
            start = date_type(year, month, 1)
            end = date_type(year, month, last_day)
            ym = f"{year}-{month:02d}"

            query = (
                select(
                    AllocatedCostRecord.account_name,
                    AllocatedCostRecord.tag_value,
                    AllocatedCostRecord.department,
                    func.sum(AllocatedCostRecord.amount_usd).label("amount_usd"),
                )
                .where(
                    AllocatedCostRecord.date >= start,
                    AllocatedCostRecord.date <= end,
                )
            )
            if account_name:
                query = query.where(AllocatedCostRecord.account_name == account_name)

            query = query.group_by(
                AllocatedCostRecord.account_name,
                AllocatedCostRecord.tag_value,
                AllocatedCostRecord.department,
            )

            result = await self.db.execute(query)
            for row in result.all():
                key = (row.account_name, row.tag_value, row.department)
                if key not in results:
                    results[key] = {
                        "account_name": row.account_name,
                        "tag_value": row.tag_value,
                        "department": row.department,
                        "month_costs": {},
                    }
                results[key]["month_costs"][ym] = Decimal(str(row.amount_usd)) if row.amount_usd else Decimal("0")

        return list(results.values())

    async def get_public_raw_summary(
        self,
        months: list[tuple[int, int]],
        account_name: str | None = None,
    ) -> list[dict]:
        """
        按 Service 汇总多个月的 Public 费用（无 Product Tag 的资源）。
        返回 [{service, account_name, month_costs: {YYYY-MM: amount}}, ...]
        """
        from backend.app.models.models import RawCostRecord
        from datetime import date as date_type
        import calendar

        results: dict[tuple, dict] = {}

        for year, month in months:
            last_day = calendar.monthrange(year, month)[1]
            start = date_type(year, month, 1)
            end = date_type(year, month, last_day)
            ym = f"{year}-{month:02d}"

            query = (
                select(
                    RawCostRecord.account_name,
                    RawCostRecord.service,
                    func.sum(RawCostRecord.amount_usd).label("amount_usd"),
                )
                .where(
                    RawCostRecord.date >= start,
                    RawCostRecord.date <= end,
                    (RawCostRecord.tag_value == None) | (RawCostRecord.tag_value == ""),
                )
            )
            if account_name:
                query = query.where(RawCostRecord.account_name == account_name)

            query = query.group_by(
                RawCostRecord.account_name,
                RawCostRecord.service,
            )

            result = await self.db.execute(query)
            for row in result.all():
                key = (row.account_name, row.service)
                if key not in results:
                    results[key] = {
                        "account_name": row.account_name,
                        "service": row.service or "Unknown",
                        "month_costs": {},
                    }
                results[key]["month_costs"][ym] = Decimal(str(row.amount_usd)) if row.amount_usd else Decimal("0")

        return list(results.values())
