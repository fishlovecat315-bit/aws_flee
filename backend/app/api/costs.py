import hashlib
import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.redis_client import get_redis
from backend.app.repositories.cost_repository import CostRepository
from backend.app.schemas.cost import (
    DailyCostItem,
    DailyCostsResponse,
    MonthlyCostItem,
    MonthlyCostsResponse,
    SummaryResponse,
)

router = APIRouter()

CACHE_TTL = 300  # 5 minutes


def _normalize(tag: str | None) -> str | None:
    import re
    if not tag:
        return None
    return re.sub(r'[^a-z0-9]', '', tag.lower()) or None


def _match_appname(tag: str | None) -> str | None:
    """对原始 Product tag value 做包含匹配（标准化后匹配，忽略符号空格大小写），长词优先。"""
    if not tag:
        return None
    import re as _re
    tag_norm = _re.sub(r'[^a-z0-9]', '', tag.lower())
    for kw in sorted(BIZ_META.keys(), key=len, reverse=True):
        if kw and kw in tag_norm:
            return kw
    return None

# 业务元数据：标准化 appname → {group: 业务归属, name: 业务模块中文名}
# 标准化规则：去掉所有非字母数字字符，转小写
BIZ_META: dict[str, dict] = {
    # 共用
    "datacollection": {"group": "共用", "name": "埋点服务"},
    "bi":             {"group": "共用", "name": "看板"},
    "nac":            {"group": "共用", "name": "账号中心"},
    "newsreporter":   {"group": "共用", "name": "NewsReporter"},
    "nacos":          {"group": "共用", "name": "Nacos"},
    "feedback":       {"group": "共用", "name": "Feedback"},
    "logkitfeedback": {"group": "共用", "name": "Feedback"},
    # SmartProduct
    "nothingx":       {"group": "SmartProduct", "name": "Nothing-x"},
    "xservice":       {"group": "SmartProduct", "name": "xservice"},
    "nothingota":     {"group": "SmartProduct", "name": "NothingOTA"},
    "tts":            {"group": "SmartProduct", "name": "TTS"},
    "ttsproxy":       {"group": "SmartProduct", "name": "TTS"},
    "mimi":           {"group": "SmartProduct", "name": "Mimi"},
    "linkjumping":    {"group": "SmartProduct", "name": "二维码服务"},
    # Community
    "nothingcommunity": {"group": "Community", "name": "社区"},
    # AI
    "essentialspace":   {"group": "AI", "name": "essential-space"},
    # Phone
    "watch1":            {"group": "Phone", "name": "cmf watch"},
    "nothingweatherserver": {"group": "Phone", "name": "天气服务"},
    "weather":           {"group": "Phone", "name": "天气服务"},
    "wallpaper":         {"group": "Phone", "name": "AI Wallpaper"},
    "betaota":           {"group": "Phone", "name": "BetaOTA"},
    "sharedwidget":      {"group": "Phone", "name": "SharedWidget"},
    "sharewidget":       {"group": "Phone", "name": "SharedWidget"},
    "communitywidget":   {"group": "Phone", "name": "社区微件"},
    "pushservice":       {"group": "Phone", "name": "PushService"},
    "appclassification": {"group": "Phone", "name": "应用分类"},
    "shortlink":         {"group": "Phone", "name": "ShortLink"},
    "nothingpreorder":   {"group": "Phone", "name": "Nothing-Preorder"},
    "questionnaire":     {"group": "Phone", "name": "问卷"},
    "blindtest":         {"group": "Phone", "name": "Camera盲测"},
    "imei":              {"group": "Phone", "name": "IMEIServer"},
    "genwidgets":        {"group": "Phone", "name": "生成式widgets"},
}


def _cache_key(endpoint: str, params: dict) -> str:
    params_str = json.dumps(params, sort_keys=True, default=str)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()
    return f"costs:{endpoint}:{params_hash}"


@router.get("/costs/daily", response_model=DailyCostsResponse)
async def get_daily_costs(
    start_date: date = Query(...),
    end_date: date = Query(...),
    department: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    tag_value: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "department": department,
        "account_name": account_name,
        "tag_value": tag_value,
        "page": page,
        "page_size": page_size,
    }
    key = _cache_key("daily", params)

    cached = await redis.get(key)
    if cached:
        return DailyCostsResponse.model_validate_json(cached)

    repo = CostRepository(db)
    records, total = await repo.get_daily_costs(
        start_date=start_date,
        end_date=end_date,
        department=department,
        account_name=account_name,
        tag_value=tag_value,
        page=page,
        page_size=page_size,
    )

    items = [
        DailyCostItem(
            date=r.date,
            department=r.department,
            account_name=r.account_name,
            tag_value=r.tag_value,
            business_module=r.business_module,
            amount_usd=r.amount_usd,
        )
        for r in records
    ]
    response = DailyCostsResponse(data=items, total=total, page=page, page_size=page_size)
    await redis.setex(key, CACHE_TTL, response.model_dump_json())
    return response


