> 本文件面向 AI 编程助手。如果你正在阅读此文件，说明你对本项目一无所知——本文将告诉你需要了解的一切。

---

# 智能人才库 (AI4TALENTS) 项目指南

## 项目概述

**智能人才库（AI4TALENTS）** 是一套面向招聘团队的多维度人才发现平台。

- **当前版本**：**V3.0.0**（以 `backend/pyproject.toml`、`frontend/package.json`、`backend/app/core/config.py` 中的版本号为准）。
- **项目定位**：整合公开学术数据与开源社区数据，帮助招聘团队发现、筛选、对比和管理高端技术人才。
- **已实现的人才数据源**：
  - **学术人才**（`domains/academic/`）：基于 OpenAlex 学术数据库，功能完整。
  - **开源人才**（`domains/open_source/`）：基于 GitHub API，功能完整。
  - **实验室人才**（`domains/lab/`）：AI 实验室人才（如 Stanford AI Lab、MIT CSAIL），通过 hermes agent 调用 `ai-lab-talent-crawler` skill 采集官网人员数据，产出 JSONL 由 `LabImportService` 导入。支持 hermes API 推送 + 管理员手动上传两种导入方式。独立 `lab_talent` 表（不复用 `core_talent`，因跨域隔离铁律）。
- **规划中的人才数据源**：竞赛人才、行业人才。

主要功能包括：学术/开源人才搜索与发现、人才画像查看、候选人筛选/排序/对比、重点人才导出、收藏与人才池管理、三维权限控制（学校/国家/技术要素）、采集任务管理、语义搜索、JD 岗位匹配、相似人才推荐、用户注册审批与审计日志等。

---

## 技术栈

### 后端

- **Python 3.11+**
- **FastAPI 0.115.0** — Web 框架
- **Pydantic v2 + pydantic-settings** — 配置与校验
- **SQLAlchemy 2.0.35 + Alembic 1.13.3** — 异步 ORM 与数据库迁移
- **asyncpg 0.29.0 + psycopg2-binary 2.9.9** — PostgreSQL 异步/同步驱动
- **PostgreSQL 16+** — 主数据库（开发与生产均使用 PostgreSQL，无 SQLite 降级）
- **pgvector** — PostgreSQL 向量扩展，用于语义搜索与人才推荐
- **Redis 5.2.0** — 可选缓存层，支持降级（无 Redis 时直接查库）
- **httpx 0.27.2 / aiohttp >=3.9.0** — 出站 HTTP 客户端（必须通过 `HttpClientFactory` 统一封装）
- **tenacity 9.0.0** — 重试策略
- **bcrypt 4.2.0 + PyJWT 2.9.0** — 认证
- **openai / tiktoken / numpy** — LLM 与嵌入相关
- **uv (Astral)** — Python 包管理与运行（取代 pip）

### 前端

- **React 18.3.1 + TypeScript 5.6.2**
- **Vite 8.0.10** — 构建工具
- **Ant Design v5.21.0 + @ant-design/icons** — UI 组件库
- **React Router v6.26.2** — 路由
- **Zustand 4.5.5** — 客户端状态管理
- **TanStack React Query v5.59.0** — 服务端状态管理与缓存
- **Axios 1.7.7** — HTTP 客户端
- **ECharts 6.1.0 + echarts-for-react** — 图表可视化
- **Vitest 4.1.5 + jsdom + @testing-library/react** — 单元测试
- **Playwright 1.58.2** — E2E 测试

### 基础设施

- **Docker & Docker Compose** — 容器化部署
- **Nginx** — 前端生产环境托管
- **GitHub Actions** — CI/CD
- **Pre-commit** — 本地提交前轻量架构检查
- **Prometheus** — 指标采集（`/api/v1/metrics`）

---

## 项目结构

