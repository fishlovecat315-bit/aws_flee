import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def run():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        # 查所有 tag 里包含 xservice 的（去掉符号后匹配）
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

        # 也查 xservice0, xservicetest 等变体
        r2 = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-03-01' AND date <= '2026-03-31' "
            "AND (LOWER(tag_value) LIKE 'xservice%' OR LOWER(tag_value) LIKE '%:xservice%') "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        grand2 = 0
        print("\n3月 xservice 开头或包含 :xservice 的 tag:")
        for row in r2.fetchall():
            print(f"  {row[0]!r:<55} ${row[1]}")
            grand2 += float(row[1])
        print(f"  合计: ${grand2:.2f}")

        # 查 3 月总费用
        r3 = await db.execute(text(
            "SELECT ROUND(SUM(amount_usd)::numeric, 2) FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-03-01' AND date <= '2026-03-31'"
        ))
        print(f"\n3月主业务总费用: ${r3.scalar()}")

asyncio.run(run())
