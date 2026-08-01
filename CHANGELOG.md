# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.0.0] - 2026-08-01

> V5.0.0 主开发内容：**行业人才库**（`domains/industry/`，第四个人才域）。当前交付设计文档，实现按 `docs/v5.0.0/02-技术设计.md` 实施顺序推进。

### Added

- **行业人才库设计文档 v1.1**（`docs/v5.0.0/02-技术设计.md`）：
  - 三表模型：`industry_position`（岗位一等实体）/ `industry_talent`（人才全局唯一，dedup_hash 三要素）/ `industry_position_talent`（关联表打分，含院校/企业/方向三维子分数）
  - 呈现原则：以人才为主线（与全库一致），岗位为标签与筛选维度（按岗招聘为辅助支撑）
  - 增量 upsert 导入：空字段不覆盖、缺席不删除、保留 touched/status/notes；JSONL 导入契约 schema v1.0
  - 数据来源：smart-talent-sourcing skill（脉脉/LinkedIn），域内不实现采集
- **AI Native 实验室师承树**（lab 域）：
  - 师从关系从力导向图重写为**树状拓扑**（自上而下、固定像素间距、无限画布缩放平移），节点带头像
  - 创始人置顶：后端 `LAB_FOUNDERS` 常量表标记（含别名归一），创始人金边树根 + 其学生真师承子树 + 「其他导师」组织聚合；无创始人实验室为实验室根 + 教授平行森林
  - B+C 分层：创始人学生中已为人师者（教授）默认展开一层，纯学生折叠为「学生（N）」聚合
  - 实验室页面拆「人才列表 / 师从关系」双 Tab（Tab 状态入 URL，详情页返回不丢失）；单击展开/收起，Shift+单击进人物详情
- **开源人才检索修复与增强**：
  - 修复 `POST /search` 关键词静默失效 bug（`query`→`q` 字段名错误，降级路径曾返回无筛选全表）
  - 混合搜索改 RRF 融合（k=60，与学术域同参数），修正分页总数失真
  - 迁移 056：`os_developer` name/github_login/company/location/bio 建 pg_trgm GIN 索引，tech_tags/primary_languages 转 JSONB + GIN
  - 列表接口 N+1 修复（角色标签批量聚合，每页 20 次查询降为 1 次）
- **开源人才「在校生」标签**：`is_student`（迁移 057）= bio 学生信号 OR（company 命中学校词典 AND 无教职工信号）；学校词典 5889 校名（学术域 core_school 导出）+ 32 条手工缩写别名；sync 流水线增量重算 + 存量回填脚本；列表/搜索/导出全链路筛选，前端筛选框 + 卡片绿色标签（开发库 3615 人标记 373 人）
- **开源仓库数据清理**：`POST /open-source/repo-configs/{id}/purge`（超管），dry_run 预览计数 → 确认硬删；归属判定「被其他已配置仓库引用才算共享」，收藏/入池人才保护；审计日志；前端清理入口 + 确认弹窗

### Changed

- 版本号 4.1.0 → 5.0.0（pyproject.toml、package.json、config.py、uv.lock、README.md、AGENTS.md、CLAUDE.md）
- mypy 基线：93 个既有错误被消除（在校生字段实施时顺带清理，零行为变化）

## [4.1.0] - 2026-07-19

### Added

- **竞赛域 M2 数据源接入**（用户关注清单第一批，爬虫插件式、后端零改动）：
  - **IOI 信息学奥赛**：`crawl_ioi.py` 解析官方统计站（stats.ioinformatics.org）服务端渲染表格，国家码自 `countries/XXX` 链接映射（100+ 三字母码→ISO-2），实测 IOI 2024 采集导入 **366 人**（金牌 34）
  - **IMO 数学奥赛**：`crawl_imo.py` 解析官网成绩页（`/results/individual/year/<year>/`，经 legacy-results-resolver 定位的规范地址），P1-P6 小题分入 `raw_meta`，实测 IMO 2024 采集导入 **609 人**（金牌 58，与官方一致）
  - **IPhO 物理奥赛**：官方站 `iphounesco.org` DNS 异常，改用 `ipho-unofficial.org` 存档源（`crawl_ipho.py`），理论/实验分入 `raw_meta`，实测 IPhO 2024 采集导入 **135 人**（金牌 18，覆盖全部获奖+荣誉提名）
  - **ICPC（团队赛首源）**：官方 API 需认证，改用 CLIST 榜单（含完整队伍成员），`crawl_icpc.py` 解析「大学（队名）+ 成员|分隔」结构，按 ICPC 惯例映射奖牌（1-4 金 / 5-8 银 / 9-12 铜），实测 ICPC 2024 全球总决赛采集导入 **139 队 + 417 队员**（冠军 Peking University（Naive Birds）金牌，队员全部挂接 team_id）