```
talent-platform/
├── backend/                    # 后端服务
│   ├── app/                   # 应用代码
│   │   ├── api_router.py      # FastAPI 路由注册表（聚合所有域路由到 /api/v1）
│   │   ├── model_registry.py  # Alembic 模型注册表（聚合所有域模型）
│   │   ├── main.py            # FastAPI 入口与生命周期管理
│   │   ├── core/              # 核心基础设施
│   │   │   ├── config.py      # 环境变量配置（pydantic-settings）
│   │   │   ├── database.py    # 异步 SQLAlchemy engine / session factory
│   │   │   ├── auth.py        # JWT、密码哈希、当前用户依赖
│   │   │   ├── exceptions.py  # 全局异常类与异常处理器
│   │   │   ├── cache.py       # Redis 客户端初始化
│   │   │   ├── logging_config.py
│   │   │   └── metrics.py     # Prometheus 指标定义
│   │   ├── middleware/        # 限流、请求日志、指标采集
│   │   └── domains/           # 领域驱动核心
│   │       ├── academic/      # 学术人才域
│   │       │   ├── api/       # FastAPI routers（collect, countries, data_version, embeddings, favorites, genealogy, homepage, jd_match, overview, recommend, schools, search, talent_pool, talents, tech_domain, venue）
│   │       │   ├── builders/  # 查询构建器（search_builder, stat_builder）
│   │       │   ├── constants/ # 域内常量
│   │       │   ├── models/    # SQLAlchemy ORM 模型
│   │       │   ├── repositories/  # 数据访问层（含 talent/ 子目录）
│   │       │   ├── schemas/   # Pydantic DTO
│   │       │   └── services/  # 业务逻辑层
│   │       │       ├── collect/       # 12 阶段采集流水线
│   │       │       ├── common/        # CS 背景分、公共工具
│   │       │       ├── embedding/     # 向量嵌入服务
│   │       │       ├── jd_match/      # JD 岗位匹配
│   │       │       ├── normalizers/   # 数据标准化
│   │       │       ├── recommend/     # 相似人才推荐
│   │       │       ├── search/        # 搜索服务
│   │       │       └── sync/          # 同步服务
│   │       ├── open_source/   # 开源人才域
│   │       │   ├── api/
│   │       │   ├── models/
│   │       │   ├── repositories/open_source/
│   │       │   ├── schemas/
│   │       │   └── services/  # 含 collectors/（github_collector, sync_service）
│   │       ├── lab/           # AI 实验室人才域（JSONL 导入，独立 lab_talent 表）
│   │       │   ├── api/       # import_endpoint, talents, stats
│   │       │   ├── constants/ # role_mapping（role_section → role_type + academic_level）
│   │       │   ├── models/    # lab_talent
│   │       │   ├── repositories/
│   │       │   ├── schemas/
│   │       │   └── services/  # lab_import_service, lab_talent_service, lab_stats_service
│   │       └── shared/        # 共享域
│   │           ├── api/       # auth, audit, health, metrics, permissions, privacy, suggestion, system_config
│   │           ├── models/    # base, enums, iam, audit, system_config, suggestion
│   │           ├── repositories/
│   │           └── services/  # cache, common/http_client, llm, config_service, audit_service, user_service 等
│   ├── migrations/            # Alembic 数据库迁移脚本
│   ├── tests/                 # pytest 测试
│   ├── scripts/               # 运维与数据脚本
│   │   ├── collect/           # 采集相关脚本
│   │   ├── data/              # 数据/种子脚本
│   │   ├── fix/               # 修复/维护脚本
│   │   └── ops/               # 运维脚本（mypy_gate.py, verify_indexes.py 等）
│   ├── pyproject.toml         # Python 依赖与工具配置
│   ├── uv.lock                # uv 锁定文件
│   ├── alembic.ini            # Alembic 配置
│   └── pytest.ini             # pytest 配置（运行时优先于 pyproject.toml 中的 pytest 配置）
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── App.tsx            # 路由定义与路由守卫
│   │   ├── pages/             # 页面级组件
│   │   ├── components/        # 可复用组件
│   │   ├── contexts/          # React Context（AuthContext, FavoritesContext，Zustand 的兼容包装）
│   │   ├── services/          # API 客户端
│   │   │   ├── api.ts         # 聚合导出
│   │   │   └── api/           # 域拆分模块（client.ts, shared.ts, academic.ts, openSource.ts, lab.ts）
│   │   ├── stores/            # Zustand 状态管理（authStore, domainStore, favoritesStore）
│   │   ├── hooks/             # 自定义 React Hooks
│   │   ├── types/             # TypeScript 类型定义
│   │   ├── constants/         # 前端常量
│   │   ├── utils/             # 工具函数
│   │   ├── theme/             # 主题配置
│   │   └── test/setup.ts      # Vitest 测试初始化
│   ├── tests/                 # Playwright E2E 测试（*.spec.ts）
│   ├── package.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   ├── eslint.config.js
│   └── .prettierrc
├── deploy/                     # 部署配置
│   ├── docker-compose.yml
│   ├── init-db.sql             # 数据库初始化脚本（uuid-ossp + pg_trgm）
│   ├── schema.sql
│   └── .env.example
├── docs/                       # 项目文档
├── outputs/                    # 输出/日志（gitignored）
├── scripts/                    # 根级脚本
├── Makefile                    # 统一命令入口
└── .github/workflows/ci.yml    # GitHub Actions CI 配置
```

