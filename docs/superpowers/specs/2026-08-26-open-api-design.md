# 人才库开放 API（Open API）与鉴权体系设计

**日期**：2026-08-26
**状态**：已确认
**分期**：P1（鉴权 + 管理 + 行业迁移 + 各域只读查询）→ P2（竞赛/实验室导入 + 跨域统一搜索）

## 背景与目标

平台现有五个域的人才数据，但对外 API 只有行业域一把静态 Key 的导入通道。目标：把导入与查询能力以统一契约开放，供自己的 AI Skill 与少量外部工具基于人才库数据做洞察，同时保持跨域隔离铁律与既有安全基线。

**已确认决策**：消费者 = 自有 Skill + 少量外部工具（非平台级多租户）；多 Key + 域级读写 scope；统一 `/api/v1/open-api/*` 命名空间；导入覆盖行业+竞赛+实验室三个 JSONL 域。

## 鉴权体系（P1，shared 域）

### 数据模型（迁移：`shared_api_key` 表）

| 列 | 说明 |
|----|------|
| api_key_id | PK |
| key_name | 备注名（展示与审计用） |
| key_hash | sha256(Key)，明文永不落库 |
| key_prefix | Key 前 8 位（列表展示识别用） |
| scopes | JSONB 数列，如 `["academic:read","industry:write"]` |
| is_active | 吊销/启用 |
| rate_limit_per_minute | 可选 per-Key 限流覆盖（NULL=用全局默认） |
| expires_at | 可选过期时间 |
| last_used_at | 最近使用（校验时异步更新） |
| created_by | FK iam_user_account |

Key 格式：`ak_` + 43 位随机 base62；创建时明文仅显示一次。

### 校验依赖

`shared/api/open_api_auth.py`：
- `require_api_key(scope: str)` FastAPI 依赖：读 `X-API-Key` 头 → sha256 比对（secrets.compare_digest）→ 校验 is_active/expires_at → 校验 scope ∈ scopes → 注入 principal `{"role": "api_agent", "api_key_id", "key_name", "scopes"}`
- 错误契约：未配置 Key 体系/库无 Key → 503；缺失或不匹配 → 401；scope 不足或已吊销 → 403
- 每次校验直查 DB（百级 Key 规模无性能问题），吊销即时生效

### 管理面板（系统配置新 tab，super_admin）

- 创建：输入备注名 + 勾选 scope 矩阵（域 × 读/写）+ 可选限流/过期 → 生成 Key 明文弹窗一次性展示
- 列表：前缀、备注名、scope 标签、状态、限流值、最近使用时间、创建人
- 操作：吊销/启用（即时生效）
- 后端 CRUD 走 shared config 域新 service；仅 super_admin

### 旧 Key 迁移

启动迁移脚本/逻辑：若 `sys_config.INDUSTRY_IMPORT_API_KEY` 存在且 api_key 表无对应记录 → 自动创建一把 `key_name="行业导入(迁移)"`、scopes=`["industry:write"]` 的记录并删除旧 sys_config 项；行业域 `verify_industry_api_key` 改为薄代理调用新依赖（外部 Header 不变，平滑兼容）。

## API 面

### 导入（P2，复用现有 JSONL 导入服务）

| 端点 | scope | 语义 |
|------|-------|------|
| POST /open-api/industry/import | industry:write | 增量 upsert（沿用现契约） |
| POST /open-api/competition/import | competition:write | 单场赛事全量替换导入 |
| POST /open-api/lab/import | lab:write | 实验室人才 JSONL 导入 |

请求体：raw JSONL 文本（Content-Type: application/x-ndjson），沿用各域现有 schema 与导入报告结构。

### 查询（P1，各域新增 api/open_api.py）

每域提供（契约面向外部消费者独立设计，不照抄前端页面 API）：
- `GET /open-api/<domain>/talents`：分页列表 + 各域核心筛选（学术：关键词/技术领域/学校；开源：技术要素/语言/location；竞赛：赛事/年份/奖牌；实验室：实验室/研究方向；行业：岗位/状态/评分区间）
- `GET /open-api/<domain>/talents/{id}`：详情（对齐前端详情页数据形状的核心子集）
- `GET /open-api/<domain>/stats`：域级统计摘要
- scope：`<domain>:read`

**脱敏边界**：外部查询不暴露邮箱等 PII 明细字段（学术 email、联系方式类字段默认剔除，后续如有需要再按 Key 单独授权）。

### 跨域统一搜索（P2，注册表模式）

- shared 定义 `SearchProvider` 协议（`async def search(keyword, filters, limit) -> list[UnifiedTalentSummary]`）与模块级注册表 `shared/services/open_api/registry.py`
- 各域在自身 services 内实现并注册（域→shared 导入合法；shared 不反向导入域——铁律不破）
- `GET /open-api/search/talents?keyword=&domains=academic,opensource`：路由层并行调用注册的 Provider，聚合为统一摘要（姓名/标识/域/主页链接/核心标签），scope 要求所勾选每个域都有 `<domain>:read`

## 治理配套

- **限流**：RateLimitMiddleware 识别 principal.api_key_id 作为限流键；per-Key rate_limit_per_minute 覆盖全局默认
- **审计**：API 调用记审计日志（key_name、端点、状态码、耗时）；管理面板展示每 Key 调用量（近 7 天）
- **监控**：Prometheus `open_api_requests_total{key_name, endpoint, status}` + 延迟直方图
- **文档**：`docs/open-api/01-agent-guide.md`（对接指南：认证头、scope 说明、各端点示例 curl）；Swagger 按域分组 tag "Open API"

## 错误处理契约

沿用项目契约：导入/查询错误返回统一 JSON 结构（detail 含错误码与信息）；429 限流带 Retry-After；不暴露内部堆栈。

## 测试策略

- 鉴权：单测 scope 矩阵（有/无/吊销/过期/错误 Key）、迁移幂等
- 契约：每域 open-api 端点的响应 schema 契约测试（防破坏外部消费者）
- 跨域搜索：注册表 Provider 聚合行为（含部分域失败降级）
- 架构：check_architecture 全绿（open_api 路由仅 import 本域 Service + shared）

## 不做的事

- ❌ OAuth2/客户端凭证流程（自有工具场景过重）
- ❌ 多租户/自助申请/计费
- ❌ 学术/开源域导入 API（采集器驱动，语义不适用）
- ❌ PII 字段对外开放（默认脱敏）

## 风险与对策

| 风险 | 对策 |
|------|------|
| 外部契约被前端迭代破坏 | 独立契约 + 契约测试锁定 |
| Key 泄露 | 吊销即时生效 + per-Key 限流 + 审计可查 |
| 跨域搜索拖垮域服务 | 并行 + 每域结果上限 + 超时降级 |
