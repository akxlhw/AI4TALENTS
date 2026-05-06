# 开源人才子系统设计文档 (v2.0.0)

> 本文档是开源人才子系统（Open Source Talent Subsystem）的完整设计说明，面向开发者和 AI 编程助手�?> 版本: v2.0.0 | 最后更�? 2026-04-30

---

## 1. 项目定位

开源人才子系统是智能人才库（AI4TALENTS）的第二大子系统，与学术人才子系统（OpenAlex 论文数据）并行运行，面向六个技术领域从 GitHub 采集开源贡献者数据，支持搜索、发现、匹配、收藏�?
| 维度 | 学术人才 | 开源人�?|
|------|---------|---------|
| 数据�?| OpenAlex API | GitHub API |
| 核心身份 | 论文作�?| 仓库贡献�?|
| 能力指标 | H-index, 引用�?| Stars, Commits, PRs |
| 技术标�?| 论文主题 | 编程语言 + 技术领�?|
| 表名前缀 | `core_` / `raw_` | `os_` |

---

## 2. 六要素技术领�?
开源人才同样按六要素分类：

| 代码 | 中文 | 英文 | 示例仓库 |
|------|------|------|---------|
| `ai` | 人工智能 | Artificial Intelligence | PyTorch, TensorFlow, Hugging Face |
| `robotics` | 机器�?| Robotics | ROS, ArduPilot, Isaac Sim |
| `data_science` | 数据科学 | Data Science | pandas, NumPy, Jupyter |
| `networks` | 网络与通信 | Networks & Communications | Linux Kernel, Envoy, gRPC |
| `systems` | 系统与软�?| Systems & Software | Go, Rust, Kubernetes, Docker |
| `security` | 信息安全 | Information Security | OWASP ZAP, Metasploit, sqlmap |

---

## 3. 文档索引

| 文档 | 内容 |
|------|------|
| [01_架构设计.md](01_架构设计.md) | 系统架构、模块划分、技术选型 |
| [02_数据模型.md](02_数据模型.md) | ER 图、表结构、字段说�?|
| [03_API规范.md](03_API规范.md) | REST API 端点、请�?响应格式 |
| [04_采集流水�?md](04_采集流水�?md) | 8 阶段采集流程、配置说�?|
| [05_部署初始�?md](05_部署初始�?md) | 迁移、Seed、环境变�?|
| [06_前端设计.md](06_前端设计.md) | 页面清单、组件设计、状态管理、API 扩展 |
| [07_模块详细设计.md](07_模块详细设计.md) | GitHubClient、SearchService、EmbeddingService、Collector 等核心模块接口与算法 |
| [08_权限与安全设�?md](08_权限与安全设�?md) | 角色矩阵、数据隔离、Token 加密、审计日�?|
| [09_测试策略与用�?md](09_测试策略与用�?md) | 前后端测试范围、用例示例、验收标�?|
| [10_数据库索引与性能.md](10_数据库索引与性能.md) | 索引清单、查询优化、pgvector 规划、迁移脚�?|

---

## 4. 快速开�?
```bash
# 1. 运行迁移（确�?os_repo_config 表已创建�?cd backend
alembic upgrade head

# 2. 预置仓库绑定
python scripts/seed_os_repo_configs.py

# 3. 配置 GitHub Token
# 在系统配置页设置，或环境变量 GITHUB_TOKENS=token1,token2

# 4. 启动采集
# 系统配置 �?采集配置 �?开源采�?�?选择技术领�?�?开始采�?```

---

## 5. 关键文件路径

```
backend/app/modules/open_source/
├── models.py                    # 12 �?SQLAlchemy 模型
├── api/
�?  ├── schemas.py               # Pydantic DTOs
�?  └── endpoints.py             # FastAPI 路由 (~700 �?
├── collectors/
�?  ├── orchestrator.py          # 8 阶段流水线编�?�?  └── phases/                  # 8 �?Phase 处理�?�?      ├── fetch_repos.py       # Phase 1: 仓库发现（双模式�?�?      ├── fetch_developers.py  # Phase 2: 开发者采�?+ 公司过滤
�?      ├── fetch_contributions.py    # Phase 3: 贡献数据
�?      ├── aggregate_languages.py    # Phase 4: 语言聚合
�?      ├── calc_tech_belong.py       # Phase 5: 技术归�?�?      ├── sync_serving.py           # Phase 6: 持久�?�?      ├── generate_embeddings.py    # Phase 7: 向量嵌入
�?      └── build_stats.py            # Phase 8: 统计
├── repositories/
�?  ├── developer_repository.py
�?  ├── embedding_repository.py
�?  └── repo_config_repository.py    # 新增
└── services/
    ├── github_client.py         # GitHub REST/GraphQL 客户�?    ├── developer_service.py
    ├── search_service.py
    ├── embedding_service.py
    ├── jd_match_service.py
    ├── stats_service.py
    └── repo_config_service.py     # 新增

frontend/src/modules/openSource/
├── types.ts
├── api.ts
├── pages/
�?  ├── OpenSourcePage.tsx         # 概览
�?  ├── OpenSourceSearchPage.tsx   # 搜索
�?  ├── DeveloperDetailPage.tsx    # 详情
�?  └── OSRepoConfigPage.tsx       # 仓库绑定管理
├── components/
�?  ├── DeveloperCard.tsx
�?  └── FilterPanel.tsx
└── hooks/
    └── useOpenSourceQueries.ts

frontend/src/components/OSCollectPanel.tsx    # 采集面板（系统配置页内嵌�?```
