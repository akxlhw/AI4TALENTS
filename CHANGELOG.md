# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - TBD

### Planned

- 物化视图 Table 重复定义提取至 `models/materialized_views.py`
- Phase 10 DDL 越界修复：`REFRESH MATERIALIZED VIEW` 下沉至 `SchoolRepository`
- 并发刷新互斥锁：多采集任务竞争刷新锁问题
- Endpoint 层剩余架构违规清理

## [2.0.4] - 2026-05-25

### Added

- **物化视图韧性三重防护** (`phase_10_school_stats.py`, `homepage_repository.py`, `school_repository.py`)
  - `REFRESH MATERIALIZED VIEW CONCURRENTLY` 增加唯一索引存在性预检，缺失时自动降级为阻塞式刷新
  - 刷新操作增加 tenacity 指数退避重试（3 次，1-30s）+ `asyncio.wait_for` 300s 超时，防止无限挂起
  - 首页 Top 院校 / 国家查询增加物化视图不可用降级：先检测 `pg_matviews`，缺失时 fallback 到实时 `COUNT(*)` 子查询
  - 刷新成功后自动失效首页 Redis 缓存 `stats:home:highlights`
- **采集错误长度限制配置化** (`config.py`)
  - 新增 `COLLECT_ERROR_MAX_LENGTH: int = 500`，防止超长异常信息入库

### Fixed

- **P0: graduate_count 永远为 0** (`school_repository.py`, `base_talent_repository.py`, `api/schools.py`)
  - 字典键 `'graduated'` → `'graduate'`，修复后 graduate_count 正确统计
- **P0: 物化视图重复计数** (`99aed1b1b7e7` 迁移)
  - `UNION ALL` → `UNION`，避免同一人才通过多个 affiliation 字段被重复计数
- **Endpoint 层魔法数字集中化** (`homepage.py`)
  - 提取 `HIGHLIGHT_LIMITS` 常量，消除散落在代码中的 `limit=6/5/10` 魔法数字

## [2.0.3] - 2026-05-22

### Added

- **滑动窗口熔断器** (`circuit_breaker.py`) — 纯 Python 实现，无外部依赖
  - 三态: CLOSED → OPEN (连续 5 次失败 / 窗口 10 次中 5 次失败) → HALF_OPEN (冷却 30s)
  - 集成到 OpenAlex Client (`_make_request`) 和 GitHub Client (`_get`)
  - 4 项配置化: `CIRCUIT_BREAKER_ENABLED`, `FAILURE_THRESHOLD`, `RECOVERY_TIMEOUT`, `WINDOW_SIZE`
- **SystemRepository** (`system_repository.py`) + **SystemService** (`system_service.py`)
  - 封装 `SELECT 1` 健康检查，消除 API 层直接 SQL

### Fixed

- **P0: API 层跨层穿透** (`talents.py`)
  - `run_sync_background()` 直接创建 `AsyncSessionLocal` → 移至 `CollaborationService.run_background_sync()`
- **P0: API 层跨层穿透** (`health.py`)
  - 直接 `session.execute(text("SELECT 1"))` → 通过 `SystemService.health_check_db(session)`
- **Phase 0 estimation 0 重试** (`data_fetchers.py`)
  - `get_work_count_from_venue()` 添加 `@with_retry(max_attempts=3)`，失败静默返回 0

## [2.0.1] - TBD

### Planned — 技术债务偿还

- **Endpoint 层剩余 18 项违规**：`countries.py`、`favorites.py`、`homepage.py`、`jd_match.py`、`overview.py`、`recommend.py`、`schools.py`、`talents.py`、`talent_pool.py`、`tech_domain.py`、`venue.py`、`audit.py`、`auth.py`、`permissions.py`
- **模块体积超标**：`OpenSourceService`（1345行）拆分、`LLMGateway`（570行）拆分
- **魔法数字集中化**：`batch_size`、`per_page`、`max_pages` 等分散配置提取到各域 `constants/`
- **异常处理精细化**：替换过度宽泛的 `except Exception: HTTPException(500, ...)`
- **前端 Demo 页面重复代码**：提取通用 `DemoPlaceholderPage` 布局组件
- **前端性能优化**：定时器 cleanup、useMemo 缓存菜单数组、useEffect 依赖补全

## [2.0.0] - 2026-05-09

### Added

- 开源人才库基础骨架（`domains/open_source/` 域模块）
- 版本号统一升级至 2.0.0

