from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.repositories.cost_repository import CostRepository
from backend.app.services.export_service import ExportService

router = APIRouter()

CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "pdf": "application/pdf",
}


@router.get("/export")
async def export_costs(
    format: Literal["xlsx", "csv", "pdf"] = Query(..., description="Export format"),
    start_date: date = Query(...),
    end_date: date = Query(...),
    department: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    repo = CostRepository(db)
    # Fetch all records (no pagination) for export
    records, _ = await repo.get_daily_costs(
        start_date=start_date,
        end_date=end_date,
        department=department,
        account_name=account_name,
        page=1,
        page_size=100_000,
    )

    data = [
        {
            "date": r.date,
            "department": r.department,
            "account_name": r.account_name,
            "tag_value": r.tag_value,
            "business_module": r.business_module,
            "amount_usd": r.amount_usd,
        }
        for r in records
    ]

    svc = ExportService()
    if format == "xlsx":
        content = svc.export_excel(data)
    elif format == "csv":
        content = svc.export_csv(data)
    else:
        content = svc.export_pdf(data)

    filename = f"costs_{start_date}_{end_date}.{format}"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }

    import io
    return StreamingResponse(
        io.BytesIO(content),
        media_type=CONTENT_TYPES[format],
        headers=headers,
    )