---

## 构建与运行命令

项目使用 **Makefile** 作为统一命令入口。Windows 环境无 `make` 时，可参照 Makefile 中的命令手动执行。

### 安装依赖

```bash
make install              # 安装前后端全部依赖（backend: uv sync --all-groups; frontend: npm install）
make install-backend      # 仅安装后端依赖
make install-frontend     # 仅安装前端依赖
```

### 开发启动

```bash
make dev-backend          # 启动后端开发服务器（uvicorn，端口 8003，--reload，host 0.0.0.0）
make dev-frontend         # 启动前端开发服务器（vite，端口 2012）
make dev                  # docker-compose up（全栈容器模式，前台运行）
```

### 测试

```bash
make test                 # 运行前后端全部测试（后端默认跳过 slow 标记的测试）
make test-backend         # uv run pytest --cov=app --cov-report=term-missing
make test-frontend        # npm run test（Vitest）
```

### 代码检查

```bash
make lint                 # 前后端基础检查（ruff + black --check + eslint）
make lint-backend         # ruff check + black --check
make lint-backend-full    # ruff + black + mypy gate + architecture check（与 CI 一致）
make lint-frontend        # npm run lint
make lint-frontend-full   # lint + audit + build（与 CI 一致）
make lint-full            # 前后端完整检查（与 CI 一致）
```

### 数据库

```bash
make migrate              # 执行 Alembic 升级到最新版本
make migrate-create       # 创建新迁移（需传 msg="描述"）
make migrate-rollback     # 回滚一次迁移
make seed                 # 初始化种子数据（scripts/data/init_system.py --force）
make pipeline             # migrate + seed
```

### Docker

```bash
make docker-up            # docker-compose up -d
make docker-down          # docker-compose down
make docker-logs          # docker-compose logs -f
```

### 访问地址

- 前端: http://localhost:2012
- 后端 API: http://localhost:8003
- API 文档 (Swagger UI): http://localhost:8003/docs
- API 文档 (ReDoc): http://localhost:8003/redoc
- 默认账号: `admin` / `admin123`

---

## 架构组织原则

### 跨域隔离（铁律）

- **`domains/academic/`、`domains/open_source/`、`domains/lab/` 三个业务域之间不得互相导入内部模块**
- **`domains/shared/` 不得导入任何业务域内部模块**（`models.enums` 除外）
- **各域仅可通过 `domains/shared/` 和 `app/core/` 共享能力**
- 违反此规则会导致 CI 构建失败（`scripts/check_architecture.py` 零容忍）

### 目录放置规则

| 代码类型 | 应放置位置 | 禁止放置位置 |
|----------|-----------|-------------|
| 学术域 API 路由 | `domains/academic/api/` | `app/api/v1/endpoints/`（已废弃） |
| 学术域模型 | `domains/academic/models/` | `app/models/`（已废弃） |
| 学术域 Service | `domains/academic/services/` | `app/services/`（已废弃） |
| 学术域 Repository | `domains/academic/repositories/` | `app/repositories/`（已废弃） |
| 学术域常量 | `domains/academic/constants/` | `app/constants/`（已废弃） |
| 共享基础设施 | `app/core/` | 任何 domain 内部 |
| 中间件 | `app/middleware/` | 任何 domain 内部 |
| 全局路由注册 | `app/api_router.py` | 任何其他位置 |
| 全局模型注册 | `app/model_registry.py` | 任何其他位置 |

### Endpoint 分层导入铁律

`api/` 下的 Endpoint 文件只能看到 Service 层，禁止直接触碰 Repository、Collector、底层 Client、LLM 网关等基础设施。

**Endpoint 允许直接 import**：
- 同域 Service
- shared Service
- 任意 schemas
- shared enums
- `app.core.*`
- 第三方库

