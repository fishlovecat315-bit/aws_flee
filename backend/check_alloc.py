import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from backend.app.services.allocation_engine import AllocationEngine
    from datetime import date
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        print("重算2月分摊...")
        engine = AllocationEngine(db)
        await engine.allocate_date_range(date(2026,2,1), date(2026,2,28))
        print("完成！\n")

        # 按部门汇总
        r = await db.execute(text(
            "SELECT department, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM allocated_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "GROUP BY department ORDER BY total DESC"
        ))
        print("按部门汇总:")
        grand = 0
        for row in r.fetchall():
            print(f"  {str(row[0]):<15} ${row[1]}")
            grand += float(row[1])
        print(f"  {'合计':<15} ${grand:.2f}")

        # 按业务模块汇总（tag_value）
        r2 = await db.execute(text(
            "SELECT COALESCE(tag_value, '(无Tag/Public)') as biz, department, "
            "ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM allocated_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "GROUP BY tag_value, department ORDER BY total DESC LIMIT 40"
        ))
        print("\n按业务模块+部门汇总（Top 40）:")
        for row in r2.fetchall():
            print(f"  {str(row[0]):<50} {str(row[1]):<12} ${row[2]}")

        # 原始总费用
        r3 = await db.execute(text(
            "SELECT ROUND(SUM(amount_usd)::numeric, 2) FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-02-01' AND date <= '2026-02-28'"
        ))
        print(f"\n原始费用总计: ${r3.scalar()}")

asyncio.run(check())
