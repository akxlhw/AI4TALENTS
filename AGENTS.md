# AGENTS.md

> 本文件面向 AI 编程助手。如果你正在阅读此文件，说明你对本项目一无所知——本文将告诉你需要了解的一切。

---

## 项目概述

**智能人才库（AI4TALENTS）** 是一套面向招聘团队的多维度人才发现平台，当前版本为 V2.0.0（后端 `pyproject.toml` 标记版本为 `2.0.0`）。

系统基于 **OpenAlex 学术数据库** 构建，覆盖四类人才数据源：

| 人才类型 | 数据来源 | 状态 |
|---------|---------|------|
| 学术人才 | OpenAlex 学术数据库 | ✅ 已完成 |
| 开源人才 | GitHub 等开源社区 | 📋 规划中 |
| 竞赛人才 | ICPC、数学建模等顶尖竞赛获奖者 | 📋 规划中 |
| 行业人才 | 招聘平台、企业数据 | 📋 规划中 |

当前已实现的核心功能包括：学术人才搜索与发现、人才画像查看、候选人筛选/排序/对比、重点人才导出、收藏与人才池管理、三维权限控制（学校/国家/技术要素）、采集任务管理、语义搜索与 JD 岗位匹配、相似人才推荐等。

---

## 技术栈

### 后端

- **Python 3.11+**
- **FastAPI** — Web 框架
- **SQLAlchemy 2.x + Alembic** — 异步 ORM 与数据库迁移
- **PostgreSQL 14+** — 主数据库（开发与生产均使用 PostgreSQL，无 SQLite 降级）
- **pgvector** — PostgreSQL 向量扩展，用于语义搜索
- **Pydantic v2 + pydantic-settings** — 配置与校验
- **Redis** — 可选缓存层，支持降级（无 Redis 时直接查库）
- **httpx / aiohttp** — 异步 HTTP 客户端
- **tenacity** — 重试策略
- **bcrypt + PyJWT** — 认证
- **openai / tiktoken / numpy** — LLM 与嵌入相关

### 前端

- **React 18 + TypeScript**
- **Vite** — 构建工具
- **Ant Design v5** — UI 组件库
- **React Router v6** — 路由
- **Zustand** — 状态管理
- **TanStack React Query (v5)** — 服务端状态管理与缓存
- **Axios** — HTTP 客户端
- **ECharts** — 图表可视化

### 基础设施

- **Docker & Docker Compose** — 容器化部署
- **Nginx** — 前端生产环境托管
- **GitHub Actions** — CI/CD
- **uv (Astral)** — Python 包管理与运行（取代 pip）

---

## 项目结构

```
talent-platform/
├── backend/                    # 后端服务
│   ├── app/                   # 应用代码
│   │   ├── api/v1/endpoints/  # API 路由（按业务模块划分）
│   │   ├── models/            # SQLAlchemy ORM 模型
│   │   ├── schemas/           # Pydantic DTO（部分也在 api/v1/schemas/）
│   │   ├── services/          # 业务逻辑层
│   │   ├── repositories/      # 数据访问层
│   │   ├── builders/          # ETL/数据转换（SearchBuilder, StatBuilder）
│   │   ├── core/              # 核心基础设施（config, auth, db, cache, logging, exceptions, metrics）
│   │   ├── middleware/        # 中间件（限流、请求日志、指标采集）
│   │   └── main.py            # FastAPI 入口
│   ├── migrations/            # Alembic 数据库迁移脚本
│   ├── tests/                 # pytest 测试
│   ├── scripts/               # 运维与数据脚本
│   ├── pyproject.toml         # Python 依赖与工具配置
│   ├── uv.lock                # uv 锁定文件
│   ├── alembic.ini            # Alembic 配置
│   └── pytest.ini             # pytest 配置
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── pages/             # 页面级组件
│   │   ├── components/        # 可复用组件
│   │   ├── services/          # API 客户端（api.ts）
│   │   ├── stores/            # Zustand 状态管理
│   │   ├── hooks/             # 自定义 React Hooks
│   │   ├── types/             # TypeScript 类型定义
│   │   ├── constants/         # 前端常量
│   │   ├── utils/             # 工具函数
│   │   └── test/setup.ts      # Vitest 测试初始化
│   ├── tests/                 # Playwright E2E 测试
│   ├── package.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── playwright.config.ts
│   ├── tsconfig.json
│   └── eslint.config.js
├── deploy/                     # 部署配置
│   ├── docker-compose.yml     # Docker Compose 编排
│   ├── init-db.sql            # 数据库初始化脚本
│   └── schema.sql             # 数据库结构备份
├── docs/                       # 项目文档（按版本 `学术人才库 v1.x/` 组织）
├── data/seed/                  # 种子数据
├── pgvector/                   # pgvector 源码（嵌入式）
├── scripts/                    # 根级脚本（dev.sh, restart_services.py）
├── Makefile                    # 统一命令入口
└── .github/workflows/ci.yml    # GitHub Actions CI 配置
```

