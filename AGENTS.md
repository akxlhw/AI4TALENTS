<!-- From: D:/AI/AI4TALENT/AGENTS.md -->
> 本文件面向 AI 编程助手。如果你正在阅读此文件，说明你对本项目一无所知——本文将告诉你需要了解的一切。

---

# 智能人才库 (AI4TALENTS) 项目指南

## 项目概述

**智能人才库（AI4TALENTS）** 是一套面向招聘团队的多维度人才发现平台。

- **当前版本**：**V5.0.0**（以 `backend/pyproject.toml`、`frontend/package.json`、`backend/app/core/config.py` 为准；变更记录见 `CHANGELOG.md`）。
- **项目定位**：整合公开学术数据与开源社区数据，帮助招聘团队发现、筛选、对比和管理高端技术人才。
- **人才数据源**（每个域独立表族，跨域隔离铁律，均不复用其他域表）：
  - **学术人才**（`domains/academic/`）：OpenAlex 学术数据库，功能完整。
  - **开源人才**（`domains/open_source/`）：GitHub API 采集，功能完整。
  - **实验室人才**（`domains/lab/`，V3.0.0）：AI 实验室人才，`ai-lab-talent-crawler` skill 产出 JSONL，管理员手动上传导入。
  - **竞赛人才**（`domains/competition/`，V4.0.0）：`comp-talent-crawler` skill 产出 schema v1.0 JSONL，`CompImportService` 按单场赛事全量替换导入。已接入 Codeforces/IOI/IMO/IPhO/ICPC。设计文档 `docs/competition-v1.0/`。
  - **行业人才**（`domains/industry/`，V5.0.0）：按岗招聘，`smart-talent-sourcing` skill 产出 JSONL，增量 upsert 导入（也支持 API Key 推送通道）。呈现以人才为主线、岗位为标签与筛选维度。设计文档 `docs/v5.0.0/`。
- **规划中**：竞赛清单内其余源（Kaggle/CTF/RoboCup/超算等）。

主要功能：人才搜索与发现、画像查看、筛选/排序/对比、导出、收藏与人才池、三维权限控制、采集任务管理、语义搜索、JD 匹配、相似推荐、学术谱系、实验室师承树、用户注册审批与审计日志等。

---

## 技术栈

### 后端

- **Python 3.11+** / **FastAPI 0.141** / **Pydantic v2 + pydantic-settings**
- **SQLAlchemy 2.0（异步）+ Alembic** / **PostgreSQL 16+（无 SQLite 降级）** / asyncpg + psycopg2-binary
- **pgvector**（语义搜索/推荐）/ **Redis**（可选缓存，支持降级）
- httpx / aiohttp（必须经 `HttpClientFactory` 封装）/ tenacity / bcrypt + PyJWT
- openai / tiktoken / beautifulsoup4 / **uv（Astral，取代 pip）**

### 前端

- **React 18 + TypeScript 5（strict）** / **Vite** / **Ant Design v5 + icons**
- React Router v6 / **Zustand**（客户端状态）/ **TanStack React Query**（服务端状态）
- Axios / **ECharts + echarts-for-react** / **Vitest + jsdom** / Playwright（E2E）

### 基础设施

- Docker & Docker Compose / Nginx（前端 production target）/ GitHub Actions CI / Pre-commit / Prometheus（`/api/v1/metrics`）

---

## 项目结构

