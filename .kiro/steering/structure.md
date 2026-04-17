# Project Structure

```
backend/
  app/
    api/          # FastAPI routers — one file per domain (costs, rules, alerts, sync, export, settings)
    core/         # Infra setup: database.py, config.py, redis_client.py, scheduler.py
    models/       # SQLAlchemy ORM models (models.py — all models in one file)
    repositories/ # DB query layer — CostRepository, RuleRepository
    schemas/      # Pydantic request/response schemas
    services/     # Business logic — AllocationEngine, CostSync, AlertService, ExportService
    main.py       # FastAPI app, router registration, lifespan
  alembic/
    versions/     # Sequential migration files: 0001_, 0002_, ...
  tests/
    integration/  # Integration tests using testcontainers + moto
  check_*.py      # Ad-hoc debug/investigation scripts (not production code)

frontend/
  src/
    api/          # Axios client (client.ts)
    components/   # Shared UI components (CostChart, CostSummaryTable, Layout)
    pages/        # Route-level page components (Dashboard, CostDetail, RulesManagement, etc.)
    types/        # Shared TypeScript types (index.ts)
  index.html
  vite.config.ts

docker/
  postgres/init.sql   # DB init script
docker-compose.yml
.env                  # Local secrets (not committed)
```

## Architecture Patterns

- **Layered backend**: API → Service → Repository → Model. Routers stay thin; business logic lives in services.
- **Async everywhere**: All DB access uses `AsyncSession`; all endpoints are `async def`.
- **Dependency injection**: `get_db()` and `get_redis()` injected via FastAPI `Depends`.
- **Redis caching**: API endpoints cache responses with MD5-keyed cache entries (`costs:{endpoint}:{params_hash}`). TTL is 300s.
- **DB rules override hardcoded rules**: `AllocationEngine` checks `_db_rules` dict first before falling back to hardcoded logic.
- **Tag normalization**: Tags are normalized via `_normalize()` (lowercase, strip non-alphanumeric) before any lookup. This function exists in both `allocation_engine.py` and `costs.py` — keep them in sync.
- **Decimal precision**: All monetary amounts use `Decimal` with `ROUND_HALF_UP` and 4 decimal places (`Numeric(12, 4)`).
- **Frontend pages**: Each page manages its own state and fetches data directly via `client` (no global state manager).
- **All API routes**: Prefixed with `/api/v1`.
