import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def run():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT date, COUNT(*) as cnt, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "GROUP BY date ORDER BY date"
        ))
        for row in r.fetchall():
            print(f"  {row[0]}  records={row[1]:>4}  ${row[2]}")

asyncio.run(run())