```
talent-platform/
├── backend/
│   ├── app/
│   │   ├── api_router.py        # FastAPI 路由注册表（聚合全部域路由到 /api/v1）
│   │   ├── model_registry.py    # Alembic 模型注册表
│   │   ├── main.py              # 入口与生命周期（lifespan、中间件、/uploads 托管）
│   │   ├── core/                # config（pydantic-settings）、database、auth、exceptions、cache、metrics
│   │   ├── middleware/          # 限流、请求日志、指标采集
│   │   └── domains/             # 领域驱动核心：每域统一 api/ models/ schemas/ repositories/ services/ [constants/]
│   │       ├── academic/        # 学术域（最大域：builders/、services/collect 11 阶段流水线、search strategies 等）
│   │       ├── open_source/     # 开源域（collectors/github_*、在校生分类器、purge、嵌入服务）
│   │       ├── lab/             # 实验室域（JSONL 导入、师承网络、主页预览）
│   │       ├── competition/     # 竞赛域（五表族、单场全量替换导入）
│   │       ├── industry/        # 行业域（岗位/人才/关联三表、增量 upsert 导入）
│   │       └── shared/          # 共享域（iam/audit/config/llm/http_client/jsonl_import 骨架等）
│   ├── migrations/              # Alembic 迁移（编号序列 001~058 + 若干 hash 历史脚本）
│   ├── tests/                   # pytest（domains/ 按域组织）
│   ├── scripts/                 # check_architecture.py（CI 门禁）、ops/mypy_gate.py、data/ 种子脚本
│   ├── pyproject.toml / uv.lock / alembic.ini / pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # 路由 + 守卫
│   │   ├── pages/               # academic / open-source / lab / competition / industry / admin / system-config 等
│   │   ├── components/ layouts/ contexts/ hooks/ stores/ theme/ types/ utils/ constants/
│   │   └── services/            # api.ts 聚合 + api/ 域拆分模块（client.ts 等）
│   ├── tests/                   # Playwright E2E（*.spec.ts）
│   ├── package.json / vite.config.ts（dev 2012，代理 /api、/uploads → 8003）/ vitest.config.ts
├── deploy/                      # docker-compose.yml、init-db.sql（uuid-ossp + pg_trgm）
├── docs/                        # 各版本设计文档（v5.0.0/、competition-v1.0/、academic-v1.x 等；audit/ 不入库）
├── scripts/                     # dev.sh、pre-push.sh、local_ci.ps1、precommit_backend.py、bump_version.py 等
├── Makefile                     # 统一命令入口
├── AGENTS.md / CLAUDE.md        # AI 助手指南（改动时两份同步）
└── CHANGELOG.md                 # 版本变更记录
```

---

## 构建与运行命令

项目使用 **Makefile** 作为统一命令入口。Windows 无 `make` 时参照 Makefile 手动执行（或用 `scripts/local_ci.ps1` / `local_test.ps1`）。

```bash
make install              # 安装全部依赖（backend: uv sync --all-groups; frontend: npm install）
make dev-backend          # 后端 uvicorn（端口 8003，--reload）
make dev-frontend         # 前端 vite（端口 2012，strictPort）
make test                 # 前后端全部测试（后端默认跳过 slow 标记）
make lint                 # 基础检查（ruff + black --check + eslint）
make lint-full            # 前后端完整检查（与 CI 一致）
make migrate / migrate-create msg="描述" / migrate-rollback
make seed                 # 种子数据（scripts/data/init_system.py --force）
make docker-up / docker-down / docker-logs
```

### 访问地址

- 前端 http://localhost:2012（`/api` 与 `/uploads` 代理到 8003）；后端 http://localhost:8003（Swagger `/docs`）
- 默认账号 `admin` / `admin123`
- 注意：Docker Compose 模式后端容器端口为 **8000**（本地开发为 8003）

---

## 架构组织原则

### 跨域隔离（铁律）

- **`domains/academic/`、`open_source/`、`lab/`、`competition/`、`industry/` 之间不得互相导入内部模块**
- **`domains/shared/` 不得导入任何业务域内部模块**（`models.enums` 除外）
- 各域仅可通过 `domains/shared/` 和 `app/core/` 共享能力
- 违反即 CI 失败（`backend/scripts/check_architecture.py` 零容忍，无基线）

### 目录放置规则

| 代码类型 | 应放置位置 | 禁止放置位置 |
|----------|-----------|-------------|
| 业务域 API 路由 | `domains/<域>/api/` | `app/api/v1/endpoints/`（已废弃） |
| 业务域模型 | `domains/<域>/models/` | `app/models/`（已废弃） |
| 业务域 Service | `domains/<域>/services/` | `app/services/`（已废弃） |
| 业务域 Repository | `domains/<域>/repositories/` | `app/repositories/`（已废弃） |
| 业务域常量 | `domains/<域>/constants/` | `app/constants/`（已废弃） |
| 共享基础设施 | `app/core/` | 任何 domain 内部 |
| 中间件 | `app/middleware/` | 任何 domain 内部 |
| 全局路由注册 | `app/api_router.py` | 任何其他位置 |
| 全局模型注册 | `app/model_registry.py` | 任何其他位置 |