---

## 构建与运行命令

项目使用 **Makefile** 作为统一命令入口。常用命令：

```bash
# 查看所有可用命令
make help

# 安装依赖
make install              # 安装前后端全部依赖（backend: uv sync --all-groups; frontend: npm install）
make install-backend
make install-frontend

# 开发启动
make dev-backend          # 启动后端开发服务器（uvicorn，端口 8003，--reload）
make dev-frontend         # 启动前端开发服务器（vite，端口 2012）
make dev                  # docker-compose up（全栈容器模式）

# 测试
make test                 # 运行后端测试（默认跳过 slow 标记的测试）
make test-backend         # uv run pytest
make test-frontend        # npm run test（Vitest）

# 代码检查
make lint                 # 前后端全部检查
make lint-backend         # ruff + black --check
make lint-frontend        # npm run lint（ESLint）

# 数据库
make migrate              # 执行 Alembic 升级到最新版本
make migrate-create       # 创建新迁移（需传 msg="描述"）
make migrate-rollback     # 回滚一次迁移

# 数据流水线
make seed                 # 初始化种子数据
make sync                 # 运行 OpenAlex 数据同步
make build-objects        # 从原始数据构建领域对象
make pipeline             # migrate + seed

# Docker
make docker-up            # docker-compose up -d
make docker-down          # docker-compose down
make docker-logs          # docker-compose logs -f

# 清理
make clean                # 清理 __pycache__、.pytest_cache、node_modules、dist、*.pyc
```

### 访问地址

- 前端: http://localhost:2012
- 后端 API: http://localhost:8003
- API 文档 (Swagger UI): http://localhost:8003/docs
- API 文档 (ReDoc): http://localhost:8003/redoc
- 默认账号: `admin` / `admin123`

---

## 代码组织与架构

### 后端分层架构

1. **Endpoints** (`api/v1/endpoints/`) — HTTP 请求处理、Pydantic 参数校验
2. **Services** (`services/`) — 业务逻辑编排
3. **Repositories** (`repositories/`) — 数据库查询与操作
4. **Builders** (`builders/`) — 原始数据 → 领域对象转换（ETL 模式）
5. **Models** (`models/`) — SQLAlchemy ORM 模型

### 三层数据架构

系统使用三层数据模型保证数据质量与可追溯性：

| 层级 | 代表表 | 作用 |
|------|--------|------|
| **原始层 (Raw)** | `raw_work`, `raw_author`, `raw_institution` | OpenAlex API 原始数据 |
| **标准化层 (Standardized)** | `std_author`, `std_school` | 清洗后的数据，含 CS 分数 |
| **服务层 (Serving)** | `core_talent`, `core_school` | 面向用户的业务数据 |

数据流向：Raw → Standardized（通过 Normalizers）→ Serving（通过 Sync services）

**CS 背景过滤**：在 Standardized → Serving 阶段，仅 `cs_concepts_score >= 0.5` 的作者会被同步到 Talent 表。配置见 `services/common/cs_concepts.py`。

### 11 阶段采集流水线

`CollectionOrchestrator` (`services/collect/orchestrator.py`) 执行完整采集：

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

每个要素包含多个 `TechDirection` 子方向，Venue（会议/期刊）通过 `VenueTechBinding` 与技术要素绑定。

### 关键后端模块

| 模块路径 | 职责 |
|----------|------|
| `services/collect/` | 采集任务创建、Venue 执行、进度追踪 |
| `services/sync/` | AuthorSync, SchoolSync, TechTagSync, ServingLayerOrchestrator |
| `services/normalizers/` | AuthorNormalizer, SchoolNormalizer, TechBelongCalculator |
| `services/search/` | 搜索服务（关键词/全文/语义/混合搜索策略） |
| `services/embedding/` | 向量嵌入服务 |
| `services/llm/` | LLM 网关（支持 DeepSeek/OpenAI/智谱/通义千问/Custom） |
| `services/jd_match/` | JD 岗位匹配服务 |
| `services/recommend/` | 相似人才推荐 |
| `services/common/cs_concepts.py` | CS 背景分数计算与过滤阈值 |
| `services/common/http_client.py` | HTTP 客户端工厂（支持代理配置） |