- 系列启用：`icpc` / `ioi` / `imo` / `ipho` 四个系列转为启用（`comp_series.is_enabled`），概览/筛选/详情自动可见
- skill 元数据：`sources.yaml` 启用 5 源并登记各源脚本；`SKILL.md` 用法覆盖 5 源

### Changed

- 版本号 4.0.0 → 4.1.0（pyproject.toml、package.json、config.py、uv.lock、README.md、AGENTS.md）
- IPhO 系列 homepage 更正为 `https://ipho-unofficial.org`（官方站 DNS 异常，采用存档源并在描述中注明）

### Notes

- M2 验证了「多源零改动接入」设计：4 个新源均为爬虫侧插件，产出同一 schema v1.0 JSONL，导入/查询/前端无一行改动
- 全量后端回归 827 通过；各源 JSONL 均通过 `scripts/check_jsonl.py` 校验

## [4.0.0] - 2026-07-19

### Added

- **竞赛人才域**（`domains/competition/`，M1 首发源 Codeforces 官方 API）：
  - **数据模型**：`comp_series / comp_contest / comp_talent / comp_team / comp_result` 五表族（跨域隔离铁律，不复用其他域表）；个人/团队赛双归属 result + PostgreSQL 部分唯一索引（团队行仅 `talent_id IS NULL` 时唯一）
  - **爬虫 skill `comp-talent-crawler`**（`~/.agents/skills/`）：官方 API 匿名采集（指定赛事/近年轮次按 Div 过滤/全站榜快照三种模式），2.2s 限流 + 指数退避、画像分批补全、断点续采（`_progress.json`）、国家名→ISO 映射；配套 schema v1.0 校验器与 13 源注册表
  - **JSONL 契约 v1.0**（meta→series→contest→team→person）：个人赛与团队赛（`type: team` 行 + members 明细）统一承载，契约见 `docs/competition-v1.0/02`
  - **CompImportService**：按单场赛事全量替换（单事务先删后插 + 聚合重算 rating/奖牌/场次）；空文件/全无效行硬守卫（绝不触发 DELETE，继承 lab V3.1.0 教训）；批内去重、`person.team_name` 自动补建 team、11 条验收用例全绿
  - **查询 API**：`/comp/talents`（keyword/国家/学校/最低积分/段位/5 种排序/分页）、`/comp/talents/{id}`（画像+参赛史）、`/comp/contests`、`/comp/contests/{id}`（个人+团队双榜单）、`/comp/overview`、`/comp/series`、`POST /comp/import/upload`（super_admin，20MB 上限）
  - **前端 4 页面**：概览（统计卡+积分榜 Top10+最近赛事）、搜索（URL 全字段双向同步+400ms 防抖）、选手详情（身份卡+参赛史+积分趋势 ECharts）、赛事详情（个人/团队榜单）；导航接入（competition 解锁、橙系主题、域路径映射）；`system-config` 新增「竞赛人才导入」Tab（拖拽上传+导入报告）
  - **设计文档** `docs/competition-v1.0/`（总览/架构与数据模型/数据源与爬虫Schema/导入接口与标准/API与前端设计 5 份）
  - series 种子 13 个赛事系列（codeforces 启用；用户关注清单 ICPC/IOI/IMO/IPhO/IMC/CTF/Kaggle/RoboCup/ASC/SC/ISC 按 M2/M3 分期放开）
- 后端测试 16 个（导入验收 11 + API 5），全量 827 通过

### Changed

