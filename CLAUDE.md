# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

智能人才库 (AI4TALENTS) - 学术人才子系统 MVP
一个基于 OpenAlex 学术数据库的人才发现平台，面向招聘团队的内部工具。

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy 2.x + Alembic (async)
- SQLite (development) / PostgreSQL (production)
- Pydantic v2

### Frontend
- React 18 + TypeScript
- Vite
- Ant Design v5
- React Router v6
- Zustand (state management)

## Project Structure

```
talent-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # API endpoints
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic DTOs
│   │   ├── repositories/      # Data access layer
│   │   ├── services/          # Business logic
│   │   │   ├── collect/       # Data collection orchestration
│   │   │   ├── sync/          # Data synchronization
│   │   │   └── normalizers/   # Data normalization
│   │   ├── builders/          # Object construction (ETL transform)
│   │   └── core/              # Config, database, security
│   ├── migrations/            # Alembic migrations
│   └── scripts/               # Utility scripts
├── frontend/
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   ├── services/          # API client
│   │   ├── contexts/          # React contexts (Auth, Favorites)
│   │   └── hooks/             # Custom hooks
│   └── tests/                 # Playwright E2E tests
└── docs/                      # Project documentation
```

## Common Commands

```bash
# Backend
cd backend
python -m venv .venv && .venv/Scripts/activate  # Windows
pip install -r requirements.txt
alembic upgrade head          # Run migrations
uvicorn app.main:app --reload --port 8003

# Backend Testing
pytest                        # Run all tests
pytest tests/test_models.py   # Run specific test file
pytest -v --cov=app           # Run with coverage
pytest -m "not slow"          # Skip slow tests

# Backend Linting
ruff check app/               # Lint
black app/                    # Format
mypy app/                     # Type check

# Frontend
cd frontend
npm install
npm run dev     # Start dev server on port 5173
npm run build   # Production build
npm run lint    # ESLint

# Frontend E2E Testing
npx playwright test           # Run all Playwright tests
npx playwright test --ui      # Run with UI
```

## Architecture Patterns

### Backend Layered Architecture
1. **Endpoints**: Request handling, validation via Pydantic schemas
2. **Services**: Business logic, orchestration
3. **Repositories**: Database operations, query building
4. **Builders**: Transform raw data into domain objects (ETL pattern)
5. **Models**: SQLAlchemy ORM models

### Data Collection Pipeline
- `services/collect/` - Task creation and venue execution
- `services/sync/` - Author, school, tech tag synchronization
- `services/normalizers/` - Data standardization (school names, author names)

### Frontend State Management
- **AuthContext**: User authentication state
- **FavoritesContext**: Favorites and talent pool state
- **Zustand**: Global state store
- **localStorage**: Column configs, search templates

### Database Naming Conventions
- Table naming: `{module}_{entity}` (e.g., `core_talent`, `iam_user_account`)
- Primary keys: `{entity}_id` (e.g., `talent_id`, `school_id`)
- Timestamps: `created_at`, `updated_at` via TimestampMixin

## API Conventions

- Base path: `/api/v1`
- Authentication: Bearer token in Authorization header
- Pagination: `page`, `page_size` query params
- Response format: JSON with consistent structure

## Key Files

| Purpose | Path |
|---------|------|
| API endpoints | `backend/app/api/v1/endpoints/` |
| Data models | `backend/app/models/` |
| Frontend pages | `frontend/src/pages/` |
| API client | `frontend/src/services/api.ts` |
| Test fixtures | `backend/tests/conftest.py` |

## Git Workflow

- `main` - Production-ready code
- `feature/*` - Feature branches
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`

## Notes

- Development uses SQLite; production uses PostgreSQL
- Default admin: `admin` / `admin123`
- Frontend port: 5173 (fixed), Backend port: 8003
- OpenAlex API: https://api.openalex.org
