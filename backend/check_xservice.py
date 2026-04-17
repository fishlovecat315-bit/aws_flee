import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        # 查所有包含 xservice 的 tag（不区分大小写）
        r = await db.execute(text(
            "SELECT tag_value, service, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "AND LOWER(tag_value) LIKE '%xservice%' "
            "GROUP BY tag_value, service ORDER BY total DESC"
        ))
        rows = r.fetchall()
        grand = 0
        print("3月 xservice 相关记录:")
        for row in rows:
            print(f"  tag={row[0]!r:<50} service={row[1]:<40} ${row[2]}")
            grand += float(row[2])
        print(f"\n  合计: ${grand:.2f}")

        # 对比：不用 LIKE，精确查 tag_value = 'xservice'
        r2 = await db.execute(text(
            "SELECT ROUND(SUM(amount_usd)::numeric, 2) "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "AND tag_value = 'xservice'"
        ))
        print(f"\n  精确匹配 'xservice': ${r2.scalar()}")

        # 查所有 3 月的不同 tag 数量
        r3 = await db.execute(text(
            "SELECT COUNT(DISTINCT tag_value) FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        print(f"  3月不同 tag 数量: {r3.scalar()}")

asyncio.run(check())