**Endpoint 禁止直接 import**：
- `*Repository`
- `*Collector`
- `LLMGateway`
- `*EmbeddingService`
- `GitHubClient` / `OpenAlexClient`
- `AsyncSessionLocal`
- 同域 `models/`
- 同域 `builders/`
- `CollectionOrchestrator`

### HTTP 客户端统一规则

系统所有出站 HTTP 请求必须统一通过 `HttpClientFactory` 创建和管理，禁止直接导入或使用 `httpx`、`aiohttp`、`requests` 等底层 HTTP 客户端库。

- 正确做法：`HttpClientFactory.create_client_for_url(target_url, timeout=...)`
- 禁止做法：`import httpx`、`from aiohttp import ClientSession` 等
- 例外文件（已基线化）：`domains/shared/services/common/http_client.py`、`domains/shared/services/github_client.py`、`domains/shared/services/openalex_client.py`、`domains/shared/services/common/data_fetchers.py`、`domains/shared/api/system_config.py`

### 三层数据架构（学术域）

| 层级 | 代表表 | 作用 |
|------|--------|------|
| **原始层 (Raw)** | `raw_work`, `raw_author`, `raw_institution` | OpenAlex API 原始数据 |
| **标准化层 (Standardized)** | `std_author`, `std_school` | 清洗后的数据，含 CS 分数 |
| **服务层 (Serving)** | `core_talent`, `core_school` | 面向用户的业务数据 |

数据流向：Raw → Standardized（通过 Normalizers）→ Serving（通过 Sync services）

**CS 背景过滤**：在 Standardized → Serving 阶段，仅 `cs_concepts_score >= 0.5` 的作者会被同步到 Talent 表。配置见 `domains/academic/services/common/cs_concepts.py`。

### 12 阶段采集流水线

`CollectionOrchestrator` (`domains/academic/services/collect/orchestrator.py`) 执行完整采集：

1. Phase 0: 估算任务规模
2. Phase 1: 执行 Venue 子任务（获取论文）
3. Phase 2: 获取作者数据
4. Phase 3: 获取机构数据
5. Phase 4: 标准化学校（RawInstitution → StdSchool）
6. Phase 5: 标准化作者（RawAuthor → StdAuthor）
7. Phase 6: 计算技术归属（AuthorTechBelong）
8. Phase 7: 同步到服务层（StdAuthor → Talent）
9. Phase 8: 获取精选论文
10. Phase 9: 更新技术标签
11. Phase 10: 更新学校统计
12. Phase 11: 构建首页统计

### 六大技术要素

| 编码 | 英文名 | 中文名 |
|------|--------|--------|
| `ai` | Artificial Intelligence | 人工智能 |
| `robotics` | Robotics | 机器人 |
| `data_science` | Data Science | 数据科学 |
| `networks` | Networks & Communications | 网络与通信 |
| `systems` | Systems & Software | 系统与软件 |
| `security` | Information Security | 信息安全 |

---

## 代码风格指南

### Python（后端）

- **格式化**: Black，`line-length = 100`
- **Lint**: Ruff，目标 Python 3.11
  - 启用规则: E, W, F, I, B, C4, UP
  - 忽略: E501（Black 已处理）、B008、UP017、UP038
- **类型检查**: mypy，`disallow_untyped_defs = true`
  - `migrations/` 与 `tests/` 被排除
  - CI 使用 **mypy gate** (`scripts/ops/mypy_gate.py`) 与基线文件 `.mypy_baseline.txt` 对比，新增类型错误会导致构建失败
  - 基线再生命令：`cd backend && uv run python scripts/ops/mypy_gate.py --regenerate`
- **导入排序**: Ruff 内置 isort 规则处理

### TypeScript / React（前端）

- **Lint**: ESLint（`typescript-eslint` + `react-hooks` + `react-refresh`）
  - `@typescript-eslint/no-explicit-any`: `off`
  - `@typescript-eslint/no-unused-vars`: 允许 `_` 前缀的未使用变量
  - `no-case-declarations`: `off`
- **格式化**: Prettier
  - `semi: false`, `singleQuote: true`, `trailingComma: es5`
  - `tabWidth: 2`, `printWidth: 100`, `endOfLine: lf`
