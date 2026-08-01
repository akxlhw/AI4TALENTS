# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

智能人才库 (AI4TALENTS) V5.0.0 — 面向招聘团队的多维度人才发现平台。

当前实现的人才数据源：
- **学术人才** (`academic` domain): 基于 OpenAlex 学术数据库，完整功能
- **开源人才** (`open_source` domain): 基于 GitHub API，完整功能
- **实验室人才** (`lab` domain): AI 实验室人才（ai-lab-talent-crawler skill + JSONL 导入）
- **竞赛人才** (`competition` domain): 竞赛选手与队伍（comp-talent-crawler skill，已接入 Codeforces/IOI/IMO/IPhO/ICPC）
- **行业人才** (`industry` domain): V5.0.0（后端已完成：三表模型 + JSONL 增量 upsert 导入 + 岗位 CRUD/人才浏览 API；数据由 smart-talent-sourcing skill 产出，设计文档见 `docs/v5.0.0/02-技术设计.md`）

## Tech Stack

### Backend
- Python 3.11
- FastAPI + Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x + Alembic (async)
- PostgreSQL 14+ with pgvector 扩展
- Redis (可选缓存层，支持降级)
- uv (依赖管理与运行)

### Frontend
- React 18 + TypeScript
- Vite
- Ant Design v5 + ECharts (图表)
- React Router v6
- TanStack React Query (服务器状态管理)
- Zustand (客户端状态: domain, auth, favorites)
- Vitest (单元测试)

## Common Commands

项目使用 Makefile 和 `uv` 管理后端依赖与命令。

```bash
# 安装依赖
make install                  # 安装前后端所有依赖
make install-backend          # uv sync --all-groups
make install-frontend         # npm install

# 开发服务器
make dev-backend              # uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
make dev-frontend             # npm run dev (port 2012)

# 测试
make test-backend             # uv run pytest --cov=app
cd backend && uv run pytest tests/test_models.py   # 单个测试文件
cd backend && uv run pytest -v --cov=app           # 带覆盖率
cd backend && uv run pytest -m "not slow"          # 跳过慢测试
cd frontend && npm run test                       # Vitest 单元测试

# 代码检查
make lint-backend             # uv run ruff check + black --check
make lint-frontend            # npm run lint
make lint-full                # CI gate: backend (ruff + black + mypy + architecture check) + frontend (lint + audit + build)
cd frontend && npm run type-check               # TypeScript standalone type check (no emit)
cd frontend && npm run format                   # Prettier 格式化
cd frontend && npm run format:check             # Prettier 格式检查
cd frontend && npm run build                    # Production build (runs tsc -b first)

# 数据库
make migrate                  # uv run alembic upgrade head
make migrate-create msg="xxx" # 创建新迁移
make migrate-rollback         # downgrade -1
make pipeline                 # migrate + seed (一步到位)

# 数据采集与同步
make seed                     # 初始化种子数据
make sync                     # 运行 OpenAlex 同步
make sync-test                # 测试 OpenAlex API 连接

# Docker
make docker-up                # 启动所有服务 (docker-compose up -d)
make docker-down              # 停止所有服务
make docker-logs              # 查看日志

# 数据初始化与维护 (backend/scripts/)
#   scripts/data/     — 数据初始化 (init_system, seed_tech_domains, generate_embeddings)
#   scripts/fix/      — 数据修复 (refresh_stats, dedup_schools)
#   scripts/ops/      — 运维工具 (verify_indexes, db_health_check)
#   scripts/collect/  — 采集相关辅助脚本
cd backend && uv run python scripts/data/init_system.py --force    # 重置系统
cd backend && uv run python scripts/data/seed_tech_domains.py      # 初始化六大技术领域
cd backend && uv run python scripts/data/generate_embeddings.py    # 生成向量嵌入
cd backend && uv run python scripts/fix/refresh_stats.py           # 刷新统计
cd backend && uv run python scripts/ops/verify_indexes.py          # 验证索引
```

## Architecture

### Application Entry & Config

```
backend/app/
├── main.py              # FastAPI app, lifespan (cache init, proxy config load), middleware chain
├── api_router.py        # 聚合所有 domain router 到 /api/v1 下
├── model_registry.py    # 所有 SQLAlchemy ORM 模型的中央导入点 (Alembic 用此发现模型)
├── core/
│   ├── config.py        # pydantic-settings BaseSettings, 所有环境变量 (DB/Redis/LLM/JWT/OpenAlex/GitHub)
│   ├── database.py      # async SQLAlchemy engine + session factory
│   ├── auth.py          # JWT 创建/验证, 密码哈希 (bcrypt), get_current_user 依赖
│   ├── exceptions.py    # 全局异常类 + FastAPI exception handlers
│   ├── cache.py         # Redis 客户端初始化
│   ├── logging_config.py
│   └── metrics.py       # Prometheus 指标定义
└── middleware/
    ├── metrics.py       # 请求计数/延迟中间件
    ├── rate_limit.py    # 可选限流中间件 (settings.RATE_LIMIT_ENABLED)
    └── request_logging.py
```

