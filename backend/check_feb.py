import asyncio, sys
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        # 2月总费用
        r = await db.execute(text(
            "SELECT COUNT(*) as records, ROUND(SUM(amount_usd)::numeric, 2) as total, "
            "MIN(date) as min_date, MAX(date) as max_date "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28'"
        ))
        row = r.fetchone()
        print(f"2月 Records: {row[0]}, Total: ${row[1]}, Date range: {row[2]} ~ {row[3]}")

        if row[0] == 0:
            print("没有2月数据，请先触发补拉")
            return

        # 按 tag_value 汇总（业务维度）
        r2 = await db.execute(text(
            "SELECT COALESCE(tag_value, '(无Tag)') as tag, "
            "ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "GROUP BY tag_value ORDER BY total DESC LIMIT 40"
        ))
        print("\n按 tag_value 汇总（Top 40）:")
        for row in r2.fetchall():
            print(f"  {str(row[0]):<55} ${row[1]}")

        # 按 service 汇总
        r3 = await db.execute(text(
            "SELECT service, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "GROUP BY service ORDER BY total DESC LIMIT 20"
        ))
        print("\n按 service 汇总（Top 20）:")
        for row in r3.fetchall():
            print(f"  {str(row[0]):<60} ${row[1]}")

        # 无Tag的费用总计
        r4 = await db.execute(text(
            "SELECT ROUND(SUM(amount_usd)::numeric, 2) "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND tag_value IS NULL"
        ))
        print(f"\n无Tag费用总计: ${r4.scalar()}")

asyncio.run(check())