- **TypeScript**: `strict: true`，启用 `noUnusedLocals` / `noUnusedParameters`
- **路径别名**: `@/` 映射到 `src/`

---

## 测试策略

### 后端测试

- **框架**: pytest + pytest-asyncio + pytest-cov + httpx (AsyncClient)
- **测试数据库**: 必须使用独立的 PostgreSQL 测试库（默认 `talent_db_test`，配置在 `tests/conftest.py`）。每个测试函数结束后会 `TRUNCATE` 所有表（首次运行会 `DROP` 后重建）。**切勿将 `TEST_DATABASE_URL` 指向生产数据库！**
- **启动前准备**:
  ```bash
  psql -U postgres -c "CREATE DATABASE talent_db_test OWNER talent_user;"
  ```
- **Fixture 核心** (`tests/conftest.py`):
  - `test_engine` — 函数级，创建/销毁所有表，自动处理 pgvector 扩展
  - `test_session` — 函数级，异步 Session
  - `client` — 函数级，覆盖 `get_async_session` 依赖的 HTTP 测试客户端
  - `sample_talent`, `sample_tech_domain`, `sample_venue`, `full_setup` — 常用测试数据
  - `test_user`, `mock_admin_user`, `mock_normal_user` — 认证相关
- **测试标记**:
  - `unit` — 单元测试
  - `integration` — 集成测试
  - `e2e` — 端到端测试
  - `slow` — 慢速测试（默认被跳过，需显式运行）
  - `requires_pgvector` — 需要 pgvector 扩展（不可用时自动跳过）
- **运行命令**:
  ```bash
  cd backend
  uv run pytest                  # 运行所有非 slow 测试
  uv run pytest -v --cov=app     # 带覆盖率
  uv run pytest -m "not slow"    # 跳过慢速（默认行为已在 pytest.ini 中配置）
  ```

### 前端测试

- **单元测试**: Vitest + jsdom + @testing-library/react
  - 测试文件: `src/**/*.test.ts`, `src/**/*.test.tsx`
  - Setup: `src/test/setup.ts`
  - 命令: `npm run test` / `npm run test:watch`
- **E2E 测试**: Playwright
  - 测试目录: `frontend/tests/`（`*.spec.ts`）
  - 仅 Chromium 浏览器
  - 开发环境复用已有服务器 (`reuseExistingServer: true`)
  - 命令:
    ```bash
    cd frontend
    npx playwright test          # 运行全部
    npx playwright test --ui     # UI 模式
    ```

---

## CI/CD

GitHub Actions 工作流 `.github/workflows/ci.yml`：

1. **backend-test** — 在 Ubuntu 上启动 PostgreSQL 15 + pgvector 服务，运行常规测试与慢速测试
2. **backend-lint** — 运行 mypy gate 与架构合规检查
3. **frontend-lint** — 安装 Node 20 依赖，执行 ESLint、npm audit、Vitest 单元测试、生产构建

### 架构合规检查

项目已配置 `backend/scripts/check_architecture.py`，在每次 PR 时自动扫描三层规则：

```bash
# 本地检查
cd backend && uv run python scripts/check_architecture.py

# 更新基线（修复历史债务后执行）
cd backend && uv run python scripts/check_architecture.py --update-baseline
```

该脚本执行以下检查：
1. **跨域依赖检查（零容忍，无基线）**：`shared/` 禁止导入业务域
2. **Endpoint 分层检查（基线容忍）**：`domains/*/api/*.py` 禁止直接导入底层
3. **HTTP 客户端统一检查（基线容忍）**：`app/**/*.py` 禁止直接导入 `httpx`/`aiohttp`/`requests`

---

## 部署流程

### Docker Compose（推荐）

```bash
make docker-up      # 启动所有服务
make docker-logs    # 查看日志
make docker-down    # 停止服务
```

服务组成（见 `deploy/docker-compose.yml`）：
- `postgres` — PostgreSQL 16-alpine（含 init-db.sql 初始化）
- `redis` — Redis 7-alpine（可选，带 `production` profile）
- `backend` — FastAPI（端口 8000，开发模式带 `--reload`）
- `frontend` — Vite dev server（端口 2012）

### 本地开发（非 Docker）