- `AGENTS.md`：竞赛域结构与关键文件、BACKEND_PORT、HTTP 例外清单、V4.0.0 版本说明
- `README.md` 版本号 V4.0.0
- mypy 基线再生（竞赛域 SQLAlchemy Column 类噪音与存量同类模式一并入线，gate 1377 通过）
- 版本号 3.1.0 → 4.0.0（pyproject.toml、package.json、config.py、uv.lock）

### Removed

- 竞赛演示页（`competition-demo-page.tsx` 及其路由）：正式页面上线后退役

## [3.1.0] - 2026-07-18

### Added

- **失败采集任务重跑**：`POST /collect/tasks/{id}/rerun` —— 将 failed/cancelled 任务重置为 pending 并保留 `last_completed_phase` checkpoint 续跑，无需全量重采（`api/collect.py:398-446`）
- **采集任务全局完成通知**：`useCollectTaskNotifier` 挂载 MainLayout，任务 running→completed/failed/cancelled 跃迁时全局 notification，离开配置页也可感知
- **学术搜索 URL 全字段状态同步**：关键词/5 个筛选器/排序/分页全部进 URL，分享链接、刷新、前进/后退均可恢复；顺带修复筛选器旧状态滞后一拍、`country_code`/`tech_domain_id` 后端支持但前端未传的死筛选
- **登录/注册页固定学术域主题**：`AcademicThemeScope`（嵌套 ConfigProvider + 作用域 CSS 变量），不再随用户当前域变色
- 基础设施 hook/工具：`usePolling`（声明式轮询，unmount 清理、无硬上限、回页恢复）、`useCollectTaskNotifier`、`navigateBack`（返回兜底）、dev-gated `utils/logger`
- 回归测试：GitHub 401 拉黑/限速推导、collector 失败计数、架构检查规则、日志 task_id 上下文（`tests/domains/open_source/`、`test_check_architecture.py`、`test_logging_context.py`）
- 采集链路 Prometheus 指标落地：`COLLECTION_TASKS_ACTIVE/TOTAL/ERRORS` 在任务开始/完成/取消/失败四路径埋点

### Changed

- **三域主题切换实时生效**：`ThemedConfigProvider` 订阅 `domainStore` 重建 AntD token（此前启动时一次性固化，切域后组件仍停留学术蓝）
- **前端响应式**：统计/筛选栅格补断点（桌面端不变）、`MainLayout` 窄屏折叠（`Grid.useBreakpoint`）、Hero 标题改 `clamp()`
- **GenealogyGraph 布局动态化**：ResizeObserver 实测容器宽度替代写死 900px；单 tier 超 12 节点折叠为 Top N + 聚合节点（点击展开）；最右节点标签内翻；toolbox 一键复位；移除 roam 错位的 HTML 色带
- **CollectConfigTab 拆分**：1140 行 / cx=142 → 200 行 / cx=1（`useCollectConfig` hook + 9 个子组件）
- 轮询收敛：`useCollectConfig` 四处内联 `setInterval+setTimeout 封顶` 改为 `usePolling`（终态即停、离开页面不再 setState、回页面自动恢复）
- 登录后回跳原页面：`ProtectedRoute` 携带 `state={{ from: location }}`
- 详情页体验：区分 error/404 并带重试、加载期不再闪空态、返回按钮 `navigateBack` 兜底（分享链接打开不再退出站点）、研究方向 Tag 可点击跳转搜索
- 反馈闭环：6 处静默 catch 补用户提示、admin 审核「拒绝」加 Popconfirm、搜索空态补清除筛选行动
- `_is_postgres()` 下沉 `app/core/database.py`（消除跨域 3 份复制）；族谱/预取后台任务下沉 Service 层（`genealogy_background_service`、`prefetch_background_service`），API 层不再触碰 `AsyncSessionLocal`
- rerun 端点 ORM 操作下沉 `CollectService.reset_task_for_rerun()`
- 前端 26 处 `console.error` 替换为 dev-gated logger；前后端删除 75 处复述式注释

### Fixed

