import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:

        # 查这些具体 tag 的 service 和费用
        tags = [
            'watch-prod-app-node1', 'watch-prod-midware-node1', 'watch-pre-app-node1',
            '开源网安iast', '漏洞学习平台', '安全iast',
            'paris-eks-nat-public1-eu-west-3a', 'mumbai-eks-nat-public1-ap-south-1a',
            'NewBIServer', 'PowerBIGateway', 'PowerBIDesktop', 'PowerBItest1',
        ]
        for tag in tags:
            r = await db.execute(text(
                "SELECT service, ROUND(SUM(amount_usd)::numeric, 2) as total "
                "FROM raw_cost_records WHERE account_name = '主业务' "
                "AND date >= '2026-02-01' AND date <= '2026-02-28' "
                "AND tag_value = :tag GROUP BY service ORDER BY total DESC"
            ), {"tag": tag})
            rows = r.fetchall()
            if rows:
                total = sum(float(r[1]) for r in rows)
                print(f"\n[{tag}] 总计 ${total:.2f}")
                for row in rows:
                    print(f"  service: {row[0]:<55} ${row[1]}")

asyncio.run(check())