### Domain-Driven Backend Structure

后端按业务域组织，而非按技术层扁平划分：

```
backend/app/domains/
├── academic/          # 学术人才域 (核心)
│   ├── api/           # FastAPI routers (collect, search, talents, schools, jd_match, recommend, etc.)
│   ├── models/        # SQLAlchemy ORM models (raw_*, std_*, core_*)
│   ├── schemas/       # Pydantic DTOs
│   ├── repositories/  # 数据库操作层 (含 talent/ 子目录下的搜索/导出库)
│   ├── services/      # 业务逻辑
│   │   ├── collect/       # 12阶段采集流水线 (orchestrator.py + phase_*.py)
│   │   ├── common/        # CS背景分、HTTP客户端
│   │   ├── embedding/     # 向量嵌入服务
│   │   ├── jd_match/      # JD岗位匹配
│   │   ├── normalizers/   # 数据标准化
│   │   ├── recommend/     # 相似人才推荐
│   │   ├── search/        # 搜索服务
│   │   └── sync/          # 同步服务
│   ├── builders/      # 查询构建器 (search_builder, stat_builder)
│   └── constants/     # 枚举常量 (collect_task, countries, role_type)
├── open_source/       # 开源人才域 (v2.0)
│   ├── api/
│   ├── models/
│   ├── repositories/open_source/  # core.py (基础CRUD), advanced.py (扩展查询)
│   ├── schemas/
│   └── services/collectors/       # github_collector, sync_service
└── shared/            # 共享基础设施
    ├── api/           # auth, audit, health, metrics, permissions, system_config
    ├── models/        # base (TimestampMixin), enums, iam, audit, system_config
    ├── repositories/
    └── services/
        ├── cache/         # Redis 缓存 (cache_manager.py)
        ├── common/        # HTTP 客户端工厂、代理配置
        ├── llm/           # LLM 网关 (多提供商统一接口)
        ├── cache_service.py        # 缓存业务层 (域聚合键管理)
        ├── config_service.py       # 动态系统配置读写
        ├── audit_service.py
        └── user_service.py
```

**注意**: 旧版文档中提到的 `app/services/collect/orchestrator.py`、`app/models/raw_data.py` 等路径已不存在。所有代码现位于 `domains/` 下对应子目录中。

### Three-Layer Data Architecture (Academic Domain)

学术人才域保持三层数据模型：

| Layer | Tables | Purpose |
|-------|--------|---------|
| **Raw** | `raw_work`, `raw_author`, `raw_institution` | OpenAlex API 原始数据 |
| **Standardized** | `std_author`, `std_school` | 清洗标准化数据，含 CS score |
| **Serving** | `core_talent`, `core_school` | 面向用户的服务层数据 |

Data flows: Raw → Standardized (via Normalizers) → Serving (via Sync services)

**CS Background Filtering**: `services/common/cs_concepts.py` 计算作者的 CS 概念得分，仅 `cs_concepts_score >= 0.5` 的作者会被同步到 `core_talent`。

### 12-Phase Collection Pipeline

`domains/academic/services/collect/orchestrator.py` 执行：

1. **Phase 0**: 估算任务规模
2. **Phase 1**: 执行 venue 子任务 (获取 works)
3. **Phase 2**: 获取作者数据
4. **Phase 3**: 获取机构数据
5. **Phase 4**: 标准化学校 (RawInstitution → StdSchool)
6. **Phase 5**: 标准化作者 (RawAuthor → StdAuthor)
7. **Phase 6**: 计算技术归属 (AuthorTechBelong)
8. **Phase 7**: 同步到服务层 (StdAuthor → Talent)
9. **Phase 8**: 获取代表作品
10. **Phase 9**: 更新技术标签
11. **Phase 10**: 更新学校统计
12. **Phase 11**: 构建首页统计

### LLM Gateway (`domains/shared/services/llm/`)

统一多模型提供商接口：
- 支持 DeepSeek / OpenAI / 智谱 / 通义千问
- 对话模型与嵌入模型可分别配置
- 用于 JD 解析、岗位匹配、相似推荐

### Frontend Architecture

**状态管理分层**:
- **TanStack React Query**: 所有服务器状态（人才列表、搜索、收藏等）。缓存策略分层: static 30min, stats 5min, list 3min, detail 10min, realtime 30s。采集任务每 5s 轮询。
- **Zustand**: 三个 store — `domainStore` (领域切换+主题, 持久化到 localStorage), `authStore` (认证状态), `favoritesStore` (收藏列表)
- **React Contexts** (`AuthContext`, `FavoritesContext`): Zustand store 的兼容包装层，避免旧代码 breaking
- **localStorage**: 列配置 (`useColumnConfig`)、搜索模板 (`useSearchTemplates`)、auth token、领域偏好

