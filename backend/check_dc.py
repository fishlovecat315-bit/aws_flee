import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        # 查 DataCollection 相关的所有 tag（模糊匹配）
        r = await db.execute(text(
            "SELECT tag_value, service, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND (LOWER(tag_value) LIKE '%datacollection%' OR LOWER(tag_value) LIKE '%data_collection%') "
            "GROUP BY tag_value, service ORDER BY total DESC"
        ))
        print("DataCollection 相关 tag:")
        for row in r.fetchall():
            print(f"  tag={row[0]!r:<50} service={row[1]:<40} ${row[2]}")

        # 查 nothing x 相关
        r2 = await db.execute(text(
            "SELECT tag_value, service, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND (LOWER(tag_value) LIKE '%nothing%x%' OR LOWER(tag_value) LIKE '%nothingx%') "
            "GROUP BY tag_value, service ORDER BY total DESC LIMIT 10"
        ))
        print("\nNothing-x 相关 tag:")
        for row in r2.fetchall():
            print(f"  tag={row[0]!r:<50} service={row[1]:<40} ${row[2]}")

        # 查 Athena 的 tag 分布（Athena 应该是 BI 业务）
        r3 = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND service = 'Amazon Athena' "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        print("\nAthena 的 tag 分布:")
        for row in r3.fetchall():
            print(f"  tag={str(row[0])!r:<50} ${row[1]}")

        # 查 S3 的 tag 分布（S3 $13,468 无 tag）
        r4 = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND service = 'Amazon Simple Storage Service' "
            "GROUP BY tag_value ORDER BY total DESC LIMIT 20"
        ))
        print("\nS3 的 tag 分布 (Top 20):")
        for row in r4.fetchall():
            print(f"  tag={str(row[0])!r:<50} ${row[1]}")

        # 查 RDS 的 tag 分布
        r5 = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND service = 'Amazon Relational Database Service' "
            "GROUP BY tag_value ORDER BY total DESC LIMIT 20"
        ))
        print("\nRDS 的 tag 分布 (Top 20):")
        for row in r5.fetchall():
            print(f"  tag={str(row[0])!r:<50} ${row[1]}")

asyncio.run(check())