### Changed

- **架构治理（Endpoint 分层）**：`search.py`、`collect.py`、`embeddings.py` 移除 13 项 Endpoint 层直接 Repository/LLMGateway 引用，改为通过 Service 层调用
- **模块拆分**：`TalentRepository`（1157行）拆分为 `BaseTalentRepository` / `TalentSearchRepository` / `TalentExportRepository`
- **前端大文件拆分**：`academic-search-page.tsx`（1166行）拆分为 SearchTab / JDMatchTab / RecommendTab 三个子组件
- **前端类型安全**：治理 21 处 `any` 类型滥用，统一使用 `unknown` + 类型守卫
- **状态管理统一**：`AuthContext` / `FavoritesContext` 从 Context API 迁移至 Zustand，消除不必要重渲染
- **CI 完善**：GitHub Actions 新增前端 Vitest 单元测试步骤

### Fixed

- **版本号同步**：统一 `CHANGELOG.md`、`README.md`、`pyproject.toml`、`package.json` 版本号为 2.0.0
- **安全修复**：移除 `jd_match.py` 中硬编码的 `user_id = 15`，未认证用户现在将收到 401 错误
- **架构一致性**：清理 `database.py` 中残留的 SQLite 降级代码，与文档声明保持一致
- **Makefile 修复**：`make test` 现在同时运行后端和前端测试
- **测试性能优化**：`conftest.py` 重构为全局 `_TABLES_INITIALIZED` 标记，首次建表后续 TRUNCATE，全量测试耗时从 ~25min 降至 ~9min
- **pgvector 测试支持**：修复测试数据库 pgvector 扩展检测逻辑，`requires_pgvector` 改为动态检测，10 个向量相关测试全部启用
- **测试稳定性**：修复 `test_cancel_embedding_no_task` 全局状态污染问题

## [1.4.2] - 2026-04-26

### Fixed

#### SQLAlchemy 查询修复
- 修复 `embedding_repository.py` 中布尔过滤器使用 `== True` 导致的类型错误
- 修复 `tech_domain_repository.py` 中 `is_enabled` 过滤器问题
- 修复 `talent_repository.py` 中 `is_visible` 过滤器问题

#### API 规范修复
- 为 `health.py`、`metrics.py`、`system_config.py` 端点添加 `response_model`
- 确保所有 API 返回符合 OpenAPI 规范的响应结构

#### 测试修复
- 修复 E2E 测试手动创建 `AsyncClient` 未使用测试数据库的问题
- 添加 `e2e_client` fixture 正确覆盖数据库依赖
- 修复 `test_recommend_service.py` 测试 fixtures

#### 代码质量
- 为使用原生 SQL 的 repository 添加 S608 安全文档注释
- 说明参数化查询和字段白名单等安全措施

### Technical Details

- 后端测试: 477 passed
- 提交: `6bddb40`

## [Unreleased]

## [1.5.0] - 2026-04-29

### Added

#### 前端主题系统
- **领域主题系统**: 基于六大技术领域的动态主题切换
  - 每个技术领域拥有独立的渐变色和视觉风格
  - 首页 Hero 区域根据当前领域动态变化
- **状态管理**: 新增 `domainStore` 跨页面状态管理
- **Demo 页面**: 新增竞赛、行业、开源三个演示页面

#### 登录页优化
- **背景图片**: 使用背景图片替代 CSS 渐变
- **毛玻璃效果**: 登录卡片采用 glassmorphism 设计

#### 架构治理
- **Endpoint 分层泄漏治理**: 将 Endpoint 层直接 session 操作从 74 处彻底消除至 0 处
  - 新增 `VenueService`、`CollectService`、`ConfigService`、`TalentService` 等 Service 层
  - `permissions.py`、`data_version.py`、`schools.py`、`talent_pool.py` 等 13 个模块接入 Service 层
- **Repository 统一化**: 推广 `BaseRepository` 基类至 `CollectTaskRepository`、`VenueRepository`

#### 文档规范
- **P0 文档修复**: README 版本号同步、文档路径修正、v1.4 功能清单补全
- **P1 文档修复**: `.env.example` 重写（补全 28 个缺失字段）、部署指南补充 Redis/LLM/向量嵌入章节
- **P2 文档修复**: 生产环境高级配置（日志轮转、连接池调优、备份策略）、前端 README 创建

### Fixed