- **OpenAlex 批量拉取静默丢一半数据**：`batch_size` 钳制 ≤50 与 `per_page=50` 对齐（`data_fetchers.py:665,808`）
- **空/全无效 JSONL 导入清空实验室数据**：`deduped` 为空且存在非空行时拒绝替换（`lab_import_service.py:184-197`）
- **GitHub 401 不轮换 token**：401 拉黑坏 token 不再选中、不再无意义睡到 reset；修正换 token 守卫把未记录 token 当 0 配额的问题
- **contributor 阶段静默完成**：失败计数生效，零产出任务标记 `failed` 而非 `completed`（消除"成功假象"）
- Phase 1 重跑不跳过已完成子任务（浪费 API 配额）
- 死配置接线：`GITHUB_RATE_LIMIT`（限速间隔按限额×token 池推导）、`COLLECT_SUBTASK_RETRY_COUNT/BASE_WAIT`、`BACKEND_PORT`（代理自检不再写死 8003）
- school normalizer 吞异常无日志；`github_client` 404 静默返回 `{}`（改返回 None）；OpenAlex client 5xx 不重试；主页抓取 SSRF 防护（私网/回环拦截）与 URL 校验顺序
- 架构检查器双盲区：banned-name 检查前移到 `app.core.` 白名单豁免之前（api 层 `AsyncSessionLocal` 不再漏检）、lab 域纳入跨域隔离检查
- 前端：`/pools/:id` 死路由点击、登录回跳丢失、跨域进学术详情主题不切回、人才池/收藏列表等加载静默失败

## [3.0.0] - 2026-07-14

### Added

- **AI Native 人才库**（`domains/lab/`）：全新独立第四域，覆盖全球顶尖 AI 实验室（Stanford AI Lab、MIT CSAIL、LAMDA 等）的研究人员
  - 独立 `lab_talent` 表 + `lab_info` 实验室元数据表（跨域隔离铁律，不复用 `core_talent`）
  - 数据来源：通过 hermes agent 调用 `ai-lab-talent-crawler` skill 采集实验室官网人员数据，产出 JSONL
  - 双导入入口：hermes API 推送（静态 API Key 鉴权）+ 管理员手动上传（super_admin）
  - 导入策略：按实验室全量替换（单事务原子性），支持新版 JSONL 格式（`type: lab` 元数据头 + `type: person` 人才行）
  - 角色映射：`role_section` → `role_type`（教授/在读学生/博后/已毕业）+ `academic_level`（博士/硕士/学士）双维度
  - 主页预览：详情页内嵌个人主页（后端代理抓取+清洗 HTML，绕过 X-Frame-Options）；批量预抓取+缓存+进度显示
  - 前端：概览页（实验室卡片+角色构成条）、实验室详情页（Profile Header + 角色 Tabs + 人才卡片网格）、人才详情页（Tabs 分区 + 主页内嵌预览）
  - 导航：`AI Native` 域入口，与学术人才/开源人才并列

### Changed

- 版本号更新至 3.0.0（pyproject.toml、package.json、config.py、AGENTS.md）
- 开源人才详情页返回按钮：`navigate('/opensource')` → `navigate(-1)`，保持搜索状态
- 导航栏域标签：实验室域从"AI 实验室"改为"AI Native"
- 研究方向导入清洗：过滤 HTML 实体（`&nbsp`）、句子碎片、人名、超长项

### Fixed

- 测试套件全量通过（CI 修复链路）：httpx API 适配、测试 DATABASE_URL 注入、mypy baseline 跨平台路径归一化、架构 baseline 跨平台哈希、mypy_gate 路径漂移、npm audit 9 个依赖漏洞
- 族谱计算 PostgreSQL 堆栈溢出（超大 IN 子句 → 临时表 + anti-join）
- 开源人才库管理员访问权限（repo_config 只读接口降权）
- 迁移链冲突（废弃 lw_* 表清理脚本 + migrate.bat 自动检测）
- 主页预览 UTF-16 编码、重定向跟随、bs4 Tag API 兼容

## [2.2.0] - 2026-06-16

### Added

