import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def run():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "AND LOWER(tag_value) LIKE '%xservice%' "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        grand = 0
        print("3月所有包含 xservice 的 tag:")
        for row in r.fetchall():
            print(f"  {row[0]!r:<55} ${row[1]}")
            grand += float(row[1])
        print(f"  合计: ${grand:.2f}")
        print(f"  AWS后台: $3,401.54")
        print(f"  差额: ${3401.54 - grand:.2f}")

        # 查 3 月总记录数和总费用
        r2 = await db.execute(text(
            "SELECT COUNT(*), ROUND(SUM(amount_usd)::numeric, 2) "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        row = r2.fetchone()
        print(f"\n3月总记录: {row[0]}, 总费用: ${row[1]}")

        # 查 3 月有多少天数据
        r3 = await db.execute(text(
            "SELECT COUNT(DISTINCT date) FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        print(f"3月数据天数: {r3.scalar()}")

asyncio.run(run())
