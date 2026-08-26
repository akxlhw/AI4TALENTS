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

### PII 脱敏

外部查询默认剔除联系方式类字段（email、social_links、blog_url、profile_url、orcid、extra_data）。列表字段为各域面向洞察的核心子集（身份、机构、技术标签、学术指标/贡献指标/评分）。

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

## 导入通道（P2 预告）

行业域现有推送通道（`POST /industry/import`，scope `industry:write`）已并入本 Key 体系；竞赛/实验室导入端点与跨域统一搜索将在 P2 开放。

## 错误码速查

| 状态 | 含义 |
|------|------|
| 401 | 缺失 X-API-Key / Key 无效 / 已吊销 |
| 403 | Key 有效但缺少所需 scope |
| 404 | 资源不存在 |
| 422 | 参数校验失败 |
| 429 | 触发限流（见 Retry-After 头） |
