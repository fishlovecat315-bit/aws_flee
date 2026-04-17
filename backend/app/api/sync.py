from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal, get_db
from backend.app.models.models import SyncLog
from backend.app.schemas.sync import SyncLogResponse
from backend.app.services.cost_sync import CostSyncService

router = APIRouter()


@router.get("/sync/logs", response_model=list[SyncLogResponse])
async def get_sync_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SyncLog).order_by(SyncLog.started_at.desc()).limit(50)
    )
    return result.scalars().all()


async def _run_sync(start_date: Optional[date], end_date: Optional[date]) -> None:
    """后台任务：独立创建 session，避免请求结束后 session 关闭的问题。"""
    async with AsyncSessionLocal() as db:
        service = CostSyncService(db)
        await service.sync_all(start_date=start_date, end_date=end_date)


@router.post("/sync/trigger", status_code=202)
async def trigger_sync(
    background_tasks: BackgroundTasks,
    start_date: Optional[date] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="结束日期 YYYY-MM-DD（含）"),
):
    """
    触发费用同步。
    - 不传参数：同步昨天
    - 传 start_date/end_date：同步指定日期范围（历史补拉）
    """
    background_tasks.add_task(_run_sync, start_date, end_date)
    if start_date:
        msg = f"Sync triggered for {start_date} ~ {end_date or start_date}"
    else:
        msg = "Sync triggered for yesterday"
    return {"message": msg}
