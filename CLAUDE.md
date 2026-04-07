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
- PostgreSQL
- Pydantic v2

### Frontend
- React 18 + TypeScript
- Vite
- Ant Design v5
- React Router v6
- Zustand (state management)

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

# Utility Scripts (backend/scripts/)
# System initialization
python scripts/init_system.py              # Reset system with interactive confirmation
python scripts/init_system.py --force      # Reset without confirmation
python scripts/seed_tech_elements.py       # Seed six tech elements

# Data maintenance
python scripts/fix_pending_normalization.py --task-id <ID> [--sync]  # Fix pending normalization
python scripts/refresh_stats.py                                       # Refresh all statistics
python scripts/recalculate_cs_scores.py    # Recalculate CS background scores
python scripts/resync_talents_v2.py        # Re-sync talents with CS filtering
```

## Architecture

### Three-Layer Data Architecture

The system uses a three-layer data model for data quality and traceability:

| Layer | Tables | Purpose |
|-------|--------|---------|
| **Raw** | `raw_work`, `raw_author`, `raw_institution` | Original data from OpenAlex API |
| **Standardized** | `std_author`, `std_school` | Cleaned and normalized data with CS score |
| **Serving** | `core_talent`, `core_school` | User-facing data with business logic |

Data flows: Raw → Standardized (via Normalizers) → Serving (via Sync services)

**CS Background Filtering**: Authors are filtered at the Standardized → Serving transition. Only authors with `cs_concepts_score >= 0.5` are synced to Talent. See `services/common/cs_concepts.py` for threshold configuration.

### Six Tech Elements (Domain Model)

The system organizes talent by six technical domains:

| Code | Name (EN) | Name (CN) |
|------|-----------|-----------|
| `ai` | Artificial Intelligence | 人工智能 |
| `robotics` | Robotics | 机器人 |
| `data_science` | Data Science | 数据科学 |
| `networks` | Networks & Communications | 网络与通信 |
| `systems` | Systems & Software | 系统与软件 |
| `security` | Information Security | 信息安全 |

Each element has multiple `TechDirection` subcategories. Venues (conferences/journals) are bound to tech elements via `VenueTechBinding`.

### 11-Phase Collection Pipeline

`CollectionOrchestrator` in `services/collect/orchestrator.py` executes:

1. **Phase 0**: Estimate task scale (count works per venue)
2. **Phase 1**: Execute venue sub-tasks (fetch works from OpenAlex)
3. **Phase 2**: Fetch author data
4. **Phase 3**: Fetch institution data
5. **Phase 4**: Normalize schools (RawInstitution → StdSchool)
6. **Phase 5**: Normalize authors (RawAuthor → StdAuthor)
7. **Phase 6**: Calculate tech belonging (AuthorTechBelong)
8. **Phase 7**: Sync to serving layer (StdAuthor → Talent)
9. **Phase 8**: Fetch selected works (top papers per author)
10. **Phase 9**: Update tech tags
11. **Phase 10**: Update school statistics
12. **Phase 11**: Build homepage statistics

### Backend Layered Architecture

1. **Endpoints**: Request handling, validation via Pydantic schemas
2. **Services**: Business logic, orchestration
3. **Repositories**: Database operations, query building
4. **Builders**: Transform raw data into domain objects (ETL pattern)
5. **Models**: SQLAlchemy ORM models

### Key Service Modules

| Module | Purpose |
|--------|---------|
| `services/collect/` | Task creation, venue execution, progress tracking |
| `services/sync/` | AuthorSync, SchoolSync, TechTagSync, ServingLayerOrchestrator |
| `services/normalizers/` | AuthorNormalizer, SchoolNormalizer, TechBelongCalculator |
| `services/common/cs_concepts.py` | CS background score calculation, filtering threshold |
| `services/data_fetchers.py` | WorkFetcher, AuthorFetcher, InstitutionFetcher |
| `services/collaboration_service.py` | Extract co-author relationships from RawWork |

### Frontend State Management

- **authStore** (`store/authStore.ts`): User authentication state
- **favoritesStore** (`store/favoritesStore.ts`): Favorites and talent pool state
- **settingsStore** (`store/settingsStore.ts`): Column configs, search templates
- **localStorage**: Persisted user preferences

### Database Naming Conventions

- Table naming: `{module}_{entity}` (e.g., `core_talent`, `iam_user_account`)
- Primary keys: `{entity}_id` (e.g., `talent_id`, `school_id`)
- Timestamps: `created_at`, `updated_at` via TimestampMixin

### Database Index Strategy (v1.3)

Performance indexes are created via migration `023_add_performance_indexes.py`.

**P0 Indexes (User-visible pages)**:
| Table | Index | Query Pattern |
|-------|-------|---------------|
| `core_talent` | `ix_core_talent_visible_school_role` | Filter by school + role |
| `core_talent` | `ix_core_talent_visible_cited_desc` | Sort by citations (PostgreSQL DESC) |
| `core_talent_tech_tag` | `ix_talent_tech_enabled_element` | Tech element page query |
| `core_talent_tech_tag` | `ix_talent_tech_enabled_direction` | Tech direction page query |
| `iam_favorite_talent` | `ix_favorite_user_active_created` | User favorites list |

**P1 Indexes (Collection tasks)**:
| Table | Index | Query Pattern |
|-------|-------|---------------|
| `raw_work` | `ix_raw_work_source_year` | Get works by venue + year |
| `raw_author` | `ix_raw_author_status_task` | Get pending authors by task |
| `raw_institution` | `ix_raw_inst_status_task` | Get pending institutions by task |

**PostgreSQL-specific features**:
- Descending indexes: `CREATE INDEX ... (column DESC)`
- Partial indexes: `CREATE INDEX ... WHERE condition`

**Verify indexes**: `python scripts/verify_indexes.py`

## API Conventions

- Base path: `/api/v1`
- Authentication: Bearer token in Authorization header
- Pagination: `page`, `page_size` query params
- Response format: JSON with consistent structure

## Key Files

| Purpose | Path |
|---------|------|
| Collection orchestrator | `backend/app/services/collect/orchestrator.py` |
| Serving layer sync | `backend/app/services/sync/orchestrator.py` |
| CS background filtering | `backend/app/services/common/cs_concepts.py` |
| Raw data models | `backend/app/models/raw_data.py` |
| Standardized models | `backend/app/models/standardized.py` |
| Serving models | `backend/app/models/talent.py`, `school.py` |
| Tech element model | `backend/app/models/tech_element.py` |
| API endpoints | `backend/app/api/v1/endpoints/` |
| Frontend pages | `frontend/src/pages/` |
| Frontend stores (Zustand) | `frontend/src/store/` |
| API client | `frontend/src/services/api.ts` |

## Git Workflow

- `main` - Production-ready code
- `feature/*` - Feature branches
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`

## Notes

- Both development and production use PostgreSQL
- Default admin: `admin` / `admin123`
- Frontend port: 5173, Backend port: 8003
- OpenAlex API: https://api.openalex.org
- Always use `--reload` flag when starting backend for development