### 前端状态管理

- **authStore** (`stores/authStore.ts`) — 用户认证状态
- **favoritesStore** (`stores/favoritesStore.ts`) — 收藏与人才池状态
- **domainStore** (`stores/domainStore.ts`) — 领域相关状态
- **localStorage** — 持久化用户偏好（列配置、搜索模板等）

---

## 数据库规范

### 命名约定

- **表名**: `{module}_{entity}`，例如 `core_talent`, `iam_user_account`, `raw_work`
- **主键**: `{entity}_id`，例如 `talent_id`, `school_id`
- **时间戳**: `created_at`, `updated_at`，通过 `TimestampMixin` 统一混入
- **枚举值**: 数据库中存字符串值，代码中用 Python Enum 或 TypeScript 常量映射

### 索引策略

性能索引通过迁移 `023_add_performance_indexes.py` 创建，分为 P0（用户可见页面）与 P1（采集任务）两类。关键索引包括：

- `core_talent`: `ix_core_talent_visible_school_role`（按学校+角色过滤）、`ix_core_talent_visible_cited_desc`（按引用数降序）
- `core_talent_tech_tag`: `ix_talent_tech_enabled_element` / `ix_talent_tech_enabled_direction`（技术要素/方向页面）
- `raw_work`: `ix_raw_work_source_year`（按 Venue + 年份）

PostgreSQL 特性使用：降序索引 (`DESC`)、部分索引 (`WHERE condition`)。可用 `python scripts/verify_indexes.py` 验证索引存在。

---

## 代码风格指南

### Python（后端）

- **格式化**: Black，`line-length = 100`
- **Lint**: Ruff，目标 Python 3.11
  - 启用规则: E, W, F, I, B, C4, UP
  - 忽略: E501（Black 已处理）、B008、UP017
- **类型检查**: mypy，`disallow_untyped_defs = true`
  - `models/`, `repositories/`, `services/`, `builders/` 模块放宽为 `false`
  - `migrations/` 与 `tests/` 被排除
  - CI 使用 **mypy gate** (`scripts/mypy_gate.py`) 与基线文件 `.mypy_baseline.txt` 对比，新增类型错误会导致构建失败
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
- **测试数据库**: **必须使用独立的 PostgreSQL 测试库**（默认 `talent_db_test`）。每个测试函数结束后会 `DROP ALL TABLES`。切勿将 `TEST_DATABASE_URL` 指向生产数据库！
- **启动前准备**:
  ```bash
  psql -U postgres -c "CREATE DATABASE talent_db_test OWNER talent_user;"
  ```
- **Fixture 核心** (`tests/conftest.py`):
  - `test_engine` — 函数级，创建/销毁所有表
  - `test_session` — 函数级，异步 Session
  - `client` — 函数级，覆盖 `get_async_session` 依赖的 HTTP 测试客户端
  - `sample_talent`, `sample_tech_domain`, `sample_venue`, `full_setup` — 常用测试数据
- **测试标记**:
  - `unit` — 单元测试
  - `integration` — 集成测试
  - `e2e` — 端到端测试
  - `slow` — 慢速测试（默认被跳过，需显式运行）
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
  - 测试目录: `frontend/tests/`
  - 仅 Chromium 浏览器
  - 开发环境复用已有服务器 (`reuseExistingServer: true`)
  - 命令:
    ```bash
    cd frontend
    npx playwright test          # 运行全部
    npx playwright test --ui     # UI 模式
    ```

---

## 部署流程

### Docker Compose（推荐）

```bash
make docker-up      # 启动所有服务
make docker-logs    # 查看日志
make docker-down    # 停止服务
```

服务组成：
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

### 后端关键配置（`.env`）

