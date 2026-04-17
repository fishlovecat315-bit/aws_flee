"""
AlertService: 在分摊计算完成后，汇总各业务部门当月累计费用，
与 alert_thresholds 对比，超阈值时通过钉钉 Webhook 发送通知。
"""
import logging
from datetime import date, datetime
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.models import AlertThreshold, AllocatedCostRecord

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_alert(self) -> None:
        """汇总各部门当月累计费用，与阈值对比，超阈值时发送钉钉通知。"""
        today = date.today()
        month_start = today.replace(day=1)

        # 查询当月各部门累计费用
        result = await self.db.execute(
            select(
                AllocatedCostRecord.department,
                func.sum(AllocatedCostRecord.amount_usd).label("total"),
            )
            .where(AllocatedCostRecord.date >= month_start)
            .group_by(AllocatedCostRecord.department)
        )
        dept_totals: dict[str, Decimal] = {
            row.department: Decimal(str(row.total)) for row in result.all()
        }

        # 查询所有激活的预警阈值
        threshold_result = await self.db.execute(
            select(AlertThreshold).where(AlertThreshold.is_active == True)  # noqa: E712
        )
        thresholds = threshold_result.scalars().all()

        for threshold in thresholds:
            current_amount = dept_totals.get(threshold.department, Decimal("0"))
            if current_amount > threshold.monthly_threshold_usd:
                await self._send_dingtalk(
                    department=threshold.department,
                    current_amount=current_amount,
                    threshold=Decimal(str(threshold.monthly_threshold_usd)),
                )

    async def _send_dingtalk(
        self, department: str, current_amount: Decimal, threshold: Decimal
    ) -> None:
        """构造钉钉 Markdown 消息并发送，失败时记录错误日志，不抛出异常。"""
        excess = current_amount - threshold
        stat_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        text = (
            f"### ⚠️ AWS 费用预警\n\n"
            f"**业务部门**：{department}\n\n"
            f"**当月累计费用**：${current_amount}\n\n"
            f"**预警阈值**：${threshold}\n\n"
            f"**超出金额**：${excess}\n\n"
            f"**统计时间**：{stat_date}"
        )

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "AWS 费用预警",
                "text": text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    settings.DINGTALK_WEBHOOK_URL,
                    json=payload,
                )
                response.raise_for_status()
                logger.info(
                    "DingTalk alert sent for department=%s, amount=%s, threshold=%s",
                    department,
                    current_amount,
                    threshold,
                )
        except Exception as exc:
            logger.error(
                "Failed to send DingTalk alert for department=%s: %s",
                department,
                exc,
            )
