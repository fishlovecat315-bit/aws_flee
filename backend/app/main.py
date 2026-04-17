from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.alerts import router as alerts_router
from backend.app.api.costs import router as costs_router
from backend.app.api.export import router as export_router
from backend.app.api.rules import router as rules_router
from backend.app.api.settings import router as settings_router
from backend.app.api.sync import router as sync_router
from backend.app.core.config import settings
from backend.app.core.database import engine
from backend.app.core.redis_client import close_redis
from backend.app.core.scheduler import check_and_backfill, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    await check_and_backfill()
    yield
    scheduler.shutdown(wait=False)
    await engine.dispose()
    await close_redis()


app = FastAPI(title="Nothing AWS Cost Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(costs_router, prefix="/api/v1")
app.include_router(rules_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
