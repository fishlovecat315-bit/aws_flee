import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')
async def run():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE allocated_cost_records SET rule_id = NULL"))
        r = await db.execute(text("DELETE FROM allocation_rules"))
        await db.commit()
        print(f"Deleted {r.rowcount} rules")
asyncio.run(run())
