import asyncio, sys, logging, re
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/workspace')

def normalize(tag):
    if not tag: return None
    return re.sub(r'[^a-z0-9]', '', tag.lower()) or None

# 你列表里未确认归属的 tag，标准化后的值
UNCONFIRMED_NORM = {normalize(t) for t in [
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
]}

CONFIRMED_NORM = {normalize(t) for t in [
    "DataCollection","BI","NAC","NewsReporter","Nacos","Feedback",
    "nothing x","xservice","NothingOTA","TTS","Mimi","LinkJumping",
    "Nothing Community","essential-space","Watch1","NothingWeatherServer",
    "Wallpaper","BetaOTA","SharedWidget","CommunityWidget","PushService",
    "APPClassification","ShortLink","Nothing-Preorder","Questionnaire",
    "BlindTest","IMEI","GenWidgets",
]}

ALL_KNOWN_NORM = CONFIRMED_NORM | UNCONFIRMED_NORM

async def check():
    from backend.app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        r = await db.execute(text(
            "SELECT tag_value, ROUND(SUM(amount_usd)::numeric, 2) as total "
            "FROM raw_cost_records WHERE account_name = '主业务' "
            "AND date >= '2026-02-01' AND date <= '2026-02-28' "
            "AND tag_value IS NOT NULL "
            "GROUP BY tag_value ORDER BY total DESC"
        ))
        rows = r.fetchall()

        print("=== 数据库中的 tag 及其标准化结果 ===")
        print(f"{'原始 tag':<50} {'标准化':<30} {'金额':>10}  {'状态'}")
        print("-" * 110)
        for tag, total in rows:
            norm = normalize(tag)
            if norm in CONFIRMED_NORM:
                status = "✓ 已确认"
            elif norm in UNCONFIRMED_NORM:
                status = "? 未确认"
            else:
                status = "✗ 不在列表"
            if float(total) > 0.5:  # 只显示有意义的金额
                print(f"  {tag:<50} {str(norm):<30} ${float(total):>10.2f}  {status}")

asyncio.run(check())
