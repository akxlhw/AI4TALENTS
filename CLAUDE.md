# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

智能人才库 (AI4TALENTS) V2.0.0 — 面向招聘团队的多维度人才发现平台。

当前实现的人才数据源：
- **学术人才** (`academic` domain): 基于 OpenAlex 学术数据库，完整功能
- **开源人才** (`opensource` domain): 基于 GitHub API，v2.0 新增
- **竞赛人才** (`competition`): 规划中
- **行业人才** (`industry`): 规划中

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
- Ant Design v5
- React Router v6
- TanStack React Query (服务器状态管理)
- Zustand (仅领域切换等极小范围客户端状态)
- Vitest (单元测试) + Playwright (E2E)

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
make test-backend             # uv run pytest
cd backend && uv run pytest tests/test_models.py   # 单个测试文件
cd backend && uv run pytest -v --cov=app           # 带覆盖率
cd backend && uv run pytest -m "not slow"          # 跳过慢测试
cd frontend && npm run test                       # Vitest 单元测试
npx playwright test                               # Playwright E2E

# 代码检查
make lint-backend             # uv run ruff check + black --check
make lint-frontend            # npm run lint
cd frontend && npm run type-check               # TypeScript 类型检查
cd frontend && npm run format                   # Prettier 格式化

# 数据库
make migrate                  # uv run alembic upgrade head
make migrate-create msg="xxx" # 创建新迁移
make migrate-rollback         # downgrade -1

# 数据初始化与维护 (backend/scripts/)
cd backend && uv run python scripts/data/init_system.py --force    # 重置系统
uv run python scripts/data/seed_tech_domains.py                    # 初始化六大技术领域
uv run python scripts/data/generate_embeddings.py                  # 生成向量嵌入
uv run python scripts/fix/refresh_stats.py                         # 刷新统计
uv run python scripts/ops/verify_indexes.py                        # 验证索引
```

## Architecture

### Domain-Driven Backend Structure

后端按业务域组织，而非按技术层扁平划分：

```
backend/app/domains/
├── academic/          # 学术人才域 (核心)
│   ├── api/           # FastAPI routers
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic DTOs
│   ├── repositories/  # 数据库操作层
│   └── services/      # 业务逻辑
│       ├── collect/       # 采集流水线
│       ├── common/        # CS背景分、HTTP客户端
│       ├── embedding/     # 向量嵌入服务
│       ├── jd_match/      # JD岗位匹配
│       ├── normalizers/   # 数据标准化
│       ├── recommend/     # 相似人才推荐
│       ├── search/        # 搜索服务
│       └── sync/          # 同步服务
├── open_source/       # 开源人才域 (v2.0)
│   └── api, models, repositories, services, schemas
└── shared/            # 共享基础设施
    ├── api/           # auth, audit, health, metrics, permissions, system_config
    ├── models/        # base, enums, iam, audit, system_config
    ├── repositories/
    └── services/
        ├── cache/         # Redis缓存抽象
        ├── common/        # HTTP客户端工厂、代理配置
        └── llm/           # LLM网关 (多提供商统一接口)
```

**重要**: 旧版文档中提到的 `app/services/collect/orchestrator.py`、`app/models/raw_data.py` 等路径已不存在。所有代码现位于 `domains/` 下对应子目录中。

### Three-Layer Data Architecture (Academic Domain)

学术人才域仍保持三层数据模型：

| Layer | Tables | Purpose |
|-------|--------|---------|
| **Raw** | `raw_work`, `raw_author`, `raw_institution` | OpenAlex API 原始数据 |
| **Standardized** | `std_author`, `std_school` | 清洗标准化数据，含 CS score |
| **Serving** | `core_talent`, `core_school` | 面向用户的服务层数据 |

Data flows: Raw → Standardized (via Normalizers) → Serving (via Sync services)

**CS Background Filtering**: `services/common/cs_concepts.py` 计算作者的 CS 概念得分，仅 `cs_concepts_score >= 0.5` 的作者会被同步到 `core_talent`。

### 12-Phase Collection Pipeline

`domains/academic/services/collect/collect_orchestrator.py` 执行：

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
- **TanStack React Query**: 所有服务器状态（人才列表、搜索、收藏等）
- **Zustand**: 仅 `domainStore` 存储当前激活的人才领域 (academic/opensource) 及主题切换
- **localStorage**: 持久化用户偏好（列配置、搜索模板等）

**主题系统** (`frontend/src/theme/`):
- 平台中性底色 + 领域感知 token 的架构
- 每个领域有独立配色方案（学术: 深蓝 `#1E3A5F`，开源: 深灰绿 `#2D3748`）
- 切换领域时通过 CSS Variables 全局生效

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
| API 路由聚合 | `backend/app/api_router.py` |
| 采集流水线 | `backend/app/domains/academic/services/collect/collect_orchestrator.py` |
| 同步服务 | `backend/app/domains/academic/services/sync/` |
| CS 背景过滤 | `backend/app/domains/academic/services/common/cs_concepts.py` |
| LLM 网关 | `backend/app/domains/shared/services/llm/llm_gateway.py` |
| 缓存服务 | `backend/app/domains/shared/services/cache/cache_service.py` |
| 前端 API 客户端 | `frontend/src/services/api/client.ts` |
| 前端主题系统 | `frontend/src/theme/index.ts` |
| 前端领域状态 | `frontend/src/stores/domainStore.ts` |

## Git Workflow

- `main` — 生产就绪代码
- `feature/*` — 功能分支
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`

## Environment Notes

- 开发与生产均使用 PostgreSQL（非 SQLite）
- 测试使用独立的 `talent_db_test` 数据库，运行后会清空表
- 默认管理员: `admin` / `admin123`
- 前端端口: 2012，后端端口: 8003
