"""
APScheduler 定时任务配置。
每日 02:00 触发费用同步，启动时检查昨日是否有成功同步记录并补同步。
"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.models import SyncLog

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_daily_sync() -> None:
    """每日定时同步任务：创建独立 DB session，执行 sync_all()。"""
    logger.info("Scheduled daily sync triggered.")
    async with AsyncSessionLocal() as db:
        from backend.app.services.cost_sync import CostSyncService  # noqa: PLC0415

        service = CostSyncService(db)
        try:
            await service.sync_all()
        except Exception as exc:  # noqa: BLE001
            logger.error("Daily sync failed: %s", exc)

async def check_and_backfill() -> None:
    """
    启动时补同步检查：若昨日没有成功的同步记录，则触发补同步。
    """
    yesterday = date.today() - timedelta(days=1)
    logger.info("Checking backfill for %s ...", yesterday)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SyncLog).where(
                SyncLog.status == "success",
            )
        )
        logs = result.scalars().all()

        # 检查是否有昨日成功的同步记录（finished_at 在昨日范围内）
        has_success = any(
            log.finished_at is not None and log.finished_at.date() == yesterday
            for log in logs
        )

        if not has_success:
            logger.info("No successful sync found for %s, triggering backfill.", yesterday)
            from backend.app.services.cost_sync import CostSyncService  # noqa: PLC0415

            service = CostSyncService(db)
            try:
                await service.sync_all(start_date=yesterday, end_date=yesterday)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Backfill sync failed (will retry on next schedule): %s", exc)
        else:
            logger.info("Successful sync already exists for %s, skipping backfill.", yesterday)


# 注册每日 02:00 定时任务
scheduler.add_job(run_daily_sync, CronTrigger(hour=2, minute=0), id="daily_sync", replace_existing=True)
