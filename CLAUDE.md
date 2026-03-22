# CLAUDE.md

This file provides guidance to Claude Code when working with this project.

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
│   │   └── core/              # Config, database, security
│   ├── migrations/            # Alembic migrations
│   └── scripts/               # Utility scripts
├── frontend/
│   ├── src/
│   │   ├── pages/             # Page components
│   │   ├── components/        # Reusable components
│   │   ├── services/          # API client
│   │   ├── contexts/          # React contexts
│   │   └── hooks/             # Custom hooks
│   └── ...
└── docs/                      # Project documentation
```

## Development Guidelines

### Backend
- Use async/await for all database operations
- Repository pattern for data access
- Pydantic schemas for request/response validation
- Alembic for database migrations
- JWT for authentication

### Frontend
- Functional components with hooks
- Ant Design components for UI
- React Context for global state (auth, favorites)
- localStorage for user preferences (column config, search templates)

### Database
- Table naming: `{module}_{entity}` (e.g., `core_talent`, `iam_user_account`)
- Primary keys: `{entity}_id` (e.g., `talent_id`, `school_id`)
- Timestamps: `created_at`, `updated_at` via TimestampMixin

## Key Files

| Purpose | Path |
|---------|------|
| API endpoints | `backend/app/api/v1/endpoints/` |
| Data models | `backend/app/models/` |
| Frontend pages | `frontend/src/pages/` |
| Frontend components | `frontend/src/components/` |
| API client | `frontend/src/services/api.ts` |
| Database config | `backend/app/core/database.py` |
| Data sync script | `backend/scripts/sync_openalex_data.py` |

## Common Commands

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate  # Create/activate venv
pip install -r requirements.txt
alembic upgrade head          # Run migrations
python scripts/sync_openalex_data.py  # Sync data from OpenAlex
uvicorn app.main:app --reload --port 8003

# Frontend
cd frontend
npm install
npm run dev     # Start dev server on port 5178
npm run build   # Production build
```

## API Conventions

- Base path: `/api/v1`
- Authentication: Bearer token in Authorization header
- Pagination: `page`, `page_size` query params
- Response format: JSON with consistent structure

## Git Workflow

- `main` - Production-ready code
- `feature/*` - Feature branches
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Tag releases: `v1.0.0-mvp-baseline`, `v1.1.0`, etc.

## Notes

- Development uses SQLite; production uses PostgreSQL
- Default admin: `admin` / `admin123`
- Frontend runs on port 5178, backend on 8003
- OpenAlex API: https://api.openalex.org