```bash
# 1. 安装依赖
make install

# 2. 配置环境变量
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. 启动数据库
cd deploy && docker-compose up -d postgres

# 4. 运行迁移
make migrate

# 5. 启动后端（终端1）
make dev-backend

# 6. 启动前端（终端2）
make dev-frontend
```

### 容器构建说明

- **后端 Dockerfile**: 基于 `python:3.11-slim`，使用 `uv` 安装依赖，`uv sync --frozen --no-dev`，非 root 用户运行，暴露 8000 端口
- **前端 Dockerfile**: 多阶段构建（development → build → production/nginx）

---

## 环境变量与配置

### 后端关键配置（`backend/.env`）

| 变量 | 说明 | 典型值 |
|------|------|--------|
| `DATABASE_URL` | 异步数据库连接 | `postgresql+asyncpg://...` |
| `DATABASE_SYNC_URL` | 同步数据库连接（用于 Alembic 等） | `postgresql://...` |
| `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_HOURS` / `REFRESH_TOKEN_EXPIRE_DAYS` | JWT 认证 | HS256, 8h, 7d |
| `CORS_ORIGINS` | 跨域来源 | `["http://localhost:2012"]`（开发） |
| `REDIS_ENABLED` / `REDIS_URL` / `REDIS_PASSWORD` / `REDIS_MAX_CONNECTIONS` | Redis 缓存开关 | `false`（开发默认关闭） |
| `LLM_ENABLED` / `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_API_BASE` / `LLM_MODEL` / `LLM_EMBEDDING_MODEL` | LLM 功能开关 | `false`, `deepseek` |
| `LLM_TIMEOUT` / `LLM_MAX_RETRIES` / `LLM_ENABLE_FALLBACK` / `LLM_MAX_BATCH_SIZE` | LLM 高级参数 | `30.0`, `3`, `false`, `16` |
| `EMBEDDING_DIMENSION` / `EMBEDDING_BATCH_SIZE` | 向量维度 | `1536`, `100` |
| `SEARCH_DEFAULT_MODE` / `SEARCH_ENABLE_SEMANTIC` | 默认搜索模式 | `keyword`（可选 fulltext/semantic/hybrid） |
| `SEARCH_SEMANTIC_THRESHOLD` / `SEARCH_PRECISE_THRESHOLD` / `SEARCH_SIMILAR_THRESHOLD_MIN` | 搜索阈值 | `0.5`, `0.95`, `0.7` |
| `SEARCH_RRF_CONSTANT` / `SEARCH_HYBRID_EXTENDED_FACTOR` | 混合搜索参数 | `60`, `3` |
| `RECOMMEND_SIMILARITY_THRESHOLD` / `RECOMMEND_TAG_WEIGHT` / `RECOMMEND_RESEARCH_WEIGHT` | 推荐阈值 | `0.6`, `0.5`, `0.5` |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | 限流开关 | `false`（开发） |
| `CIRCUIT_BREAKER_ENABLED` / `CIRCUIT_BREAKER_FAILURE_THRESHOLD` / `CIRCUIT_BREAKER_RECOVERY_TIMEOUT` / `CIRCUIT_BREAKER_WINDOW_SIZE` | 熔断器配置 | `true`, `5`, `30.0`, `10` |
| `GITHUB_TOKENS` / `GITHUB_BASE_URL` / `GITHUB_RATE_LIMIT` / `GITHUB_PER_PAGE` / `GITHUB_BATCH_SIZE` | GitHub API 配置（开源人才采集） | `ghp_xxx`, `https://api.github.com`, `5000`, `100`, `5` |
| `OPENALEX_BASE_URL` / `OPENALEX_EMAIL` / `OPENALEX_RATE_LIMIT` | OpenAlex API 配置 | `https://api.openalex.org` |
| `APP_NAME` / `APP_VERSION` / `ENVIRONMENT` / `DEBUG` | 应用基础配置 | 智能人才库 API, 3.0.0, development, false |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | 分页 | `20`, `100` |
| `BATCH_SIZE` / `SYNC_TIMEOUT` / `SYNC_COMMIT_BATCH_SIZE` | 批量处理 | `1000`, `3600`, `100` |
| `CACHE_DEFAULT_TTL` / `CACHE_KEY_PREFIX` | 缓存 | `300`, `ai4talents` |
| `JD_MATCH_WEIGHT_RESEARCH` / `JD_MATCH_WEIGHT_IMPACT` / `JD_MATCH_H_REF` | JD 匹配权重 | `0.8`, `0.2`, `100.0` |
| `HTTP_TIMEOUT_SHORT` / `HTTP_TIMEOUT_DEFAULT` | HTTP 超时 | `10.0`, `30.0` |
| `COLLECT_ERROR_MAX_LENGTH` | 采集错误日志最大长度 | `500` |