`open_source`、`lab`、`competition`、`industry` 域的多个子路由由各自 `api/__init__.py` 聚合成单个 router 后，再在 `app/api_router.py` 统一挂载。

### Endpoint 分层导入铁律

`api/` 下的 Endpoint 文件只能看到 Service 层，禁止直接触碰 Repository、Collector、底层 Client、LLM 网关等基础设施。

**允许直接 import**：同域 Service、shared Service、任意 schemas、shared enums（`*.models.enums`）、`app.core.*`、`fastapi`、`sqlalchemy`、`pydantic`、`typing` 等第三方库。

**禁止直接 import**：`*Repository`、`*Collector`、`LLMGateway`、`*EmbeddingService`、`GitHubClient`/`OpenAlexClient` 等底层 HTTP Client、`AsyncSessionLocal`、同域 `models/`、`builders/`、`CollectionOrchestrator`。

### HTTP 客户端统一规则

系统所有出站 HTTP 请求必须统一通过 `HttpClientFactory` 创建和管理，禁止直接导入或使用 `httpx`、`aiohttp`、`requests` 等底层库。

- 正确做法：`HttpClientFactory.create_client_for_url(target_url, timeout=...)`
- 例外文件（已基线化）：`domains/shared/services/common/http_client.py`（工厂本身）、`domains/academic/services/data_fetchers.py`（aiohttp）、`domains/academic/services/openalex_client.py`（httpx）、`domains/open_source/services/github_client.py`（httpx）、`domains/shared/services/system_config_test_service.py`（函数内 httpx）

### 错误处理契约

Service/基础设施层一律 raise 领域自定义异常（LLM 链路统一经 `llm/errors.py` 的 `llm_error_from_exception` 转换底层 SDK 异常），边界处（API 层异常处理器、health 探测、后台任务）再统一转换为 HTTP 响应/布尔/任务状态，禁止以布尔/元组/字符串状态码作为错误通道；可调参数（超时、重试次数、批大小）必须读 `config.py` 或域 `constants/`，禁止内联魔法值。

### 三层数据架构（学术域）

Raw（`raw_work`/`raw_author`/`raw_institution`）→ Standardized（`std_author`/`std_school`，Normalizers）→ Serving（`core_talent`/`core_school`，Sync services）。**CS 背景过滤**：仅 `cs_concepts_score >= 0.5` 的作者同步到 Talent 表（`domains/academic/services/common/cs_concepts.py`）。

### 采集流水线（学术域）

`CollectionOrchestrator`（`services/collect/orchestrator.py`）为瘦编排器，11 个阶段由 `collect/phases/` 下独立处理器实现（Venue 采集 → 作者/机构数据 → 标准化 → 技术归属 → 同步服务层 → 精选论文 → 主题标签 → 学校统计 → 首页统计）。

### 六大技术要素

表 `core_tech_domain`（种子 `scripts/data/init_system.py`）：`ai` 人工智能 / `robotics` 机器人 / `data_science` 数据科学 / `networks` 网络与通信 / `systems` 系统与软件 / `security` 信息安全。

---

## 代码风格指南

### Python（后端）

- **格式化**：Black，`line-length = 100`，target `py311`
- **Lint**：Ruff（E, W, F, I, B, C4, UP；忽略 E501、B008、UP017、UP038；排除 `migrations/`）
- **类型检查**：mypy，`disallow_untyped_defs = true`，`ignore_missing_imports = true`（`migrations/`、`tests/` 排除）
  - CI 使用 **mypy gate**（`scripts/ops/mypy_gate.py`）对比基线 `.mypy_baseline.txt`，新增错误即失败
  - 基线再生：`cd backend && uv run python scripts/ops/mypy_gate.py --regenerate`

### TypeScript / React（前端）

- **Lint**：ESLint 9 flat config（`no-explicit-any: off`；允许 `_` 前缀未使用变量）
- **格式化**：Prettier（`semi: false`、`singleQuote: true`、`tabWidth: 2`、`printWidth: 100`），`npm run format[:check]`
- **TS**：`strict: true` + `noUnusedLocals/Parameters`；路径别名 `@/` → `src/`

---

## 测试策略

### 后端测试

