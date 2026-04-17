import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def run():
    from backend.app.core.database import AsyncSessionLocal
    from backend.app.services.cost_sync import CostSyncService
    from sqlalchemy import text
    from datetime import date

    async with AsyncSessionLocal() as db:
        # 清空3月主业务数据
        await db.execute(text(
            "DELETE FROM allocated_cost_records WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        r = await db.execute(text(
            "DELETE FROM raw_cost_records WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        await db.commit()
        print(f"Deleted {r.rowcount} raw records for March")

    # 重新拉取
    async with AsyncSessionLocal() as db:
        svc = CostSyncService(db)
        log = await svc.sync_all(start_date=date(2026,3,1), end_date=date(2026,3,30))
        print(f"Resync: status={log.status}, records={log.records_count}")

    # 验证 xservice
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "AND LOWER(tag_value) LIKE '%xservice%' "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        grand = 0
        print("\n3月 xservice 相关（重拉后）:")
        for row in r.fetchall():
            print(f"  {row[0]!r:<55} ${row[1]}")
            grand += float(row[1])
        print(f"  合计: ${grand:.2f}")

asyncio.run(run())
