# 开源人才库搜索页洞察统计模块 — 设计文档

> 日期：2026-09-07 | 版本：V5.1.0 迭代 | 状态：已确认

## 1. 背景与目标

开源人才库搜索页（`/opensource/search`）当前只有「筛选 + 列表」，招聘人员无法快速评估当前筛选条件下的命中人才结构。本特性在列表下方增加**随检索条件联动的洞察统计面板**，帮助招聘人员判断"这批人值不值得逐个看、能不能触达、来自哪些项目和公司"。

## 2. 需求范围

- 统计对象为**当前检索条件的全部命中集**（跨分页），非当前页
- 首版 4 个维度（核心 4 维）：

| 维度 | 内容 | 招聘价值 |
|------|------|---------|
| 技术要素分布 | tech_tags 各要素命中人数（横向条形图） | 看命中学科结构 |
| 来源仓库分布 | 已配置采集仓库的命中人数 Top 10（横向条形图） | 评估人才项目血统 |
| 可触达率 | 有有效联系方式人数 / 总命中人数（大数字卡） | 招聘漏斗起点 |
| 公司分布 | company Top 10（横向条形图） | 判断竞对挖角空间 |

- **权限**：仅系统管理员可见（`admin` / `super_admin`；普通 `user` 不可见）
- **呈现**：列表下方可折叠面板，默认收起；展开时请求数据；筛选条件变化时若面板处于展开态则自动刷新
- 不做：趋势时间序列、跨域对比、导出洞察（YAGNI）

## 3. 技术方案（方案 A：专用聚合端点）

### 3.1 后端

**端点**：`GET /api/v1/open-source/developers/insights`

- 查询参数与 `GET /developers` 完全一致：`q / tech_elements / languages / location / company / min_stars / is_committer / is_student / has_contact / china_related / top_org / repo_full_names`
- 权限：`require_admin`（自 `app.domains.shared.api.auth_deps` 导入，open_source → shared 为合法依赖方向）
- 路由注册顺序：必须放在 `/developers/{developer_id}` 之前（FastAPI 静态路径优先），与既有 `/developers/ids` 的注释约定一致

**Service**：`OSDeveloperService.get_developer_insights(**kwargs)` → 复用列表的 filters 构建逻辑。

- 将 `list_developers` 中现有的 filters dict 组装段抽取为 `_build_filters(...)` 私有方法，`list_developers` 与 `get_developer_insights` 共用，避免两处漂移。

**Repository**：`DevelopersMixin` 新增 `get_developer_insights(filters) -> dict`，四个聚合共享同一 WHERE 条件组（与 `list_developers` 完全一致，含 `is_visible = true`）：

1. `tech_element_distribution`：`jsonb_array_elements_text(tech_tags::jsonb)` GROUP BY 要素计数（tech_tags 列为 JSON/JSONB variant，与既有 `?|` 用法一致先 cast）
2. `repo_distribution`：`os_contribution ⋈ os_repository ⋈ os_repo_config`，按仓库统计 **distinct developer_id**，仅计入 os_repo_config 中已配置的仓库（"知名项目"= 已配置采集源），Top 10
3. `contactable`：复用 has_contact 判定表达式（主页/邮箱/社媒任一有效），返回 `{contactable: n, total: m}`
4. `company_distribution`：company GROUP BY Top 10，排除 NULL 与空字符串

**响应模型**（新增 schema，放 `schemas/open_source.py`）：

```python
class OSInsightsResponse(BaseModel):
    total: int
    contactable: int                      # 有联系方式人数（前端算百分比）
    tech_element_distribution: dict[str, int]
    repo_distribution: list[dict]         # [{"repo_full_name": str, "developer_count": int}]
    company_distribution: dict[str, int]  # Top 10，按计数降序
```

**边界语义**：semantic / hybrid 搜索模式下，洞察按「筛选条件 + q 关键词过滤」统计（洞察端点不走向量召回）。前端在面板内注明「语义/混合模式下按关键词条件统计」。

### 3.2 前端

- 新组件 `frontend/src/pages/open-source/components/os-insights-panel.tsx`
  - AntD Collapse 单面板，标题「命中人才洞察」，默认收起
  - 展开时调用 `api.openSource.getDeveloperInsights(params)`（`services/api/openSource.ts` 新增方法，参数与 listDevelopers 相同）
  - 内容布局：Row 两列——左：技术要素横向条形图（ECharts，echarts-for-react 现有依赖）；右：来源仓库 Top10 横向条形图；下方：可触达率大数字卡（`n / m（z%）`）+ 公司 Top10 横向条形图
  - `query` 变化时：若面板展开则自动重新请求；收起态不请求
- 接入 `open-source-search-page.tsx`：`<OsSearchResults>` 下方；仅当当前用户角色为 `admin` / `super_admin` 时渲染（读 auth/user store 的 role）
- 面板内一行灰色小字注明语义模式边界

### 3.3 数据流

```
筛选变更 → query state → （面板展开时）GET /developers/insights?同筛选参数
  → Endpoint(require_admin) → Service.get_developer_insights → _build_filters（与列表共用）
  → Repo 聚合（共享 WHERE 条件组）→ OSInsightsResponse → 面板渲染
```

### 3.4 错误处理

- 非 admin 调用：403（依赖层抛出，统一异常处理器转响应）
- 聚合失败：端点不吞异常，前端 catch 显示「洞察加载失败」+ 重试按钮
- 空命中集：返回 total=0 与各空分布，前端展示空态（Empty）

## 4. 测试

- **后端** `tests/domains/open_source/services/test_os_insights.py`：
  - 种子数据覆盖技术要素/仓库贡献/联系方式/公司，验证四个分布数字与 total/contactable
  - 筛选联动：加 `china_related=True` 后分布随之收窄
  - 权限：`user` 角色 403、`admin` 200（走端点层）
- **前端** `os-insights-panel` 渲染测试：mock API，验证展开后请求一次、折叠不请求、角色为 user 时页面不渲染面板（页面级）

## 5. 不做的事（YAGNI）

- 洞察结果缓存（命中集通常 < 万级，聚合查询量级可接受；若实测慢再加）
- 普通用户可见（本期管理员专属）
- 更多维度（地区/在校生/语言栈/影响力分桶/角色分布列入 backlog）
- 洞察导出、定时报表