- **框架**：pytest + pytest-asyncio + httpx (AsyncClient)；配置 `backend/pytest.ini` 生效（默认 `-m "not slow"`）
- **测试库**：独立 PostgreSQL（默认 `talent_db_test`，`tests/conftest.py` 用 `DATABASE_URL`/`DATABASE_SYNC_URL` 覆盖；每函数后 TRUNCATE 所有表）。**切勿指向生产库！** 首次需 `CREATE DATABASE talent_db_test OWNER talent_user;`
- **核心 Fixture**：`test_engine` / `test_session` / `client`（覆盖 `get_async_session`）/ `sample_talent` 等 / `test_user`、`mock_admin_user`
- **标记**：`unit` / `integration` / `e2e` / `slow`（默认跳过）/ `requires_pgvector`（不可用自动跳过）
- **命令**：`cd backend && uv run pytest`（`-v --cov=app` 带覆盖率）

### 前端测试

- **单元**：Vitest + jsdom + testing-library（`src/**/*.test.ts(x)`，setup `src/test/setup.ts`），`npm run test`
- **E2E**：Playwright（`tests/*.spec.ts`，仅 Chromium，workers 1，`npm run build && npx playwright test`，dev 复用已有服务器）

---

## CI/CD

GitHub Actions `.github/workflows/ci.yml`（push/PR 到 main/develop）：

1. **backend-test** — PostgreSQL 15 + pgvector 服务，uv 安装后跑常规 + slow 测试
2. **backend-lint** — mypy gate（`scripts/ops/mypy_gate.py`）+ 架构合规检查（`scripts/check_architecture.py`）
3. **frontend-lint** — Node 20 `npm ci`，ESLint、npm audit、Vitest、生产构建（`tsc -b && vite build`）

### 架构合规检查（本地）

```bash
cd backend && uv run python scripts/check_architecture.py          # 检查
cd backend && uv run python scripts/check_architecture.py --update-baseline  # 修复历史债务后更新基线
```

三条规则：跨域依赖（零容忍无基线）、Endpoint 分层（基线容忍）、HTTP 客户端统一（基线容忍）；基线文件 `.architecture_baseline.txt`。

### Pre-commit

`.pre-commit-config.yaml`：对 `backend/app/domains/*/api/*.py` 变更执行架构检查（`scripts/precommit_backend.py`）。安装：`cd backend && uv run pre-commit install`。

---

## 部署流程

### Docker Compose（推荐）

```bash
make docker-up / docker-logs / docker-down
```

服务：`postgres`（16-alpine + init-db.sql）、`redis`（7-alpine，`--profile production` 才启动）、`backend`（容器端口 8000，开发挂载源码 + reload）、`frontend`（2012，development target）。密码等敏感值走环境变量（`POSTGRES_PASSWORD` 占位符 `CHANGE_ME_IN_PRODUCTION`）；生产用 override 文件或 docker secrets，**禁止提交真实密码**。

### 本地开发（非 Docker）

```bash
make install && cp backend/.env.example backend/.env && cp frontend/.env.example frontend/.env
cd deploy && docker-compose up -d postgres   # 起库
make migrate && make dev-backend             # 终端1
make dev-frontend                            # 终端2
```

---

## 环境变量与配置

模板：`backend/.env.example` / `frontend/.env.example`。关键项（其余见模板注释）：

