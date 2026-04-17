import asyncio, sys
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT COUNT(*) as records, SUM(amount_usd) as total, MIN(date) as min_date, MAX(date) as max_date "
            "FROM raw_cost_records WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        row = r.fetchone()
        print(f"Records: {row[0]}, Total: {row[1]}, Date range: {row[2]} ~ {row[3]}")

        r2 = await db.execute(text(
            "SELECT date, SUM(amount_usd) as daily_total FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "GROUP BY date ORDER BY date"
        ))
        rows = r2.fetchall()
        print(f"Days with data: {len(rows)}")
        for row in rows:
            print(f"  {row[0]}: ${row[1]:.2f}")

        # 检查是否有其他账号名称
        r3 = await db.execute(text(
            "SELECT DISTINCT account_name, account_id FROM raw_cost_records"
        ))
        print("\nAll accounts in DB:")
        for row in r3.fetchall():
            print(f"  account_name={row[0]}, account_id={row[1]}")

asyncio.run(check())
