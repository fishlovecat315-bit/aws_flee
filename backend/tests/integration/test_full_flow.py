"""
集成测试：完整同步 → 分摊 → 预警流程

Requirements: 1.1, 1.2, 1.6, 6.2, 6.3

使用 testcontainers 启动真实 PostgreSQL，moto mock AWS CE，responses mock 钉钉 Webhook。
"""
import os
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
import responses as responses_lib
from moto import mock_ce
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

# ---------------------------------------------------------------------------
# 测试常量
# ---------------------------------------------------------------------------

TEST_DATE = date(2024, 1, 15)
DINGTALK_URL = "https://oapi.dingtalk.com/robot/send?access_token=test"

PLM_ACCOUNT_ID = "111111111111"
MAIN_ACCOUNT_ID = "222222222222"
CN_ACCOUNT_ID = "333333333333"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def postgres_container():
    """启动真实 PostgreSQL 容器（模块级别，所有测试共享）。"""
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="module")
async def db_engine(postgres_container):
    """创建 async engine，指向测试容器。"""
    # testcontainers 返回 psycopg2 URL，需转换为 asyncpg URL
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(async_url, echo=False)

    # 创建所有表
    from backend.app.core.database import Base  # noqa: PLC0415
    import backend.app.models.models  # noqa: F401, PLC0415 — 确保模型注册到 Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """每个测试用例独立的数据库 session，测试后回滚。"""
    SessionLocal = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with SessionLocal() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# 环境变量 patch（在导入 settings 之前设置）
# ---------------------------------------------------------------------------


def _patch_settings(monkeypatch, db_url: str) -> None:
    """覆盖 settings 中的关键配置，指向测试环境。"""
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("PLM_ACCOUNT_ID", PLM_ACCOUNT_ID)
    monkeypatch.setenv("MAIN_ACCOUNT_ID", MAIN_ACCOUNT_ID)
    monkeypatch.setenv("CN_ACCOUNT_ID", CN_ACCOUNT_ID)
    monkeypatch.setenv("DINGTALK_WEBHOOK_URL", DINGTALK_URL)
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')


# ---------------------------------------------------------------------------
# 辅助：构造 moto CE mock 数据
# ---------------------------------------------------------------------------


def _build_ce_response(start: date, end: date, groups: list[dict]) -> dict:
    """构造 moto get_cost_and_usage 返回格式。"""
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
                "Groups": groups,
                "Estimated": False,
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }


def _make_group(service: str, tag_value: str, amount: str) -> dict:
    return {
        "Keys": [service, f"Name${tag_value}"],
        "Metrics": {"BlendedCost": {"Amount": amount, "Unit": "USD"}},
    }


# ---------------------------------------------------------------------------
# 主集成测试
# ---------------------------------------------------------------------------


