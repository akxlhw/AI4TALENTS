# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.2.0]: https://github.com/your-org/talent-platform/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/your-org/talent-platform/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/your-org/talent-platform/releases/tag/v1.0.0
