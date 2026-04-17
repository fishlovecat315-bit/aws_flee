"""
API 端到端集成测试

使用 FastAPI TestClient + testcontainers PostgreSQL 测试所有 API 端点的请求/响应格式。

Requirements: 2.1, 2.2, 5.2, 7.1, 7.2, 7.3
"""
import importlib
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

# ---------------------------------------------------------------------------
# Module-level PostgreSQL container (shared across all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="module")
async def test_engine(postgres_container):
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(async_url, echo=False)

    import backend.app.models.models  # noqa: F401 — register models
    from backend.app.core.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# ---------------------------------------------------------------------------
# Fake Redis (no-op implementation)
# ---------------------------------------------------------------------------


class FakeRedis:
    """Minimal fake Redis that always returns cache miss."""

    async def get(self, key):
        return None

    async def setex(self, key, ttl, value):
        pass


# ---------------------------------------------------------------------------
# Build test app with overridden dependencies
# ---------------------------------------------------------------------------


def make_test_app(session_factory) -> FastAPI:
    """Create a FastAPI app with lifespan disabled and test DB/Redis injected."""

    @asynccontextmanager
    async def noop_lifespan(app: FastAPI):
        yield

    from backend.app.api.alerts import router as alerts_router
    from backend.app.api.costs import router as costs_router
    from backend.app.api.export import router as export_router
    from backend.app.api.rules import router as rules_router
    from backend.app.api.sync import router as sync_router
    from backend.app.core.database import get_db
    from backend.app.core.redis_client import get_redis

    app = FastAPI(lifespan=noop_lifespan)
    app.include_router(costs_router, prefix="/api/v1")
    app.include_router(rules_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(export_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fake_redis = FakeRedis()

    def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    return app


# ---------------------------------------------------------------------------
# Fixtures: test client + seed data
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def client(test_session_factory):
    app = make_test_app(test_session_factory)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest_asyncio.fixture(scope="module")
async def seeded_db(test_session_factory):
    """Insert minimal seed data used across tests."""
    from backend.app.models.models import (
        AllocatedCostRecord,
        AllocationRule,
        AlertThreshold,
        SyncLog,
    )

    async with test_session_factory() as session:
        # Allocation rule (shared type with ratios)
        rule = AllocationRule(
            account_name="主业务",
            tag_value="shared-tag",
            rule_type="shared",
            business_module="SharedModule",
            department=None,
            ratios={"Phone": 0.6, "Smart": 0.4},
            is_active=True,
        )
        session.add(rule)

        # Allocated cost record
        record = AllocatedCostRecord(
            date=date(2024, 3, 15),
            account_name="主业务",
            tag_value="shared-tag",
            business_module="SharedModule",
            department="Phone",
            amount_usd=Decimal("120.50"),
            calculated_at=datetime(2024, 3, 16, 2, 0, 0),
        )
        session.add(record)

        # Alert threshold
        threshold = AlertThreshold(
            department="Phone",
            monthly_threshold_usd=Decimal("5000.00"),
            is_active=True,
        )
        session.add(threshold)

        # Sync log
        log = SyncLog(
            started_at=datetime(2024, 3, 16, 2, 0, 0),
            finished_at=datetime(2024, 3, 16, 2, 5, 0),
            status="success",
            accounts_synced="PLM,主业务,国内",
            records_count=10,
        )
        session.add(log)

        await session.commit()

        # Return the rule id for use in tests
        await session.refresh(rule)
        return {"rule_id": rule.id}


# ---------------------------------------------------------------------------
# Tests: Cost endpoints
# ---------------------------------------------------------------------------


def test_get_daily_costs_returns_200(client, seeded_db):
    """GET /api/v1/costs/daily returns 200 with correct response schema.

    Validates: Requirements 2.1
    """
    resp = client.get(
        "/api/v1/costs/daily",
        params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert isinstance(body["data"], list)


def test_get_daily_costs_item_schema(client, seeded_db):
    """Daily cost items contain required fields.

    Validates: Requirements 2.1
    """
    resp = client.get(
        "/api/v1/costs/daily",
        params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    item = body["data"][0]
    assert "date" in item
    assert "department" in item
    assert "account_name" in item
    assert "amount_usd" in item


def test_get_monthly_costs_returns_200(client, seeded_db):
    """GET /api/v1/costs/monthly returns 200 with correct response schema.

    Validates: Requirements 2.2
    """
    resp = client.get("/api/v1/costs/monthly", params={"year": 2024, "month": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body
    assert isinstance(body["data"], list)


def test_get_monthly_costs_item_schema(client, seeded_db):
    """Monthly cost items contain year_month, department, amount_usd.

    Validates: Requirements 2.2
    """
    resp = client.get("/api/v1/costs/monthly", params={"year": 2024, "month": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    item = body["data"][0]
    assert "year_month" in item
    assert "department" in item
    assert "amount_usd" in item


def test_get_costs_summary_returns_200(client, seeded_db):
    """GET /api/v1/costs/summary returns 200 with correct response schema.

    Validates: Requirements 2.1
    """
    resp = client.get(
        "/api/v1/costs/summary",
        params={"start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "by_department" in body
    assert "by_account" in body
    assert "by_tag" in body
    assert isinstance(body["by_department"], list)
    assert isinstance(body["by_account"], list)
    assert isinstance(body["by_tag"], list)


# ---------------------------------------------------------------------------
# Tests: Rules endpoints
# ---------------------------------------------------------------------------


def test_get_rules_returns_200(client, seeded_db):
    """GET /api/v1/rules returns 200 with list of rules.

    Validates: Requirements 5.2
    """
    resp = client.get("/api/v1/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


def test_get_rules_item_schema(client, seeded_db):
    """Rule items contain required fields.

    Validates: Requirements 5.2
    """
    resp = client.get("/api/v1/rules")
    assert resp.status_code == 200
    rule = resp.json()[0]
    assert "id" in rule
    assert "account_name" in rule
    assert "rule_type" in rule
    assert "is_active" in rule


def test_update_rule_invalid_ratios_returns_400(client, seeded_db):
    """PUT /api/v1/rules/{id} returns 400 when ratios don't sum to 1.0.

    Validates: Requirements 5.2
    """
    rule_id = seeded_db["rule_id"]
    resp = client.put(
        f"/api/v1/rules/{rule_id}",
        json={"ratios": {"Phone": 0.5, "Smart": 0.3}},  # sums to 0.8, not 1.0
    )
    assert resp.status_code == 400
    assert "ratios" in resp.json()["detail"].lower()


def test_update_rule_valid_ratios_returns_200(client, seeded_db):
    """PUT /api/v1/rules/{id} returns 200 when ratios sum to 1.0.

    Validates: Requirements 5.2
    """
    rule_id = seeded_db["rule_id"]
    resp = client.put(
        f"/api/v1/rules/{rule_id}",
        json={"ratios": {"Phone": 0.7, "Smart": 0.3}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ratios"]["Phone"] == pytest.approx(0.7)
    assert body["ratios"]["Smart"] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Tests: Alert threshold endpoints
# ---------------------------------------------------------------------------


def test_get_alert_thresholds_returns_200(client, seeded_db):
    """GET /api/v1/alerts/thresholds returns 200 with list.

    Validates: Requirements 7.1
    """
    resp = client.get("/api/v1/alerts/thresholds")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


def test_get_alert_thresholds_item_schema(client, seeded_db):
    """Alert threshold items contain required fields.

    Validates: Requirements 7.1
    """
    resp = client.get("/api/v1/alerts/thresholds")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "id" in item
    assert "department" in item
    assert "monthly_threshold_usd" in item
    assert "is_active" in item


def test_upsert_alert_threshold_creates_new(client, seeded_db):
    """PUT /api/v1/alerts/thresholds/{dept} creates a new threshold.

    Validates: Requirements 7.1
    """
    resp = client.put(
        "/api/v1/alerts/thresholds/NewDept",
        json={"monthly_threshold_usd": "3000.00", "is_active": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["department"] == "NewDept"
    assert float(body["monthly_threshold_usd"]) == pytest.approx(3000.0)
    assert body["is_active"] is True


def test_upsert_alert_threshold_updates_existing(client, seeded_db):
    """PUT /api/v1/alerts/thresholds/{dept} updates an existing threshold.

    Validates: Requirements 7.1
    """
    # First create
    client.put(
        "/api/v1/alerts/thresholds/UpdateDept",
        json={"monthly_threshold_usd": "1000.00", "is_active": True},
    )
    # Then update
    resp = client.put(
        "/api/v1/alerts/thresholds/UpdateDept",
        json={"monthly_threshold_usd": "2000.00", "is_active": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["monthly_threshold_usd"]) == pytest.approx(2000.0)
    assert body["is_active"] is False


# ---------------------------------------------------------------------------
# Tests: Export endpoints
# ---------------------------------------------------------------------------


def test_export_xlsx_returns_200_with_correct_content_type(client, seeded_db):
    """GET /api/v1/export?format=xlsx returns 200 with xlsx content-type.

    Validates: Requirements 7.2, 7.3
    """
    resp = client.get(
        "/api/v1/export",
        params={"format": "xlsx", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]


def test_export_csv_returns_200_with_correct_content_type(client, seeded_db):
    """GET /api/v1/export?format=csv returns 200 with csv content-type.

    Validates: Requirements 7.2, 7.3
    """
    resp = client.get(
        "/api/v1/export",
        params={"format": "csv", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


def test_export_has_content_disposition_header(client, seeded_db):
    """Export response includes Content-Disposition attachment header.

    Validates: Requirements 7.2
    """
    resp = client.get(
        "/api/v1/export",
        params={"format": "csv", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")


# ---------------------------------------------------------------------------
# Tests: Sync logs endpoint
# ---------------------------------------------------------------------------


def test_get_sync_logs_returns_200(client, seeded_db):
    """GET /api/v1/sync/logs returns 200 with list.

    Validates: Requirements 2.1
    """
    resp = client.get("/api/v1/sync/logs")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


def test_get_sync_logs_item_schema(client, seeded_db):
    """Sync log items contain required fields."""
    resp = client.get("/api/v1/sync/logs")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "id" in item
    assert "started_at" in item
    assert "status" in item