### 前端关键配置（`frontend/.env`）

| 变量 | 说明 | 典型值 |
|------|------|--------|
| `VITE_API_URL` | 后端 API 基础地址 | `http://localhost:8003` |

> 注意：前端环境变量必须以 `VITE_` 开头才能在代码中通过 `import.meta.env` 访问。

---

## API 规范

- **Base Path**: `/api/v1`
- **认证方式**: Bearer Token（`Authorization: Bearer <token>`）
- **分页参数**: `page`, `page_size`（Query 参数）
- **响应格式**: 统一 JSON 结构
- **静态文件**: `/uploads` — 上传文件托管
- **健康检查**:
  - `/api/v1/health` — 综合健康
  - `/ready` — 就绪探针
  - `/live` — 存活探针
- **指标**: `/api/v1/metrics` — Prometheus 格式指标

---

## 安全注意事项

1. **数据库隔离**: 测试数据库与生产数据库必须物理隔离。`conftest.py` 会在每个测试函数后删除所有表。
2. **JWT Secret**: 生产环境必须修改 `SECRET_KEY`，避免使用默认值。`config.py` 会在生产环境校验密钥长度和存在性，不满足则直接抛错。
3. **CORS**: 开发环境允许全部来源 (`["*"]`)，生产环境应限制为实际域名。`config.py` 会在生产环境强制拒绝 `*` 和 `localhost`。
4. **Rate Limiting**: 生产环境建议启用 (`RATE_LIMIT_ENABLED=true`)，默认 100 req/min 每用户/IP。
5. **代理配置**: v1.4.1 支持从数据库动态加载企业代理配置，用于内网部署。见 `app/main.py` 中的 `init_proxy_config()`。
6. **LLM API Key**: 生产环境需妥善保管，勿提交到版本控制。
7. **密码存储**: 使用 bcrypt 哈希，禁止明文存储。
8. **CORS Credentials**: 系统使用 JWT Token 放在 `Authorization` Header 中（非 Cookie），因此 `allow_credentials=False`。

---

## 关键文件速查

| 用途 | 路径 |
|------|------|
| 后端入口 + 生命周期 | `backend/app/main.py` |
| 环境变量配置 | `backend/app/core/config.py` |
| ORM 模型中央注册 | `backend/app/model_registry.py` |
| API 路由聚合 | `backend/app/api_router.py` |
| 采集流水线编排 | `backend/app/domains/academic/services/collect/orchestrator.py` |
| CS 背景过滤 | `backend/app/domains/academic/services/common/cs_concepts.py` |
| LLM 网关 | `backend/app/domains/shared/services/llm/llm_gateway.py` |
| HTTP 客户端工厂 | `backend/app/domains/shared/services/common/http_client.py` |
| 前端 API 客户端 | `frontend/src/services/api/client.ts` |
| 前端类型定义 | `frontend/src/types/index.ts` |
| 前端主题系统 | `frontend/src/theme/index.ts` |
| 前端路由 + 守卫 | `frontend/src/App.tsx` |

---

## 给 AI 助手的开发 Checklist

新增或修改代码前，请确认：

1. 该文件属于哪个业务域？→ 放入对应 `domains/xxx/` 子目录
2. 是否跨域共享？→ 放入 `domains/shared/`
3. 是否基础设施？→ 放入 `app/core/` 或 `app/middleware/`
4. 是否有对应的 `__init__.py` 导出？→ 确保上层可导入
5. Endpoint 是否只导入 Service，没有直接导入 Repository/Collector/LLMGateway/EmbeddingService？
6. 是否直接使用了 `httpx`/`aiohttp`/`requests`？→ 改为 `HttpClientFactory`
7. 是否跨域导入？→ 改为通过 shared 或 core 共享
8. 修改后是否运行了 `make lint-full` 或 CI 对应命令？
9. 修改了架构/配置/流程后，是否同步更新了本 `AGENTS.md` 与 `README.md`/`CLAUDE.md`？
