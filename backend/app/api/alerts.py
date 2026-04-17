from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.models import AlertThreshold
from backend.app.schemas.alert import AlertThresholdResponse, AlertThresholdUpdate

router = APIRouter()


@router.get("/alerts/thresholds", response_model=list[AlertThresholdResponse])
async def get_thresholds(db: AsyncSession = Depends(get_db)):
    """Return all alert thresholds."""
    result = await db.execute(select(AlertThreshold).order_by(AlertThreshold.department))
    return result.scalars().all()


@router.put("/alerts/thresholds/{dept}", response_model=AlertThresholdResponse)
async def upsert_threshold(
    dept: str,
    body: AlertThresholdUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update the alert threshold for a department."""
    result = await db.execute(
        select(AlertThreshold).where(AlertThreshold.department == dept)
    )
    threshold = result.scalar_one_or_none()

    if threshold is None:
        threshold = AlertThreshold(
            department=dept,
            monthly_threshold_usd=body.monthly_threshold_usd,
            is_active=body.is_active,
        )
        db.add(threshold)
    else:
        threshold.monthly_threshold_usd = body.monthly_threshold_usd
        threshold.is_active = body.is_active

    await db.commit()
    await db.refresh(threshold)
    return threshold
