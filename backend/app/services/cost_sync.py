"""
CostSyncService: 从 AWS Cost Explorer 同步费用数据到 raw_cost_records 表。
三个子账号（PLM / 主业务 / 国内）各自使用独立凭证。
支持单日同步和日期范围批量同步。
AWS Cost Explorer DAILY 粒度单次最多返回 14 天，超过自动分段请求。
"""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import boto3
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.models import AwsCredentialSetting, RawCostRecord, SyncLog

logger = logging.getLogger(__name__)

# asyncpg 参数上限约 32767，每条记录 8 个字段，批次大小 1000 条（8000 参数）
BATCH_SIZE = 1000
# AWS Cost Explorer DAILY 粒度 + GroupBy 单次最多约 5000 行，按 7 天分段确保不截断
CE_MAX_DAYS = 7

ACCOUNTS = [
    {"prefix": "PLM", "account_name": "PLM"},
    {"prefix": "MAIN", "account_name": "主业务"},
    {"prefix": "CN", "account_name": "国内"},
]


async def _load_account_creds(db: AsyncSession, prefix: str) -> dict[str, str]:
    keys = [f"{prefix}_ACCESS_KEY_ID", f"{prefix}_SECRET_ACCESS_KEY",
            f"{prefix}_REGION", f"{prefix}_ACCOUNT_ID"]
    result = await db.execute(
        select(AwsCredentialSetting).where(AwsCredentialSetting.key.in_(keys))
    )
    return {row.key: row.value for row in result.scalars().all()}


class CostSyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_ce_client(self, access_key: str, secret_key: str, region: str):
        return boto3.client(
            "ce",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def _fetch_chunk(self, access_key: str, secret_key: str, region: str,
                     start: date, end: date) -> dict:
        """同步调用 AWS Cost Explorer API（在 executor 中运行）。"""
        ce = self._get_ce_client(access_key, secret_key, region)
        return ce.get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            GroupBy=[
                {"Type": "TAG", "Key": "Product"},
            ],
            Metrics=["BlendedCost"],
        )

    async def sync_account(
        self, account_id: str, account_name: str,
        access_key: str, secret_key: str, region: str,
        start_date: date, end_date: date,
    ) -> int:
        """
        拉取指定账号指定范围的费用数据并 UPSERT。
        自动将超过 14 天的范围拆成多段请求。
        end_date 是 AWS API 的不含结束日（即 start_date + N 天）。
        """
        loop = asyncio.get_event_loop()
        records = []

        chunk_start = start_date
        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=CE_MAX_DAYS), end_date)
            resp = await loop.run_in_executor(
                None, self._fetch_chunk,
                access_key, secret_key, region, chunk_start, chunk_end,
            )
            for time_period in resp.get("ResultsByTime", []):
                record_date = date.fromisoformat(time_period["TimePeriod"]["Start"])
                for group in time_period.get("Groups", []):
                    keys = group.get("Keys", [])
                    raw_tag = keys[0] if keys else ""
                    # Product tag 格式: "Product$value" 或 "Product$"（无标签）
                    if "$" in raw_tag:
                        raw_value = raw_tag.split("$", 1)[1].strip() or None
                    else:
                        raw_value = None
                    # 保存原始 Product tag value，不做标准化
                    tag_value = raw_value
                    amount_str = (
                        group.get("Metrics", {}).get("BlendedCost", {}).get("Amount", "0")
                    )
                    records.append({
                        "account_id": account_id,
                        "account_name": account_name,
                        "date": record_date,
                        "service": "ALL",
                        "tag_key": "Product" if tag_value else None,
                        "tag_value": tag_value,
                        "amount_usd": Decimal(amount_str),
                        "currency": "USD",
                    })
            chunk_start = chunk_end

        if not records:
            return 0

        total_inserted = 0
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            stmt = pg_insert(RawCostRecord).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["account_id", "date", "service", "tag_key", "tag_value"],
                set_={"amount_usd": stmt.excluded.amount_usd, "synced_at": func.now()},
            )
            await self.db.execute(stmt)
            total_inserted += len(batch)
        await self.db.flush()
        return total_inserted


    async def sync_all(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> SyncLog:
        """
        同步指定日期范围的费用数据。
        不传参数默认同步昨天。
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=1)
        if end_date is None:
            end_date = start_date
        # AWS API end_date 不含，+1 天
        api_end_date = end_date + timedelta(days=1)

        now = datetime.now(tz=timezone.utc)
        sync_log = SyncLog(started_at=now, status="running")
        self.db.add(sync_log)
        await self.db.flush()

        total_records = 0
        synced_accounts = []

        try:
            for account_cfg in ACCOUNTS:
                prefix = account_cfg["prefix"]
                account_name = account_cfg["account_name"]
                creds = await _load_account_creds(self.db, prefix)
                access_key = creds.get(f"{prefix}_ACCESS_KEY_ID", "")
                secret_key = creds.get(f"{prefix}_SECRET_ACCESS_KEY", "")
                region = creds.get(f"{prefix}_REGION", "us-east-1")
                account_id = creds.get(f"{prefix}_ACCOUNT_ID", "")

                if not access_key or not secret_key or not account_id:
                    logger.warning("账号 %s 凭证未配置，跳过同步", account_name)
                    continue

                count = await self.sync_account(
                    account_id=account_id, account_name=account_name,
                    access_key=access_key, secret_key=secret_key, region=region,
                    start_date=start_date, end_date=api_end_date,
                )
                total_records += count
                synced_accounts.append(account_name)
                logger.info("Synced %s [%s~%s]: %d records", account_name, start_date, end_date, count)

            sync_log.status = "success"
            sync_log.finished_at = datetime.now(tz=timezone.utc)
            sync_log.accounts_synced = ", ".join(synced_accounts) if synced_accounts else "none"
            sync_log.records_count = total_records
            await self.db.commit()

            try:
                from backend.app.services.allocation_engine import AllocationEngine  # noqa: PLC0415
                engine = AllocationEngine(self.db)
                await engine.allocate_date_range(start_date, end_date)
            except ImportError:
                logger.debug("AllocationEngine not yet available, skipping.")
            except Exception as exc:  # noqa: BLE001
                logger.error("AllocationEngine failed after sync: %s", exc, exc_info=True)

        except Exception as exc:
            logger.error("sync_all failed: %s", exc, exc_info=True)
            sync_log.status = "failed"
            sync_log.finished_at = datetime.now(tz=timezone.utc)
            sync_log.error_message = str(exc)
            await self.db.commit()
            raise

        return sync_log