| 变量 | 说明 | 典型值 |
|------|------|--------|
| `DATABASE_URL` | 异步数据库连接 | `postgresql+asyncpg://...` |
| `DATABASE_SYNC_URL` | 同步数据库连接（用于 Alembic 等） | `postgresql://...` |
| `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_HOURS` | JWT 认证 | HS256, 8h |
| `CORS_ORIGINS` | 跨域来源 | `["*"]`（开发） |
| `REDIS_ENABLED` / `REDIS_URL` | Redis 缓存开关 | `false`（开发默认关闭） |
| `LLM_ENABLED` / `LLM_PROVIDER` / `LLM_API_KEY` | LLM 功能开关 | `false`, `deepseek` |
| `EMBEDDING_DIMENSION` | 向量维度 | `1536`（取决于嵌入模型） |
| `SEARCH_DEFAULT_MODE` | 默认搜索模式 | `keyword`（可选 fulltext/semantic/hybrid） |
| `RATE_LIMIT_ENABLED` | 限流开关 | `false`（开发） |

### 前端关键配置（`.env`）

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
- **健康检查**:
  - `/api/v1/health` — 综合健康
  - `/ready` — 就绪探针
  - `/live` — 存活探针
- **指标**: `/api/v1/metrics` — Prometheus 格式指标

---

## 安全注意事项

1. **数据库隔离**: 测试数据库与生产数据库必须物理隔离。`conftest.py` 会在每个测试函数后删除所有表。
2. **JWT Secret**: 生产环境必须修改 `SECRET_KEY`，避免使用默认值。
3. **CORS**: 开发环境允许全部来源 (`["*"]`)，生产环境应限制为实际域名。
4. **Rate Limiting**: 生产环境建议启用 (`RATE_LIMIT_ENABLED=true`)，默认 100 req/min 每用户/IP。
5. **代理配置**: v1.4.1 支持从数据库动态加载企业代理配置，用于内网部署。见 `app/main.py` 中的 `init_proxy_config()`。
6. **LLM API Key**: 生产环境需妥善保管，勿提交到版本控制。
7. **密码存储**: 使用 bcrypt 哈希，禁止明文存储。

---

## CI/CD

GitHub Actions 工作流 `.github/workflows/ci.yml`：

1. **backend-test** — 在 Ubuntu 上启动 PostgreSQL 15 服务，运行 `uv run pytest tests/ -v --tb=short`
2. **backend-lint** — 运行 `uv run python scripts/mypy_gate.py`（基于基线的 mypy 门禁）
3. **frontend-lint** — Node 20 环境，执行 `npm ci` → `npm run lint` → `npm audit` → `npm run build`

触发条件：push / PR 到 `main` 或 `develop` 分支。

---

## 关键文件速查

| 用途 | 路径 |
|------|------|
| 后端入口 | `backend/app/main.py` |
| 配置定义 | `backend/app/core/config.py` |
| 数据库引擎 | `backend/app/core/database.py` |
| 采集编排器 | `backend/app/services/collect/orchestrator.py` |
| 服务层同步编排 | `backend/app/services/sync/orchestrator.py` |
| CS 背景过滤 | `backend/app/services/common/cs_concepts.py` |
| 原始数据模型 | `backend/app/models/raw_data.py` |
| 标准化模型 | `backend/app/models/standardized.py` |
| 服务层模型（人才） | `backend/app/models/talent.py` |
| 服务层模型（学校） | `backend/app/models/school.py` |
| 技术域模型 | `backend/app/models/tech_domain.py` |
| API 路由汇总 | `backend/app/api/v1/router.py` |
| 前端入口 | `frontend/src/main.tsx` |
| 前端路由 | `frontend/src/App.tsx` |
| API 客户端 | `frontend/src/services/api.ts` |
| 全局布局 | `frontend/src/layouts/MainLayout.tsx` |

---

## 开发注意事项

- **后端开发务必加 `--reload`**: `uvicorn app.main:app --reload --port 8003`
- **前端端口固化**: Vite 配置 `strictPort: true`，端口 2012 被占用时会报错而非自动切换
- **代理开发**: 前端 `vite.config.ts` 已配置 `/api` 代理到 `http://localhost:8003`
- **mypy 基线维护**: 若修复了已有 mypy 错误，需重新生成基线：`python scripts/mypy_gate.py --regenerate`
- **Git 分支**: `main` 为生产就绪代码，`feature/*` 为功能分支。提交信息建议遵循 conventional commits（`feat:`, `fix:`, `docs:`, `refactor:`）
- **自然语言**: 项目文档与注释主要使用中文，代码变量/函数名使用英文，API 返回数据包含中英文混合字段