| 变量 | 说明 | 典型值 |
|------|------|--------|
| `DATABASE_URL` / `DATABASE_SYNC_URL` | 异步/同步数据库连接（必填，缺失抛错） | `postgresql+asyncpg://...` |
| `SECRET_KEY` / `ACCESS_TOKEN_EXPIRE_HOURS` | JWT（生产必须改，<32 字符告警） | HS256, 8h |
| `CORS_ORIGINS` | 跨域来源（生产拒绝 `*` 和 localhost） | `["http://localhost:2012"]` |
| `REDIS_ENABLED` / `REDIS_URL` | Redis 开关 | `false`（开发） |
| `LLM_ENABLED` / `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_EMBEDDING_MODEL` | LLM 开关与模型 | `false`, `deepseek` |
| `LLM_TIMEOUT` / `LLM_MAX_RETRIES` / `LLM_MAX_BATCH_SIZE` | LLM 参数（错误处理契约要求从这里读） | `30.0`, `3`, `16` |
| `EMBEDDING_DIMENSION` / `EMBEDDING_BATCH_SIZE` | 向量维度 | `1536`, `100` |
| `SEARCH_DEFAULT_MODE` / `SEARCH_RRF_CONSTANT` / `SEARCH_HYBRID_EXTENDED_FACTOR` | 搜索模式与混合参数 | `keyword`, `60`, `3` |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | 限流 | `false`, `100` |
| `CIRCUIT_BREAKER_ENABLED` 等 `CIRCUIT_BREAKER_*` | 熔断器 | `true`, `5`, `30.0`, `10` |
| `GITHUB_TOKENS` / `GITHUB_RATE_LIMIT` | GitHub 采集（token 逗号分隔） | `ghp_xxx`, `5000` |
| `OPENALEX_BASE_URL` / `OPENALEX_EMAIL` / `OPENALEX_RATE_LIMIT` | OpenAlex 采集 | `10` req/s |
| `APP_NAME` / `APP_VERSION` / `ENVIRONMENT` / `DEBUG` | 应用基础 | 智能人才库 API, 5.0.0, development, false |
| `BACKEND_PORT` | 后端端口（本地 8003；Docker 设 8000） | `8003` |
| `INDUSTRY_IMPORT_API_KEY` | 行业导入 API Key（系统配置面板维护，非 .env） | — |
| 前端 `VITE_API_URL` | 后端 API 基础地址（须 `VITE_` 前缀） | `http://localhost:8003` |

---

## API 规范

- **Base Path**：`/api/v1`；**认证**：Bearer Token（`Authorization: Bearer <token>`）
- **分页**：`page`, `page_size`；**响应**：统一 JSON 结构
- **静态文件**：`/uploads`；**健康检查**：`/api/v1/health`、`/ready`、`/live`；**指标**：`/api/v1/metrics`

---

## 安全注意事项

1. **测试库与生产库物理隔离**（conftest 会清空/重建表）。
2. **生产必须改 `SECRET_KEY`**：生产缺失直接抛错，开发自动生成随机密钥并告警，<32 字符告警。
3. **CORS**：开发默认 `["http://localhost:2012"]`；生产强制拒绝 `*` 与 localhost 来源。JWT 走 Header（非 Cookie），故 `allow_credentials=False`。
4. **限流**：生产建议 `RATE_LIMIT_ENABLED=true`（默认 100 req/min 每用户/IP）。
5. **代理**：支持从数据库动态加载企业代理（`app/main.py` 的 `init_proxy_config()`，lifespan 启动执行）。
6. **LLM API Key / GitHub Tokens**：勿提交版本控制；staging/production 下 `DATABASE_URL` 含默认弱口令会告警。
7. **密码**：bcrypt 哈希，禁止明文。
8. **Docker**：`deploy/docker-compose.yml` 密码为占位符，生产必须 override/secrets。

---

## 关键文件速查

| 用途 | 路径 |
|------|------|
| 后端入口 + 生命周期 | `backend/app/main.py` |
| 环境变量配置 | `backend/app/core/config.py` |
| ORM 模型中央注册 | `backend/app/model_registry.py` |
| API 路由聚合 | `backend/app/api_router.py` |
| 采集流水线编排 | `backend/app/domains/academic/services/collect/orchestrator.py` |
| LLM 网关 | `backend/app/domains/shared/services/llm/llm_gateway.py` |
| HTTP 客户端工厂 | `backend/app/domains/shared/services/common/http_client.py` |
| JSONL 导入共享骨架 | `backend/app/domains/shared/services/jsonl_import/` |
| 架构合规检查 / mypy 门禁 | `backend/scripts/check_architecture.py` / `scripts/ops/mypy_gate.py` |
| 前端 API 客户端 | `frontend/src/services/api/client.ts` |
| 前端路由 + 守卫 | `frontend/src/App.tsx` |
| 前端主题 / 域注册 | `frontend/src/theme/index.ts` |
| 行业域设计文档 | `docs/v5.0.0/`（00 README / 01 需求清单 / 02 技术设计 / 03 Agent 对接指南） |

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
9. 修改了架构/配置/流程后，是否同步更新了本 `AGENTS.md` 与 `CLAUDE.md`？
