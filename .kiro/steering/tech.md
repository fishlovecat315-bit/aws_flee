# Tech Stack

## Backend
- **Runtime**: Python 3.11+
- **Framework**: FastAPI with async/await throughout
- **ORM**: SQLAlchemy 2.0 (async) with `asyncpg` driver
- **Migrations**: Alembic (sequential versioning: `0001_`, `0002_`, ...)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7 (response caching, 5-minute TTL default)
- **AWS SDK**: boto3 (Cost Explorer API)
- **Scheduler**: APScheduler (daily sync + backfill on startup)
- **Alerts**: DingTalk webhook
- **Export**: openpyxl (Excel), WeasyPrint (PDF)
- **Config**: pydantic-settings, `.env` file

## Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite 5
- **UI Library**: Ant Design 5
- **Charts**: ECharts via echarts-for-react
- **Routing**: React Router v6
- **HTTP Client**: Axios (baseURL: `/api/v1`, 30s timeout)

## Infrastructure
- **Containerization**: Docker + Docker Compose
- **Services**: postgres, redis, backend (port 8000), frontend/nginx (port 3000)
- **Reverse Proxy**: nginx serves frontend static files and proxies `/api` to backend

## Testing
- **Framework**: pytest + pytest-asyncio (`asyncio_mode = auto`)
- **AWS Mocking**: moto (`moto[ce]`)
- **DB Testing**: testcontainers (PostgreSQL)
- **Property-Based**: Hypothesis
- **HTTP Mocking**: responses

## Common Commands

```bash
# Start all services
docker compose up -d

# Backend only (local dev)
cd backend
uvicorn backend.app.main:app --reload --port 8000

# Run migrations
cd backend
alembic upgrade head

# Create a new migration
alembic revision -m "description"

# Run tests (from backend/)
pytest
pytest tests/integration/

# Frontend dev server
cd frontend
npm run dev

# Frontend build
npm run build
```

## Environment Variables (`.env`)
Required: `DATABASE_URL`, `REDIS_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `PLM_ACCOUNT_ID`, `MAIN_ACCOUNT_ID`, `CN_ACCOUNT_ID`, `DINGTALK_WEBHOOK_URL`