@mock_ce
@responses_lib.activate
@pytest.mark.asyncio
async def test_full_sync_allocate_alert_flow(
    postgres_container,
    db_engine,
    db_session: AsyncSession,
    monkeypatch,
):
    """
    完整流程集成测试：
    1. 触发 CostSyncService.sync_all()
    2. 验证 raw_cost_records 包含三个账号的数据
    3. 验证 allocated_cost_records 包含目标日期的分摊结果
    4. 验证钉钉 Webhook 被调用（Smart 部门超阈值）

    Validates: Requirements 1.1, 1.2, 1.6, 6.2, 6.3
    """
    import importlib  # noqa: PLC0415

    # --- 1. 覆盖 settings ---
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    _patch_settings(monkeypatch, async_url)

    # 重新加载 settings 模块，使 monkeypatch 生效
    import backend.app.core.config as config_module  # noqa: PLC0415

    importlib.reload(config_module)
    config_module.settings = config_module.Settings()

    # 同步更新各服务模块引用的 settings
    import backend.app.services.cost_sync as cost_sync_module  # noqa: PLC0415
    import backend.app.services.alert_service as alert_module  # noqa: PLC0415

    cost_sync_module.settings = config_module.settings
    alert_module.settings = config_module.settings

    # --- 2. 注册钉钉 Webhook mock ---
    responses_lib.add(
        responses_lib.POST,
        DINGTALK_URL,
        json={"errcode": 0, "errmsg": "ok"},
        status=200,
    )

    # --- 3. 插入 AlertThreshold（Smart 部门，阈值 $100，很容易超过）---
    from backend.app.models.models import AlertThreshold  # noqa: PLC0415

    threshold = AlertThreshold(
        department="Smart",
        monthly_threshold_usd=Decimal("100.00"),
        is_active=True,
    )
    db_session.add(threshold)
    await db_session.commit()

    # --- 4. 配置 moto CE mock 数据（三个账号各返回一条记录）---
    import boto3  # noqa: PLC0415

    ce_client = boto3.client("ce", region_name="us-east-1")

    from unittest.mock import patch  # noqa: PLC0415
    from datetime import timedelta  # noqa: PLC0415

    start = TEST_DATE
    end = TEST_DATE + timedelta(days=1)

    plm_response = _build_ce_response(
        start, end,
        [_make_group("Amazon EC2", "OBA-app", "50.0000")]
    )
    main_response = _build_ce_response(
        start, end,
        [_make_group("Amazon S3", "nothing x", "200.0000")]  # Smart 部门，超过 $100 阈值
    )
    cn_response = _build_ce_response(
        start, end,
        [_make_group("Amazon RDS", "NothingX", "30.0000")]
    )

    # moto 对 CE 的 mock 是全局的，通过 patch 返回值来控制不同账号的响应
    # 由于三个账号使用同一个 CE client（moto 不区分账号），
    # 我们 patch _fetch_cost_and_usage 来按账号返回不同数据
    call_count = {"n": 0}
    responses_map = [plm_response, main_response, cn_response]

    def fake_fetch(self_svc, account_id, start_date, end_date):
        idx = call_count["n"]
        call_count["n"] += 1
        return responses_map[idx % len(responses_map)]

    # --- 5. 执行同步 ---
    from backend.app.services.cost_sync import CostSyncService  # noqa: PLC0415

    with patch.object(CostSyncService, "_fetch_cost_and_usage", fake_fetch):
        sync_log = await CostSyncService(db_session).sync_all(target_date=TEST_DATE)

    # --- 6. 验证 sync_log ---
    assert sync_log.status == "success", f"sync_log.status={sync_log.status!r}"
    assert sync_log.records_count == 3  # 三个账号各 1 条

    # --- 7. 验证 raw_cost_records 包含三个账号的数据（Requirement 1.1, 1.2）---
    from backend.app.models.models import RawCostRecord  # noqa: PLC0415

    result = await db_session.execute(
        select(RawCostRecord).where(RawCostRecord.date == TEST_DATE)
    )
    raw_records = result.scalars().all()
    assert len(raw_records) == 3, f"Expected 3 raw records, got {len(raw_records)}"

    account_names = {r.account_name for r in raw_records}
    assert account_names == {"PLM", "主业务", "国内"}, f"Missing accounts: {account_names}"

    # --- 8. 验证 allocated_cost_records 包含目标日期的分摊结果（Requirement 1.6）---
    from backend.app.models.models import AllocatedCostRecord  # noqa: PLC0415

    alloc_result = await db_session.execute(
        select(AllocatedCostRecord).where(AllocatedCostRecord.date == TEST_DATE)
    )
    allocated_records = alloc_result.scalars().all()
    assert len(allocated_records) > 0, "No allocated records found for test date"

    allocated_depts = {r.department for r in allocated_records}
    # Smart 来自主业务账号 nothing x tag，IT 来自 PLM OBA-app tag
    assert "Smart" in allocated_depts, f"Smart not in {allocated_depts}"
    assert "IT" in allocated_depts, f"IT not in {allocated_depts}"

    # --- 9. 验证钉钉 Webhook 被调用（Smart 超过 $100 阈值，Requirement 6.2, 6.3）---
    dingtalk_calls = [
        call for call in responses_lib.calls
        if DINGTALK_URL in call.request.url
    ]
    assert len(dingtalk_calls) >= 1, "DingTalk webhook was not called"

    import json  # noqa: PLC0415

    payload = json.loads(dingtalk_calls[0].request.body)
    assert payload["msgtype"] == "markdown"
    text_content = payload["markdown"]["text"]
    assert "Smart" in text_content, "Department name missing from DingTalk message"
    assert "$" in text_content, "Amount missing from DingTalk message"
