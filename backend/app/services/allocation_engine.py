"""
AllocationEngine: 按照预定义规则将 raw_cost_records 分摊到各业务部门。

主业务账号分摊规则（来自截图）：
  SmartProduct（100% Smart）: nothing x, xservice, NothingOTA, TTS, Mimi, LinkJumping
  Common（按比例）:
    DataCollection → Phone:Smart:销售 = 70:20:10
    BI             → Phone:Smart:销售 = 40:30:30
    NAC            → Smart:Community:销售 = 33.3:33.3:33.3
    NewsReporter   → Phone:Smart = 50:50
    Nacos          → AI:Smart:Phone = 33.3:50:16.6
    Feedback       → Phone:Smart = 50:50
  Community（100% Community）: Nothing Community
  AI（100% AI）: essential-space
  Phone（100% Phone）: Watch1, NothingWeatherServer*, Wallpaper, BetaOTA, SharedWidget,
                       CommunityWidget, PushService, APPClassification, ShortLink,
                       Nothing-Preorder, Questionnaire, BlindTest, IMEI, GenWidgets
    * NothingWeatherServer 实际按 Phone:Smart = 9:1 分摊
  Public（无 Tag，按 service 类型分摊）:
    EFS                → Nacos 规则（AI:Smart:Phone = 33.3:50:16.6）
    ECS/EKS            → Smart:Phone:AI = 1:2:1
    TTS/语音转文字 service → 100% Smart
    Athena & Glue      → BI 规则（Phone:Smart:销售 = 40:30:30）
    ELB                → 100% Smart（Nothing-X）
    MongoDB/Marketplace → 基础$2500 由 AI:Smart:Phone 三者均摊，超出部分 100% Smart
    Redshift           → DataCollection 规则（Phone:Smart:销售 = 70:20:10）
    其余无 Tag          → Public 分摊（Phone:SmartProduct:IT:Community 按实际比例）
"""
import logging
import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import AllocatedCostRecord, AllocationRule, RawCostRecord

logger = logging.getLogger(__name__)

def _normalize(tag: str | None) -> str | None:
    """标准化 tag：去掉所有非字母数字字符，转小写。"""
    if not tag:
        return None
    return re.sub(r'[^a-z0-9]', '', tag.lower()) or None


def _match_appname(tag: str | None) -> str | None:
    """
    对原始 Product tag value 做包含匹配（不区分大小写，忽略符号和空格）。
    先将 tag 标准化（去掉非字母数字字符转小写），再按关键词长度降序匹配。
    """
    if not tag:
        return None
    tag_norm = re.sub(r'[^a-z0-9]', '', tag.lower())
    for kw in _SORTED_KEYWORDS:
        if kw in tag_norm:
            return kw
    return None


# ---------------------------------------------------------------------------
# 主业务账号分摊规则（标准化后的 appname → 规则）
# ---------------------------------------------------------------------------

# SmartProduct 直接归属（100% Smart）— 标准化后的 appname
MAIN_SMART_DIRECT = {
    "nothingx", "xservice", "nothingota", "tts", "mimi", "linkjumping",
    # 变体
    "ttsproxy",  # TTSProxy:* → TTS → Smart
}

# Community 直接归属（100% Community）
MAIN_COMMUNITY_DIRECT = {"nothingcommunity"}

# AI 直接归属（100% AI）
MAIN_AI_DIRECT = {"essentialspace"}

# Phone 直接归属（100% Phone，除 NothingWeatherServer 外）
MAIN_PHONE_DIRECT = {
    "watch1", "wallpaper",
    "betaota", "sharedwidget", "communitywidget",
    "pushservice", "appclassification", "shortlink", "nothingpreorder",
    "questionnaire", "blindtest", "imei", "genwidgets",
    "sharewidget",
}

# NothingWeatherServer → Phone:Smart = 9:1
WEATHER_TAGS = {"nothingweatherserver", "weather"}