@router.get("/costs/monthly", response_model=MonthlyCostsResponse)
async def get_monthly_costs(
    year: int = Query(...),
    month: int | None = Query(default=None, ge=1, le=12),
    department: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    params = {
        "year": year,
        "month": month,
        "department": department,
        "account_name": account_name,
    }
    key = _cache_key("monthly", params)

    cached = await redis.get(key)
    if cached:
        return MonthlyCostsResponse.model_validate_json(cached)

    repo = CostRepository(db)
    rows = await repo.get_monthly_costs(
        year=year,
        month=month,
        department=department,
        account_name=account_name,
    )

    items = [
        MonthlyCostItem(
            year_month=row["year_month"].strftime("%Y-%m"),
            department=row["department"],
            amount_usd=row["amount_usd"],
        )
        for row in rows
    ]
    response = MonthlyCostsResponse(data=items, total=len(items))
    await redis.setex(key, CACHE_TTL, response.model_dump_json())
    return response


@router.get("/costs/summary", response_model=SummaryResponse)
async def get_costs_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    params = {"start_date": start_date, "end_date": end_date}
    key = _cache_key("summary", params)

    cached = await redis.get(key)
    if cached:
        return SummaryResponse.model_validate_json(cached)

    repo = CostRepository(db)
    summary = await repo.get_summary(start_date=start_date, end_date=end_date)

    response = SummaryResponse(
        by_department=summary["by_department"],
        by_account=summary["by_account"],
        by_tag=summary["by_tag"],
    )
    await redis.setex(key, CACHE_TTL, response.model_dump_json())
    return response


@router.get("/costs/business-summary")
async def get_business_summary(
    account_name: str | None = Query(default=None),
    months: int = Query(default=3, ge=1, le=12, description="查询最近N个月"),
    db: AsyncSession = Depends(get_db),
):
    """
    按业务模块汇总多月费用，用于展示类似截图的对比表格。
    返回每个业务模块在各月的费用及环比变化。
    """
    import calendar
    from datetime import date as date_type

    today = date_type.today()
    month_list = []
    for i in range(months - 1, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_list.append((y, m))

    repo = CostRepository(db)
    rows = await repo.get_business_summary(months=month_list, account_name=account_name)

    month_keys = [f"{y}-{m:02d}" for y, m in month_list]

    # 整理数据，按业务模块聚合（同一 biz_name 的多个部门合并为一行）
    # key: (account_name, biz_group, biz_name, tag_value_normalized)
    merged: dict[tuple, dict] = {}

    for row in rows:
        tag = row["tag_value"]
        dept = row["department"]
        matched = _match_appname(tag)  # 对原始 tag value 做包含匹配
        biz_info = BIZ_META.get(matched) if matched else None

        biz_group = biz_info["group"] if biz_info else ("Public" if tag is None else "其他")
        biz_name = biz_info["name"] if biz_info else (tag or f"Public分摊({dept})")

        # Public 分摊按部门单独一行（不合并）
        if biz_group == "Public" or tag is None:
            merge_key = (row["account_name"], biz_group, f"Public分摊({dept})", None, dept)
        else:
            merge_key = (row["account_name"], biz_group, biz_name, matched or tag, "")

        if merge_key not in merged:
            merged[merge_key] = {
                "account_name": row["account_name"],
                "tag_value": tag,
                "biz_group": biz_group,
                "biz_name": biz_name if biz_group != "Public" else f"Public分摊({dept})",
                "department": dept,
                "month_costs": {ym: 0.0 for ym in month_keys},
                "dept_breakdown": {},  # {dept: {ym: amount}}
            }

        for ym in month_keys:
            v = float(row["month_costs"].get(ym, 0))
            merged[merge_key]["month_costs"][ym] = merged[merge_key]["month_costs"].get(ym, 0) + v
            if dept not in merged[merge_key]["dept_breakdown"]:
                merged[merge_key]["dept_breakdown"][dept] = {ym2: 0.0 for ym2 in month_keys}
            merged[merge_key]["dept_breakdown"][dept][ym] = merged[merge_key]["dept_breakdown"][dept].get(ym, 0) + v

    result = []
    for item in merged.values():
        costs = item["month_costs"]
        last = costs.get(month_keys[-1], 0)
        prev = costs.get(month_keys[-2], 0) if len(month_keys) >= 2 else 0
        result.append({
            "account_name": item["account_name"],
            "tag_value": item["tag_value"],
            "department": item["department"],
            "biz_group": item["biz_group"],
            "biz_name": item["biz_name"],
            "month_costs": costs,
            "dept_breakdown": item["dept_breakdown"],
            "mom_change": round(last - prev, 4),
        })

    GROUP_ORDER = ["共用", "SmartProduct", "Community", "AI", "Phone", "Public", "其他"]
    result.sort(key=lambda x: (
        GROUP_ORDER.index(x["biz_group"]) if x["biz_group"] in GROUP_ORDER else 99,
        -x["month_costs"].get(month_keys[-1], 0)
    ))

    return {"months": month_keys, "data": result}
