# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-04-06

### Added

#### Architecture & Performance
- **PostgreSQL Performance Indexes**: Added 12 optimized indexes for user-visible pages and collection tasks
  - P0: `ix_core_talent_visible_school_role`, `ix_core_talent_visible_cited_desc` for talent list queries
  - P0: `ix_talent_tech_enabled_element`, `ix_talent_tech_enabled_direction` for tech element pages
  - P0: `ix_favorite_user_active_created` for user favorites
  - P1: `ix_raw_work_source_year`, `ix_raw_author_status_task`, `ix_raw_inst_status_task` for collection pipeline
- **Redis Cache Layer**: Full caching infrastructure with graceful degradation
  - Cache connection management with connection pooling
  - `CacheService` with get/set/delete/delete_pattern operations
  - TTL with random jitter to prevent cache avalanche
  - Cache invalidation on data changes
  - Health check integration
- **Cursor-Based Pagination**: Replaced OFFSET pagination for better deep-page performance
  - `get_list_by_cursor` in talent repository
  - Supports role_type, school_id filters
  - Next cursor encoding for seamless pagination
- **Bulk Sync Operations**: Optimized batch processing for data synchronization
  - `bulk_sync_schools` with single transaction upsert
  - `bulk_sync_authors` with CS score filtering
  - Returns `new_talents` list for downstream work fetching
- **Metrics Collection**: Prometheus-compatible metrics system
  - Counter, Gauge, Histogram metric types
  - `/api/v1/metrics` endpoint (Prometheus format)
  - `/api/v1/metrics/json` endpoint (JSON format)
  - HTTP request tracking with path normalization
- **Enhanced Health Check**: Comprehensive health monitoring
  - `/api/v1/health` - full health status with database and cache
  - `/api/v1/health/ready` - readiness probe for K8s
  - `/api/v1/health/live` - liveness probe

#### Frontend
- **React Query Integration**: Client-side caching and request deduplication
  - QueryClient setup with 5-minute stale time
  - API hooks using `useQuery` and `useMutation`
  - Automatic background refetching
  - Cache key management for tech elements
- **Query Client Provider**: Root-level query client configuration

#### Documentation
- v1.3 version plan with architecture upgrade roadmap
- Performance index verification script

### Changed

#### Backend
- Database configuration supports both SQLite (dev) and PostgreSQL (prod)
- Statistics endpoints utilize cache layer when available
- Collection pipeline triggers cache invalidation on completion

#### Frontend
- API service layer refactored to use React Query hooks
- Homepage data cached with automatic refresh

### Technical Details
- Backend tests: 320 passed (up from 249)
- Frontend E2E tests: 38 tests
- Cache hit latency: < 10ms
- Query performance improvement: 3-5x on indexed queries

## [1.2.2] - 2026-04-03

### Fixed
- Fixed SQLite database lock error when starting new collection task after cancelling/deleting previous task
  - Added retry mechanism with exponential backoff (0.5s, 1s, 2s) to repository upsert operations
  - Improved error handling in WorkFetcher to continue on individual record failures
  - Automatic transaction rollback and retry on "database is locked" errors

## [1.2.1] - 2026-04-03

### Fixed
- Fixed `AttributeError: 'dict' object has no attribute 'user_id'` in talent pool API
  - `require_user` dependency returns `dict`, not `UserAccount` ORM object
  - Updated `talent_pool.py` and `data_version.py` to use dict access `current_user["user_id"]`
- Fixed tech element page stats not updating when filtering by tech element
  - Added `professor_count` and `student_count` to `TechElementStatsResponse`
  - Added role-based statistics query in `get_element_stats` repository method
  - Frontend now updates all stats fields when tech element changes

## [1.2.0] - 2026-03-30

### Added

#### Backend
- Rate limiting middleware (100 req/min per API) for system stability
- Structured JSON logging with `python-json-logger`
- Request tracking middleware with `X-Request-ID` header
- Request logging middleware for response time and status tracking
- Global exception handling with unified error response format
- New tests for search and talents API endpoints

#### Frontend
- Zustand stores for state management (`authStore`, `favoritesStore`, `settingsStore`)
- Reusable common components (`PageHeader`, `FilterSection`, `SelectionActions`)
- Constants directory with extracted common constants

#### Documentation
- Production deployment guide (`docs/部署文档.md`)

### Changed

#### Frontend
- Cleaned up deprecated `*Refactored.tsx` files
- Unified type definitions (all ID types are now `number`)
- Extracted inline types to `types/index.ts`
- Improved code reusability with common components

### Fixed
- Test environment rate limiting interference (disabled in tests)

### Technical Details
- Backend tests increased from 222 to 249 passed
- Improved logging with JSON structured output
- Enhanced request tracing for debugging

## [1.1.0] - 2026-03-30

### Added

#### Features
- **Tech Element Perspective**: New main navigation for business departments to view talent by technical domain
- **Country School Perspective**: New main navigation for platform teams to view talent coverage
- **Homepage Enhancement**: Dual perspective summary cards, hot tech element tags, top countries/schools
- **Advanced Search**: Filter by tech element, tech direction, region, country, role type, graduation status
- **Talent Detail Enhancement**: Tech tags, recruitment summary, data completeness, pending items
- **Favorites & Talent Pool**: Light operation workflow with follow-up status tracking
- **Collection Configuration**: Venue management, task scheduling, execution progress tracking
- **Data Version Control**: Version management, publish/rollback operations
- **Data Quality Dashboard**: Quality summary, manual correction workflow

#### Data Architecture
- **Three-Layer Data Model**: Raw → Standardized → Serving architecture
- **Raw Data Layer**: `RawWork`, `RawAuthor`, `RawInstitution` models
- **Standardized Layer**: `StdAuthor`, `StdSchool`, `SchoolNameAlias` models
- **Serving Layer**: `core_talent`, `core_school` models
- **Venue Configuration**: `config_venue`, `config_venue_tech_binding` tables

#### Backend
- 11-phase collection pipeline with orchestrated execution
- Role auto-detection based on papers/citations/h-index
- CS background score filtering at standardization layer
- Author tech belonging tracking (`AuthorTechBelong` model)
- Venue sub-task granularity for collection progress

#### Frontend
- 6 main navigation pages with responsive design
- Real-time collection task progress display
- Multi-filter support with URL state persistence
- Column configuration persistence

### Changed
- Navigation architecture from school-focused to dual-perspective
- Permission model expanded to 3 dimensions (school/country/tech element)
- Search from basic to advanced with 10+ filter options

### Fixed
- 23 Change Requests (CR-01 to CR-24) implemented
- 10 Task Packages (TP1 to TP10) completed

## [1.0.0] - 2026-01-15

### Added
- Initial MVP release
- Basic talent browsing by country/school
- Keyword search functionality
- School detail pages
- Talent list and detail pages
- Basic user authentication and authorization
- School-based permission control
- Data import from OpenAlex API

### Technical Stack
- Backend: Python 3.11 + FastAPI + SQLAlchemy + Alembic
- Frontend: React 18 + TypeScript + Vite + Ant Design v5
- Database: SQLite (dev) / PostgreSQL (prod)

[1.3.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/akxlhw/AI4TALENTS/releases/tag/v1.0.0
