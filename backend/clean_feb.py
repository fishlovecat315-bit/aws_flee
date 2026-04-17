import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def run():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r1 = await db.execute(text(
            "DELETE FROM allocated_cost_records WHERE account_name = '主业务' AND date >= '2026-02-01' AND date <= '2026-02-28'"
        ))
        r2 = await db.execute(text(
            "DELETE FROM raw_cost_records WHERE account_name = '主业务' AND date >= '2026-02-01' AND date <= '2026-02-28'"
        ))
        await db.commit()
        print(f"Deleted allocated: {r1.rowcount}, raw: {r2.rowcount}")

asyncio.run(run())