- **院校机构显示不一致**: 修复 JD 匹配/推荐结果与人才详情页院校机构显示不一致问题
  - 为 `MatchResultItem`、`RecommendResultItem`、`SemanticSearchResult` 添加 `education_school_name` 和 `company_school_name` 字段
  - 更新搜索、推荐、JD 匹配服务填充新字段
  - 前端人才列表优先显示教育机构
- **代码质量 P0**: Pydantic Schema 字段描述补全（8 个文件、270+ 字段）
- **代码质量 P1**: Endpoint `response_model` 补全、`venue.py` summary/description 补全
- **代码质量 P2**: 裸 `dict` 返回统一为 Pydantic Response Model
- **采集任务**: 修复入库人才为 0 的问题
- **导入路径**: 修复 `TalentTechTag` 从 `app.models.talent` 迁移至 `app.models.tech_domain` 后的导入问题

## [1.4.1] - 2026-04-23

### Added

#### 企业内网部署支持
- **代理配置增强**: 支持 HTTP/HTTPS 代理配置，SSL 证书验证开关
- **no_proxy 功能**: 支持配置不走代理的内网地址
- **局域网访问**: 后端监听所有网卡，支持局域网 IP 访问
- **CORS 跨域修复**: 支持局域网前端访问后端 API

#### LLM 配置优化
- **对话/嵌入模型分离**: 独立的启用开关和配置
- **嵌入模型连接测试**: 支持测试嵌入模型连接状态
- **API base URL 规范化**: 自动移除末尾斜杠避免双斜杠问题
- **连接测试日志**: 添加关键配置和连接日志便于调试

#### 向量功能增强
- **运行时切换向量维度**: 自动处理数据库变更
- **配置化向量维度**: 适配不同嵌入模型 (1536/1024/768 等)

#### 数据采集改进
- **分离教育/公司机构**: 按发文数量选择主要机构显示
- **顶会顶刊快照**: 采集任务保存创建时的配置快照，避免历史记录被覆盖
- **CS 背景筛选阈值**: 提高至 0.7，提升人才质量

### Changed

#### UI/UX 优化
- 登录页面标题改为"顶尖优秀人才发现平台"
- 全局"学校"改为"院校机构"，更准确反映数据范围
- 人才列表优先显示教育/公司机构而非 legacy school
- LLM 配置页面布局优化，嵌入模型配置独立化

#### 代码重构
- `tech_element` 重命名为 `tech_domain`，语义更清晰
- 新增 `BaseRepository` 基类，减少重复代码
- 内聚院校机构显示逻辑到 Talent 模型

### Fixed

- 修复搜索页面翻页无响应问题
- 修复 `venue_id` 类型错误
- 修复代理配置未正确应用到所有 HTTP 客户端的问题
- 修复代理配置路由冲突问题
- 修复嵌入模型测试连接检查错误的启用开关
- 向量生成时不再强制要求嵌入 API Key
- 空 API Key 时跳过 Authorization header

### Technical Details

- 44 个提交 (v1.4.0..v1.4.1)
- 后端测试: 458+ tests
- 前端 E2E 测试: 4 test files

## [1.4.0] - 2026-04-17

### Added

#### 智能推荐与语义搜索
- **pgvector 向量嵌入支持**: 使用 pgvector 扩展存储人才向量嵌入，支持相似度检索
- **语义搜索**: 基于向量相似度的语义搜索，支持中英文查询
- **混合搜索**: 关键词搜索与语义搜索融合 (Reciprocal Rank Fusion)
- **自动搜索模式选择**: 前端自动选择最优搜索模式 (keyword/fulltext/semantic/hybrid)

#### JD 岗位匹配
- **LLM JD 解析**: 使用 DeepSeek/OpenAI 等 LLM 解析岗位描述，提取研究方向
- **智能匹配**: 基于研究方向匹配度排序候选人
- **匹配会话管理**: 保存 JD 匹配历史记录

#### 相似人才推荐
- **向量相似度推荐**: 基于人才画像向量推荐相似人才
- **标签相似度降级**: 无向量时基于技术标签相似度推荐
- **推荐原因说明**: 提供推荐理由（研究方向相似、教育背景相似等）

#### 数据模型
- **core_talent_embedding**: 人才向量嵌入表
- **jd_match_session**: JD 匹配会话表
- **jd_match_result**: JD 匹配结果表
- **sys_config**: 系统配置表（运行时配置）