**路由结构** (React Router v6):
- `/` → 根据 domain 分发到 AcademicHomePage 或 OpenSourcePage
- `/search-recommend` → 搜索+智能推荐 (三个 tab: search, jd-match, similar-recommend)
- `/talents/:id`, `/schools/:id` → 详情页
- `/opensource/*` → 开源领域页面 (首页、搜索、开发者详情、仓库列表/详情)
- `/admin` → 用户管理, `/system-config` → 系统配置 (采集/LLM/代理/GitHub)
- `/favorites`, `/profile` → 用户个人页
- 路由守卫: `ProtectedRoute` (需登录), `AdminRoute` (需管理员), `PublicRoute` (已登录则重定向)

**主题系统** (`frontend/src/theme/index.ts`):
- 平台中性底色 + 领域感知 token 的架构
- 每个领域有独立配色方案（学术: 深蓝 `#1E3A5F`，开源: 深灰绿 `#2D3748`）
- `applyDomainCssVars(domain)`: 运行时设置 CSS Variables + `data-domain` attribute
- `buildAntTheme(domain)`: 构建完整 Ant Design ThemeConfig (组件 tokens 随领域变化)

**API 客户端** (`frontend/src/services/api/`):
- 三层结构: `client.ts` (Axios 实例, 30s 超时, Bearer token 拦截器, 401 重定向) → `shared.ts` / `academic.ts` / `openSource.ts` (按域分模块) → `api.ts` (统一聚合导出)
- 前端 `.env` 中的 `VITE_API_URL` 控制 API 基地址；开发时通过 Vite proxy (`/api` → `localhost:8003`)

**类型定义**: `frontend/src/types/index.ts` — 单文件, 按版本分节 (v1.0 ~ v2.0), 涵盖所有 API 响应类型

### Infrastructure

- **deploy/**: `docker-compose.yml` (postgres:16-alpine + redis:7-alpine + backend + frontend), `init-db.sql` (uuid-ossp + pg_trgm 扩展), `.env.example`
- **Alembic 迁移**: `backend/migrations/` (非 `alembic/`)。`env.py` 从 `app.model_registry` 导入所有模型，实现自动模型发现——新增模型只需在 `model_registry.py` 中导入即可被 Alembic 识别
- **Windows 脚本**: `restart.bat` (终止进程→清理缓存→启动后端/前端), `stop.bat` (终止所有服务窗口)

### Database Conventions

- 表命名: `{module}_{entity}` (如 `core_talent`, `iam_user_account`)
- 主键: `{entity}_id` (如 `talent_id`, `school_id`)
- 时间戳: `created_at`, `updated_at` via `TimestampMixin`
- pgvector 扩展用于向量存储 (`core_talent_embedding`)

### API Conventions

- Base path: `/api/v1`
- Authentication: Bearer token in `Authorization` header
- Pagination: `page`, `page_size` query params
- 健康检查: `/api/v1/health`, `/ready`, `/live`
- 指标: `/api/v1/metrics` (Prometheus)

## Key Files

| Purpose | Path |
|---------|------|
| App 入口 + 生命周期 | `backend/app/main.py` |
| 系统配置 (所有环境变量) | `backend/app/core/config.py` |
| ORM 模型中央注册 | `backend/app/model_registry.py` |
| API 路由聚合 | `backend/app/api_router.py` |
| 采集流水线编排 | `backend/app/domains/academic/services/collect/orchestrator.py` |
| 同步服务 | `backend/app/domains/academic/services/sync/` |
| CS 背景过滤 | `backend/app/domains/academic/services/common/cs_concepts.py` |
| LLM 网关 | `backend/app/domains/shared/services/llm/llm_gateway.py` |
| 缓存服务 | `backend/app/domains/shared/services/cache_service.py` |
| HTTP 客户端工厂 | `backend/app/domains/shared/services/common/` |
| 前端 API 客户端 | `frontend/src/services/api/client.ts` |
| 前端类型定义 | `frontend/src/types/index.ts` |
| 前端主题系统 | `frontend/src/theme/index.ts` |
| 前端路由 + 守卫 | `frontend/src/App.tsx` |
| 前端布局 (顶栏+领域切换) | `frontend/src/layouts/MainLayout.tsx` |
| 前端 React Query hooks | `frontend/src/hooks/useQueries.ts` |

## Git Workflow

- `main` — 生产就绪代码
- `feature/*` — 功能分支
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`

## Environment Notes

- 开发与生产均使用 PostgreSQL（非 SQLite）
- 测试使用独立的 `talent_db_test` 数据库，运行后会清空表。首次运行测试前需创建：`CREATE DATABASE talent_db_test OWNER talent_user;`
- 默认管理员: `admin` / `admin123`
- 前端端口: 2012，后端端口: 8003
- 前端 `.env` 中 `VITE_API_URL` 留空则使用 Vite proxy；后端 `.env` 包含所有数据库/Redis/LLM 配置

### Windows 开发

Windows 默认无 `make` 命令。可用以下替代方案：

- **项目根目录 `restart.bat`**: 一键终止进程、清理缓存、启动后端 (port 8003) 和前端 (port 2012)
- **手动命令**: 参考 README.md 中 PowerShell 命令，或使用 WSL
- **后端依赖**: `cd backend && uv sync --all-groups` (需要单独安装 uv)