- **学术族谱人才洞察** (`domains/academic/services/genealogy_service.py`, `influence_service.py`)
  - 新增 `genealogy_edge`（学术族谱边）与 `talent_influence_score`（影响力评分）两张表及 Alembic 迁移 `049_add_genealogy_tables`
  - 影响力评分算法：h_index / citation / works / collaboration / bridge 五维加权，输出 composite_score 与 tier 分层（tier1 学术领军 / tier2 中坚学者 / tier3 青年才俊 / tier4 新锐）
  - 导师-学生传承关系推断：基于 `raw_work.raw_json` 的 authorships 位置模式、同机构、重复合作、时间跨度等信号累加置信度
  - API：`GET /api/v1/talents/{talent_id}/genealogy`（族谱网络查询）、`POST /api/v1/talents/genealogy/sync`（同步触发）
  - 前端：`GenealogyGraph.tsx`（ECharts 分层力导向图），集成至人才详情页
  - 设计依据：`docs/academic-genealogy-v2.2.0-design.md`

- **运维脚本** (`scripts/ops/deploy_database.py`, `deploy_database.sh`)
  - 数据库部署自动化

- **采集配置增强**：前端 `collect-config-tab` 新增配置项（+95 行）

### Changed

- **采集数据提取层重构** (`services/data_fetchers.py`，+130 行)：扩展原始数据字段提取逻辑
- **标准化层调整**：`AuthorNormalizer`、`SchoolNormalizer` 适配新增字段
- **采集流水线阶段调整**：Phase 1（论文采集）、Phase 4/5（学校/作者标准化）、Phase 10（学校统计）流程优化
- **核心配置扩展** (`core/config.py`，+14 行)：新增族谱相关配置项

### Fixed

- **历史迁移健壮性修复**：`012`/`022`/`025` 迁移将 `information_schema` 元数据查询替换为 `pg_catalog.pg_attribute` / `pg_constraint`，避免在权限受限或 schema 视图异常的环境下重复执行失败

## [2.1.1] - 2026-05-29

### Fixed

- Phase 10 `is_critical=False` 导致的数据一致性风险
- `favourite`/`favorite` 拼写混用统一为 `favorite`
- `open_source_service.py` 纯委托门面消除
- 物化视图刷新增加 Prometheus 指标采集
- 清理死代码：`SimilarityCalculator`、`generate_reasons` 等零引用符号

### Changed

- 前端 localStorage 操作封装为 `storageService`

## [2.1.0] - 2026-05-29

### Added

- **隐私合规声明** (`domains/shared/api/privacy.py`, `privacy_service.py`)
  - 用户隐私协议与数据使用声明页面 (`privacy-policy-page.tsx`, `terms-of-use-page.tsx`)
  - Cookie / 本地存储使用提示与同意管理 (`StorageConsentBanner.tsx`)
  - 用户账号表增加隐私同意字段，支持 GDPR/PIPL 合规追踪

- **新增"我的建议"模块** (`domains/shared/api/suggestion.py`, `suggestion_service.py`)
  - 用户可向平台提交功能建议、数据纠错、体验反馈
  - 支持截图附件上传（PNG/JPEG/GIF/WebP，最大 5MB）
  - 后端：建议表设计 + 分类标签 + 处理状态流转（open/in_progress/resolved/closed）
  - 前端：建议入口 + 表单提交 + 历史建议列表 + 管理员回复

- **开源人才库支持人才数据导出** (`domains/open_source/api/developers.py`)
  - 开源域开发者列表/详情页增加导出按钮，支持 Excel / CSV 格式
  - 导出字段：开发者基本信息、仓库统计、技术标签、活跃度评分
  - 导出文件附带法律声明水印，仅限管理员操作

- **用户管理模块优化** (`domains/shared/api/permissions.py`, `user_activity_service.py`)
  - 管理员后台用户列表增强：支持按角色/状态/注册时间筛选与排序
  - 用户详情页新增活动记录 Drawer：登录历史、操作日志、权限变更统一时间线展示
  - 引入 `UserActivityService` 投影层：基于 `audit_operation_log` 统一聚合用户活动事件
  - `iam_user_account` 增加 `created_at` 索引，优化注册时间筛选性能

### Changed

- **权限矩阵细化**：区分超级管理员与管理员的权限边界
  - 角色变更、用户创建等敏感操作仅限超级管理员
  - 开源仓库配置、系统配置等关键接口提升至超级管理员权限

### Technical Debt

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