#### 搜索增强
- **全文索引**: PostgreSQL tsvector + GIN 索引
- **多字段权重**: 姓名(A)、职位(B)、研究方向(C)、学校(D) 权重分级
- **高亮显示**: 搜索结果关键词高亮

#### LLM 基础设施
- **LLMGateway**: 统一 LLM API 封装，支持 DeepSeek/OpenAI/智谱/通义千问
- **重试机制**: 指数退避重试，超时处理
- **配置化**: 支持运行时切换 LLM 提供商和模型

### Changed

#### 搜索体验优化
- 搜索页面简化，自动选择最优搜索模式
- 移除手动搜索模式切换，提升用户体验
- 搜索结果显示匹配度分数和匹配原因

#### 数据采集优化
- 提高计算机科学背景筛选阈值至 0.7
- 分离教育机构和公司机构显示
- 采集任务保存创建时的顶会顶刊快照

#### UI 优化
- 登录页面标题改为"顶尖优秀人才发现平台"
- 搜索推荐页面"学校"改为"院校机构"
- 人才列表优先显示教育/公司机构而非 legacy school

### Fixed

- 修复搜索页面翻页无响应问题
- 修复 venue_id 类型错误
- 支持运行时切换向量维度，自动处理数据库变更
- 支持配置化向量维度，适配不同嵌入模型

### Technical Details

- 数据库迁移: 025~031 (7 个迁移文件)
- 新增依赖: openai, tiktoken, pgvector
- 后端测试: 458+ tests
- 前端 E2E 测试: 4 test files

### Migration Guide

1. 安装 pgvector 扩展:
   ```sql
   CREATE EXTENSION vector;
   ```

2. 配置 LLM (可选):
   ```env
   LLM_ENABLED=true
   LLM_PROVIDER=deepseek
   LLM_API_KEY=your-api-key
   ```

3. 生成向量嵌入:
   ```bash
   python scripts/generate_embeddings.py
   ```

## [1.3.2] - 2026-04-10

### Fixed

#### 合作网络同步
- 使用 FastAPI BackgroundTasks 替代手动线程管理，修复事件循环冲突错误

#### 测试配置
- 修复 TEST_DATABASE_URL 指向生产数据库导致测试误删数据的风险
- 测试数据库改为独立的 `talent_db_test`
- 默认跳过需要 CREATEDB 权限的迁移测试

#### E2E 测试
- 修复测试使用正确的 client fixture 以访问测试数据

### Added
- 添加 `scripts/create_test_db.py` 辅助创建测试数据库

### Documentation
- README 补充测试数据库创建说明和警告

## [1.3.1] - 2026-04-09

### Fixed

#### PostgreSQL 兼容性
- 批量同步时分批处理插入操作，避免 PostgreSQL 参数限制
- 移除 SQLite 兼容代码，清理 PostgreSQL 迁移遗留
- 修复错误迁移删除后的 schema 遗留问题
- 修复批量同步学者合作网络的事件循环错误

#### 数据采集
- 使用 `locations.source.id` 替代 `primary_location.source.id` 获取数据源
- 补充缺失的 OpenAlex Source ID 配置
- cancel_task 添加数据库锁重试机制
- 统一时间字段为 UTC 时区
- Phase 1 完成后立即更新 total_records
- 修复数据采集和初始化脚本问题

#### 缓存
- 采集任务完成后自动刷新首页缓存
- init_system.py 添加 Redis 缓存清理

#### 测试
- 补充 v1.3 版本测试覆盖 (+51 个测试用例)
- 修复 Playwright 选择器语法错误
- 改进前端测试登录函数的可靠性
- 修复前端测试文件缺少 expect 导入

### Changed
- 删除错误的迁移文件并补充完整性测试
- 清理废弃代码和冗余文件

### Documentation
- 添加 Windows 部署文档

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
- Initial release
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

[2.0.3]: https://github.com/akxlhw/AI4TALENTS/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/akxlhw/AI4TALENTS/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/akxlhw/AI4TALENTS/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.4.2...v2.0.0
[1.4.2]: https://github.com/akxlhw/AI4TALENTS/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/akxlhw/AI4TALENTS/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.3.2...v1.4.0
[1.3.2]: https://github.com/akxlhw/AI4TALENTS/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/akxlhw/AI4TALENTS/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.2...v1.3.0
[1.2.2]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/akxlhw/AI4TALENTS/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/akxlhw/AI4TALENTS/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/akxlhw/AI4TALENTS/releases/tag/v1.0.0
