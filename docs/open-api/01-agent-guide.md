# 开放 API 对接指南（P1 — 查询）

> 适用版本：v5.1+（开放 API P1）。本文面向外部工具与 AI Skill 的开发者，说明如何基于人才库数据做查询洞察。

## 认证

所有开放 API 使用 `X-API-Key` 请求头：

```bash
curl -H "X-API-Key: ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
     "http://<host>:8003/api/v1/open-api/academic/talents?page_size=5"
```

- Key 由超级管理员在「系统配置 → API Key 管理」创建，明文仅创建时展示一次
- 每个 Key 绑定一组 scope（域 × 读/写），如 `academic:read` + `industry:write`
- 错误语义：缺失/无效 Key → `401`；Key 有效但缺少所需 scope → `403`；已吊销 → `401`
- 限流：按 Key 独立计数（滑动窗口 1 分钟），超限返回 `429` + `Retry-After` 头；per-Key 限额可在管理面板配置

## 统一响应契约

列表端点统一 envelope：

```json
{
  "items": [...],
  "total": 50062,
  "page": 1,
  "page_size": 20
}
```

分页参数：`page`（≥1）、`page_size`（1~100，默认 20）。

## 查询端点一览（scope: `<域>:read`）

| 域 | 列表 | 详情 | 统计 |
|----|------|------|------|
| 学术 | `GET /open-api/academic/talents` | `/talents/{id}` | `/stats` |
| 开源 | `GET /open-api/open-source/talents` | `/talents/{id}` | `/stats` |
| 竞赛 | `GET /open-api/competition/talents` | `/talents/{id}` | `/stats` |
| 实验室 | `GET /open-api/lab/talents` | `/talents/{id}` | `/stats` |
| 行业 | `GET /open-api/industry/talents` | `/talents/{id}` | `/stats`（岗位粒度） |

（完整前缀 `/api/v1`；Swagger 见 `http://<host>:8003/docs` 的 "Open API — *" 分组）

### 各域列表筛选参数

- **学术**：`keyword`（姓名/关键词）、`role_type`、`min_citations`
- **开源**：`keyword`、`tech_elements`（技术要素，任一命中）、`languages`、`location`、`min_stars`
- **竞赛**：`keyword`、`country_code`、`school`、`min_rating`、`rank_title`、`sort_by`（rating_desc/contests_desc/medals_desc/recent_desc）
- **实验室**：`keyword`、`parent_lab`、`lab_name`、`role_type`、`research_area`
- **行业**：`keyword`、`position_id`、`min_score`（0-100）、`status`（new/connected/terminated）

### 字段说明

Open API 经 API Key 鉴权，联系方式类字段（email、social_links、blog_url、profile_url、orcid 等）正常透出，便于触达候选人。仅内部原始负载（如学术域 `extra_data`）不对外。列表字段为各域面向洞察的核心子集（身份、机构、技术标签、学术指标/贡献指标/评分）。

## 示例：洞察 Skill 的典型调用流

```bash
# 1. 看各域数据规模
curl -H "X-API-Key: $KEY" http://localhost:8003/api/v1/open-api/academic/stats

# 2. 按技术要素筛开源人才
curl -H "X-API-Key: $KEY" \
  "http://localhost:8003/api/v1/open-api/open-source/talents?tech_elements=models&min_stars=5000&page_size=50"

# 3. 取竞赛高分选手详情（含参赛史）
curl -H "X-API-Key: $KEY" \
  "http://localhost:8003/api/v1/open-api/competition/talents?min_rating=2400&country_code=CN"
```

## 跨域统一搜索（P2）

`GET /open-api/search/talents`：一次调用并行搜索多个域，返回统一摘要（姓名/标识/域/主页链接/核心标签）。所选每个域都需要对应 `<域>:read` scope。

| 参数 | 说明 |
|------|------|
| keyword | 必填，1~200 字符 |
| domains | 逗号分隔域名；缺省 = 全部已注册域 |
| per_domain | 每域返回条数，默认 5，上限 20 |

```bash
curl -H "X-API-Key: $KEY"   "http://localhost:8003/api/v1/open-api/search/talents?keyword=chen&domains=academic,open_source&per_domain=10"
```

响应含 `items`（聚合结果）、`errors`（单域失败降级，不影响其他域）、`unknown_domains`（拼错的域名透出）。

## 导入通道（P2）

三个 JSONL 域均已开放 API 导入（scope：`<域>:write`），请求体为 raw JSONL 文本（≤20MB，UTF-8）：

| 端点 | 语义 | 额外参数 |
|------|------|---------|
| `POST /open-api/industry/import` | 增量 upsert（空字段不覆盖） | `position_id` 必填、`batch` 可选 |
| `POST /open-api/competition/import` | 单场赛事全量替换（schema v1.0） | 无 |
| `POST /open-api/lab/import` | 按实验室全量替换 | `parent_lab` 必填 |

```bash
# 实验室导入示例
curl -X POST -H "X-API-Key: $KEY"   "http://localhost:8003/api/v1/open-api/lab/import?parent_lab=Stanford%20AI%20Lab"   -H "Content-Type: application/x-ndjson"   --data-binary @lab-talents.jsonl
```

JSONL schema 与管理员手工上传通道完全一致（行业=smart-talent-sourcing 产出、竞赛=comp-talent-crawler 产出、实验室=ai-lab-talent-crawler 产出）；导入报告结构与上传通道一致。

> 旧通道 `POST /industry/import` 继续可用（同一 Key、同一 scope），行为与新端点完全等价。

## 错误码速查

| 状态 | 含义 |
|------|------|
| 401 | 缺失 X-API-Key / Key 无效 / 已吊销 |
| 403 | Key 有效但缺少所需 scope |
| 404 | 资源不存在 |
| 422 | 参数校验失败 |
| 429 | 触发限流（见 Retry-After 头） |
