import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT service, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND tag_value IS NULL "
            "GROUP BY service ORDER BY total DESC"
        ))
        rows = r.fetchall()
        grand = 0
        print("无Tag费用按service分布:")
        for row in rows:
            print(f"  {str(row[0]):<65} ${row[1]}")
            grand += float(row[1])
        print(f"\n  合计: ${grand:.2f}")

asyncio.run(check())