# Common 共用资源分摊比例（标准化 appname → {dept: ratio}）
MAIN_SHARED: dict[str, dict[str, Decimal]] = {
    "datacollection": {"Phone": Decimal("70"), "Smart": Decimal("20"), "销售": Decimal("10")},
    "bi":             {"Phone": Decimal("40"), "Smart": Decimal("30"), "销售": Decimal("30")},
    "nac":            {"Smart": Decimal("1"),  "Community": Decimal("1"), "销售": Decimal("1")},
    "newsreporter":   {"Phone": Decimal("1"),  "Smart": Decimal("1")},
    "nacos":          {"AI": Decimal("1"),     "Smart": Decimal("3"),  "Phone": Decimal("1")},
    "feedback":       {"Phone": Decimal("1"),  "Smart": Decimal("1")},
    # 变体
    "logkitfeedback": {"Phone": Decimal("1"),  "Smart": Decimal("1")},  # LogkitFeedback → Feedback
    "common":         {"Smart": Decimal("1"),  "Phone": Decimal("2"), "AI": Decimal("1")},  # Common → EKS 规则
    "commoncache":    {"AI": Decimal("1"),     "Smart": Decimal("3"),  "Phone": Decimal("1")},  # Common Cache → Nacos
    "commonrds":      {"Phone": Decimal("70"), "Smart": Decimal("20"), "销售": Decimal("10")},  # Common RDS → DataCollection
}

# ECS/EKS 分摊：nothing-x(Smart) + share-widget(Phone) + 生成式widget(Phone) + essential-space(AI)
# → Smart:Phone:AI = 1:2:1
EKS_ECS_RATIOS: dict[str, Decimal] = {
    "Smart": Decimal("1"), "Phone": Decimal("2"), "AI": Decimal("1"),
}

# EFS 归属 Nacos 业务，按 Nacos 规则分摊
EFS_RATIOS = MAIN_SHARED["nacos"]

# MongoDB 基础费用阈值（$2500 由 AI:Smart:Phone 三者均摊）
MONGODB_BASE = Decimal("2500.00")
MONGODB_BASE_RATIOS: dict[str, Decimal] = {
    "AI": Decimal("1"), "Smart": Decimal("1"), "Phone": Decimal("1"),
}

# Public 兜底分摊（其余无 Tag 资源，按 Software 实际使用量均摊）
# Phone:SmartProduct:IT:Community，截图里 2 月比例约 4202:8248:10909:90
# 这里用固定比例，后续可通过 DB 规则覆盖
PUBLIC_FALLBACK_RATIOS: dict[str, Decimal] = {
    "Phone": Decimal("1"), "Smart": Decimal("2"), "IT": Decimal("2.6"), "Community": Decimal("0.02"),
}

# 所有已知的标准化关键词（用于包含匹配）
_ALL_KNOWN_KEYS: set[str] = (
    MAIN_SMART_DIRECT | MAIN_COMMUNITY_DIRECT | MAIN_AI_DIRECT |
    MAIN_PHONE_DIRECT | WEATHER_TAGS | set(MAIN_SHARED.keys())
)
# 按长度降序排列，确保长词优先匹配（避免 "bi" 误匹配 "bi20" 等）
_SORTED_KEYWORDS: list[str] = sorted(_ALL_KNOWN_KEYS, key=len, reverse=True)

# ---------------------------------------------------------------------------
# PLM 账号分摊规则
# ---------------------------------------------------------------------------
PLM_DIRECT: dict[str, str] = {
    "OBA-app": "IT", "CommonRedshift": "IT", "ems-app-database": "IT",
    "IPGuard": "IT", "powerbi rds": "IT",
    "LogCollect": "Phone", "DIS": "Phone", "CIT": "销售",
}
PLM_PUBLIC_RATIOS: dict[str, Decimal] = {"Phone": Decimal("2"), "IT": Decimal("1")}

# ---------------------------------------------------------------------------
# 国内账号分摊规则
# ---------------------------------------------------------------------------
CN_DIRECT: dict[str, str] = {
    "NothingX": "Smart", "Mini": "Smart", "DataCollection": "Smart",
    "OTA": "Smart", "feedback": "Smart", "NAC": "Smart",
    "Common Cache": "Smart", "LogCollect": "Smart", "Nacos": "Smart",
}


class AllocationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._db_rules: dict[tuple[str, Optional[str]], AllocationRule] = {}

    async def run(self, target_date: date) -> None:
        await self.allocate_date_range(target_date, target_date)

    async def allocate_date_range(self, start_date: date, end_date: date) -> None:
        await self._load_db_rules()
        current = start_date
        while current <= end_date:
            await self._allocate_single_date(current)
            current += timedelta(days=1)
        try:
            from backend.app.services.alert_service import AlertService  # noqa: PLC0415
            await AlertService(self.db).check_and_alert()
        except Exception as exc:  # noqa: BLE001
            logger.error("AlertService failed: %s", exc)

    async def _load_db_rules(self) -> None:
        result = await self.db.execute(
            select(AllocationRule).where(AllocationRule.is_active == True)  # noqa: E712
        )
        self._db_rules = {(r.account_name, r.tag_value): r for r in result.scalars().all()}

    async def _allocate_single_date(self, target_date: date) -> None:
        await self.db.execute(
            delete(AllocatedCostRecord).where(AllocatedCostRecord.date == target_date)
        )
        result = await self.db.execute(
            select(RawCostRecord).where(RawCostRecord.date == target_date)
        )
        raw_records = result.scalars().all()

        new_records: list[AllocatedCostRecord] = []
        for raw in raw_records:
            for dept, amt, biz_module, rule_id in self._apply_rule(raw):
                new_records.append(AllocatedCostRecord(
                    date=target_date,
                    account_name=raw.account_name,
                    tag_value=raw.tag_value,
                    business_module=biz_module,
                    department=dept,
                    amount_usd=amt,
                    rule_id=rule_id,
                    calculated_at=datetime.now(tz=timezone.utc),
                ))

        if new_records:
            self.db.add_all(new_records)
        await self.db.commit()
        logger.info("Allocated %d splits for %s (from %d raw)", len(new_records), target_date, len(raw_records))

    def _apply_rule(self, raw: RawCostRecord) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        account = raw.account_name
        tag = raw.tag_value
        service = raw.service
        amount = Decimal(str(raw.amount_usd))

        # DB 规则优先
        db_rule = self._db_rules.get((account, tag))
        if db_rule:
            return self._apply_db_rule(db_rule, amount)

        if account == "PLM":
            return self._alloc_plm(tag, service, amount)
        if account == "主业务":
            return self._alloc_main(tag, service, amount)
        if account == "国内":
            return self._alloc_cn(tag, service, amount)
        return [("未分类", amount, tag, None)]

    def _apply_db_rule(self, rule: AllocationRule, amount: Decimal) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        if rule.rule_type == "direct":
            return [(rule.department, amount, rule.business_module, rule.id)]
        if rule.rule_type in ("shared", "public") and rule.ratios:
            ratios = {k: Decimal(str(v)) for k, v in rule.ratios.items()}
            return [(d, a, rule.business_module, rule.id) for d, a in self._split(amount, ratios)]
        return [("未分类", amount, rule.business_module, rule.id)]

    # ------------------------------------------------------------------
    # PLM
    # ------------------------------------------------------------------
    def _alloc_plm(self, tag: Optional[str], service: str, amount: Decimal) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        if tag:
            tag_norm = re.sub(r'[^a-z0-9]', '', tag.lower())
            for k, v in PLM_DIRECT.items():
                if k.lower() in tag_norm:
                    return [(v, amount, tag, None)]
        return [(d, a, tag, None) for d, a in self._split(amount, PLM_PUBLIC_RATIOS)]

    # ------------------------------------------------------------------
    # 主业务
    # ------------------------------------------------------------------
    def _alloc_main(self, tag: Optional[str], service: str, amount: Decimal) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        matched = _match_appname(tag)  # 对原始 tag value 做包含匹配

        # 1. SmartProduct 直接归属
        if matched and matched in MAIN_SMART_DIRECT:
            return [("Smart", amount, tag, None)]

        # 2. Community 直接归属
        if matched and matched in MAIN_COMMUNITY_DIRECT:
            return [("Community", amount, tag, None)]

        # 3. AI 直接归属
        if matched and matched in MAIN_AI_DIRECT:
            return [("AI", amount, tag, None)]

        # 4. NothingWeatherServer → Phone:Smart = 9:1
        if matched and matched in WEATHER_TAGS:
            return [(d, a, tag, None) for d, a in self._split(amount, {"Phone": Decimal("9"), "Smart": Decimal("1")})]

        # 5. Phone 直接归属
        if matched and matched in MAIN_PHONE_DIRECT:
            return [("Phone", amount, tag, None)]

        # 6. Common 共用资源（按标准化 appname 匹配）
        if matched and matched in MAIN_SHARED:
            return [(d, a, tag, None) for d, a in self._split(amount, MAIN_SHARED[matched])]

        # 7. EKS/ECS 相关 tag（包含 eks 或 ecs）
        tag_norm = re.sub(r'[^a-z0-9]', '', tag.lower()) if tag else ""
        if tag_norm and ("eks" in tag_norm or "ecs" in tag_norm):
            return [(d, a, tag, None) for d, a in self._split(amount, EKS_ECS_RATIOS)]

        # 8. 无 Tag 或未匹配
        if not tag:
            # 无 Tag → Public 规则（按 service 类型）
            return self._alloc_main_public(tag, service, amount)
        else:
            # 有 Tag 但未匹配到已知业务 → 归属于"其他"
            return [("其他", amount, tag, None)]

    def _alloc_main_public(self, tag: Optional[str], service: str, amount: Decimal) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        """无 Tag 或未匹配的资源 → Public 兜底分摊。"""
        service_lower = service.lower() if service else ""

        # 1. EFS → Nacos
        if "elasticfilesystem" in service_lower or "efs" in service_lower:
            return [(d, a, tag, None) for d, a in self._split(amount, MAIN_SHARED.get("nacos", {}))]
            
        # 2. ECS/EKS
        if "elasticcontainerservice" in service_lower or "ecs" in service_lower or "eks" in service_lower or "kubernetes" in service_lower:
            return [(d, a, tag, None) for d, a in self._split(amount, EKS_ECS_RATIOS)]
            
        # 3. TTS
        if "polly" in service_lower or "tts" in service_lower:
            return [("Smart", amount, tag, None)]
            
        # 4. Athena & Glue
        if "athena" in service_lower or "glue" in service_lower:
            return [(d, a, tag, None) for d, a in self._split(amount, MAIN_SHARED.get("bi", {}))]
            
        # 5. ELB
        if "elasticloadbalancing" in service_lower or "elb" in service_lower:
            return [("Smart", amount, tag, None)]
            
        # 6. MongoDB / Marketplace
        if "mongodb" in service_lower or "marketplace" in service_lower:
            return [(d, a, tag, None) for d, a in self._alloc_mongodb(amount)]
            
        # 7. Redshift
        if "redshift" in service_lower:
            return [(d, a, tag, None) for d, a in self._split(amount, MAIN_SHARED.get("datacollection", {}))]

        # 8. 其余无 Tag
        return [(d, a, tag, None) for d, a in self._split(amount, PUBLIC_FALLBACK_RATIOS)]

    def _alloc_mongodb(self, total: Decimal) -> list[tuple[str, Decimal]]:
        """基础 $2500 由 Nothing-x(Smart) 和 SharedWidget(Phone) 各 50% 均摊，超出部分 100% Smart。"""
        base_ratios: dict[str, Decimal] = {"Smart": Decimal("1"), "Phone": Decimal("1")}
        if total <= MONGODB_BASE:
            return self._split(total, base_ratios)
        base_splits = self._split(MONGODB_BASE, base_ratios)
        excess = total - MONGODB_BASE
        return [(dept, amt + excess if dept == "Smart" else amt) for dept, amt in base_splits]

    # ------------------------------------------------------------------
    # 国内
    # ------------------------------------------------------------------
    def _alloc_cn(self, tag: Optional[str], service: str, amount: Decimal) -> list[tuple[str, Decimal, Optional[str], Optional[int]]]:
        if tag:
            tag_norm = re.sub(r'[^a-z0-9]', '', tag.lower())
            for k in CN_DIRECT:
                if k.lower() in tag_norm:
                    return [("Smart", amount, tag, None)]
        return [("其他", amount, tag, None)]

    # ------------------------------------------------------------------
    # 比例分摊工具
    # ------------------------------------------------------------------
    def _split(self, amount: Decimal, ratios: dict[str, Decimal]) -> list[tuple[str, Decimal]]:
        if not ratios:
            return [("未分类", amount)]
        total_ratio = sum(ratios.values())
        precision = Decimal("0.0001")
        splits = []
        allocated = Decimal("0")
        for dept, ratio in ratios.items():
            share = (amount * ratio / total_ratio).quantize(precision, rounding=ROUND_HALF_UP)
            splits.append((dept, share))
            allocated += share
        remainder = amount - allocated
        if remainder:
            max_idx = max(range(len(splits)), key=lambda i: splits[i][1])
            dept, share = splits[max_idx]
            splits[max_idx] = (dept, share + remainder)
        return splits
