import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

# 你提供的已知 tag 列表
KNOWN_CONFIRMED = {
    "DataCollection","BI","NAC","NewsReporter","Nacos","Feedback",
    "nothing x","xservice","NothingOTA","TTS","Mimi","LinkJumping",
    "Nothing Community","essential-space","Watch1","NothingWeatherServer",
    "Wallpaper","BetaOTA","SharedWidget","CommunityWidget","PushService",
    "APPClassification","ShortLink","Nothing-Preorder","Questionnaire",
    "BlindTest","IMEI","GenWidgets",
}

KNOWN_UNCONFIRMED = {
    "AnonymousChat","BackendServerUse","Basic Service","Common",
    "Common Cache:Cache:ap-northeast-1","Common Cache:Cache:eu-central-1",
    "Common:CDN:ap-northeast-1","Common:CDN:ap-south-1","Common:RDS:eu-west-3",
    "DiagnosticTool","DianosticTool","Dinosaur:EC2:ap-northeast-1",
    "DinosaurTranslationTool","EKS","EKS:EC2:eu-west-3",
    "EKSCluster:EKS:ap-south-1","EKSCommon:EC2:ap-south-1","EKSCommon:EC2:eu-west-3",
    "GA4 Event Sync","IAST:EC2:sa-east-1","India Student Community",
    "JIRA:S3:ap-east-1","LogkitFeedback","Loki:CDN:ap-northeast-1",
    "Loki:CDN:ap-south-1","LutFilter:CF:Global","LutFilter:S3:ap-south-1",
    "NFTWidget","Nothing Account Center",
    "Nothing Account Center/Nothing Community/Nothing IoT",
    "Nothing Dock","Nothing IoT OTA System","Nothing OBA System",
    "Nothing Phone","Nothing Store","Nothing Student Program",
    "Nothing Wallet","NothingCareers","NothingPhone",
    "NothingPhoneConnectStatus:Lambda:ap-east-1",
    "OSTips:CDN:ap-east-1","OSTips:S3:ap-east-1","Other:EC2:eu-west-3",
    "Privacy","Provision:S3:us-west-1","Push:CDN:ap-northeast-1",
    "QR code link:S3:us-west-1","Qcli","SecurityTest:EC2:eu-west-3",
    "ShareWidget:CDN:ap-northeast-1","TTSProxy:EC2:ap-northeast-1",
    "TTSProxy:CDN:ap-south-1","TTSProxy:EC2:ap-south-1","TTSProxy:EC2:eu-west-3",
    "TTSProxy:ELB:ap-northeast-1","TTSProxy:ELB:ap-south-1","TTSProxy:ELB:eu-west-3",
    "Weather:CDN:Global","campaign","common:rds:us-east-1",
    "essential-voice:ELB:ap-northeast-1","essential-voice:ELB:ap-south-1",
    "essential-voice:ELB:eu-west-3","games:CDN:global","games:s3:ap-southeast-1",
    "support:CDN:global","support:EC2:ap-northeast-1","support:s3:eu-west-3",
    "tips:EC2:ap-northeast-1","tips:alb:eu-west-3","tips:ec2:eu-west-3",
    "tips:lb:ap-northeast-1",
}

ALL_KNOWN = KNOWN_CONFIRMED | KNOWN_UNCONFIRMED

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT DISTINCT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND tag_value IS NOT NULL "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        db_tags = {row[0]: float(row[1]) for row in r.fetchall()}

        print(f"数据库中共有 {len(db_tags)} 个不同 tag（不含 NULL）\n")

        # 在数据库中但不在你的列表里的 tag（意外的 tag）
        unexpected = {t: v for t, v in db_tags.items() if t not in ALL_KNOWN}
        print(f"=== 数据库中存在但你列表里没有的 tag（{len(unexpected)} 个）===")
        for t, v in sorted(unexpected.items(), key=lambda x: -x[1]):
            print(f"  ${v:>10.2f}  {t}")

        # 你列表里有但数据库中不存在的 tag
        missing = ALL_KNOWN - set(db_tags.keys())
        print(f"\n=== 你列表里有但数据库中不存在的 tag（{len(missing)} 个）===")
        for t in sorted(missing):
            print(f"  {t}")

        # 确认归属的 tag 在数据库中的费用
        print(f"\n=== 确认归属 tag 的费用汇总 ===")
        total_confirmed = 0
        for t in sorted(KNOWN_CONFIRMED):
            v = db_tags.get(t, 0)
            if v > 0:
                print(f"  ${v:>10.2f}  {t}")
                total_confirmed += v
        print(f"  确认归属合计: ${total_confirmed:.2f}")

        # 未确认归属的 tag 在数据库中的费用
        print(f"\n=== 未确认归属 tag 的费用汇总 ===")
        total_unconfirmed = 0
        for t in sorted(KNOWN_UNCONFIRMED):
            v = db_tags.get(t, 0)
            if v > 0:
                print(f"  ${v:>10.2f}  {t}")
                total_unconfirmed += v
        print(f"  未确认归属合计: ${total_unconfirmed:.2f}")

        total_null = await db.execute(text(
            "SELECT ROUND(SUM(amount_usd)::numeric, 2) FROM raw_cost_records "
            "WHERE account_name = '主业务' AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND tag_value IS NULL"
        ))
        print(f"\n无 Tag (NULL) 费用: ${total_null.scalar()}")

asyncio.run(check())
