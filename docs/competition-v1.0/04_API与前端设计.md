# 04 API 与前端设计

> 竞赛人才域 v1.0 —— REST 端点、前端页面、权限、测试策略、里程碑

## 1. REST API（Base: `/api/v1/comp`）

| 端点 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/comp/overview` | GET | 登录 | 概览统计：选手数/赛事数/系列数/奖牌选手数/国家数 + 积分榜 Top 10 预览 + 最近赛事 Top 5 |
| `/comp/talents` | GET | 登录 | 选手列表。参数：`keyword`（handle/real_name 模糊）、`country_code`、`school`（模糊）、`min_rating`、`rank_title`、`series`（预留，多源后生效）、`sort_by`（rating_desc/rating_asc/contests_desc/medals_desc/recent_desc）、`page`/`page_size` |
| `/comp/talents/{id}` | GET | 登录 | 选手详情：画像 + 聚合 + 参赛史（results 按时间倒序，含 contest 名/名次/award/rating 变动）+ rating 趋势点列 |
| `/comp/contests` | GET | 登录 | 赛事列表。参数：`series_code`、`season`、`keyword`、`year_gte`、`page`/`page_size`，默认 start_time 倒序 |
| `/comp/contests/{id}` | GET | 登录 | 赛事详情 + 榜单（个人赛：results 按 rank 升序含选手摘要；团队赛：团队 results 按 rank 升序含队伍摘要与 members 明细） |
| `/comp/teams` | GET | 登录 | 队伍列表（团队赛系列用）。参数：`series_code`、`school`、`country_code`、`keyword`、`page`/`page_size` |
| `/comp/teams/{id}` | GET | 登录 | 队伍详情：画像 + 队史（各场次成绩）+ 已知成员 |
| `/comp/import` | POST | **super_admin** | JSONL 上传导入（见 [03 文档](03_导入接口与标准.md)） |
| `/comp/series` | GET | 登录 | 系列清单（含各 series 的选手/赛事计数，用于前端筛选器与卡片） |

约定：全部走 Endpoint → Service → Repository 分层（端点不碰 Repository/模型，check_architecture 强制）；响应 DTO 分 Summary/Detail 两档（lab 惯例）。

## 2. 前端设计（替换现有 demo 页）

### 2.1 路由与导航

```
/competition                  概览页（替换 competition-demo-page）
/competition/search           选手搜索页
/competition/talents/:id      选手详情页
/competition/contests/:id     赛事详情页（榜单）
/competition/teams/:id        队伍详情页（团队赛系列上线时启用）
```

- `domainNavItems` 中 competition 去掉 `soon: true`；`domainStore.availableDomains` 加入 `'competition'`
- `DOMAIN_PATH_PREFIXES` 追加 `'/competition': 'competition'`（域主题自动切换）
- 主题色沿用 `domainThemes.competition`（橙系 #DD6B20，demo 页已奠定）
- 目录：`pages/competition/{competition-overview-page.tsx, competition-search-page.tsx, competition-talent-detail-page.tsx, competition-contest-detail-page.tsx, components/}`，复用 lab 域模式：`PageSkeleton`、`EmptyPlaceholder`、`BreadcrumbNav`、Avatar 兜底

### 2.2 页面要点

**概览页**（参照 lab-overview-page，demo 页已验证视觉语言）：
- Hero（渐变 + 标题 + 简介，用 `<DomainHero>` 理念）
- 4 张统计卡（收录选手 / 覆盖赛事 / 系列数 / 金牌选手，响应式 `xs={24} sm={12} lg={6}`）
- 积分榜预览（Top 10：名次圈 + handle + 学校/国家 + rating + 趋势箭头）→ 点击进选手详情
- 最近赛事（Top 5 卡片：赛事名 + 时间 + 冠军）→ 点击进赛事详情
- 数据为空时：对管理员显示「去导入」引导（lab 模式），普通用户显示空态

**选手搜索页**（参照 lab-search-page）：
- 筛选器：关键词 / 国家 / 学校 / 最低积分 / 段位；**筛选条件全字段 URL 同步**（直接采用 V3.1.0 学术搜索的 URL 单一事实源模式，lab 域同款）
- 选手卡片：Avatar 兜底 + handle + 段位 Tag + 学校/国家 + rating 条 + 奖牌计数 + 近 trend
- 空态带「清除筛选」行动

**选手详情页**：
- Header：Avatar + handle（real_name）+ 段位 Tag + 学校/国家 + 当前/最高 rating + 奖牌行（金/银/铜计数）
- 左栏 sticky 身份卡（lab 详情页模式）；右栏 Tabs：
  - 「参赛史」表格：赛事（可点进赛事详情）/ 时间 / 名次 / award Tag / rating±（带涨跌色）
  - 「积分趋势」ECharts 折线迷你图（rating_after 按时间序列，M1 数据够即出，不够则隐藏）
- 数据源外链（profile_url 新窗口）

**赛事详情页**：
- Header：赛事名 + 系列 Tag + 时间/时长 + 源站链接
- 榜单表格：rank（前三奖牌色）/ 选手（可点）/ 学校-国家 / score / rating 变动 / award
- 分页 50/页，rank 升序

**管理导入入口**：`system-config` 页新增「竞赛导入」Tab，复用 `components/lab-import-form.tsx` 的报告展示结构（抽出共享 `ImportReportView`，lab/竞赛两个 form 复用——实现时注意别复制粘贴）。

## 3. 权限

| 角色 | 能力 |
|------|------|
| 未登录 | 无（全局 ProtectedRoute） |
| 登录用户 | 全部读取端点 |
| admin | 同上（M1 无额外能力） |
| super_admin | + `/comp/import` 导入 |

三维权限（学校/国家/技术要素）不映射竞赛域（M1 结论，同 lab）。

## 4. 测试策略

**后端**（`tests/domains/competition/`，PostgreSQL 测试库，conftest 现有体系）：

- `test_comp_import_service.py`：03 文档 §4 的 8 条验收用例（合法/幂等/空文件守卫/批内重复/版本拒收/不一致拒收/替换而非叠加/画像非空合并）
- `test_comp_talent_service.py`：列表筛选/排序/分页、详情参赛史组装、keyword 大小写不敏感
- `test_comp_api.py`：端点鉴权（导入非 super_admin 403）、overview 计数正确性
- 架构检查：`check_architecture.py` 增加 competition 域跨域禁令后全绿

**前端**（vitest）：

- URL 同步逻辑（筛选 → URL → 恢复）
- 选手卡片 Avatar 兜底、rating 条渲染、空态行动按钮
- Playwright E2E 后续补：导入 → 概览 → 详情链路（参照 lab 现有 spec 模式）

## 5. 里程碑拆解

| 里程碑 | 内容 | 验收 |
|--------|------|------|
| **M1.1 骨架** | 4 表迁移 + series 种子 + 模型注册 + 架构禁令追加 | migrate 通过，检查器绿 |
| **M1.2 爬虫** | `comp-talent-crawler` skill：contest.list→standings→user.info→JSONL，含 checkpoint/限流/自检 | 产出示例文件通过 03 全部校验 |
| **M1.3 导入** | CompImportService + 端点 + 导入报告 + 全部验收测试 | 8 条用例全绿 |
| **M1.4 查询 API** | talents/contests/series/overview 端点 | API 测试全绿 |
| **M1.5 前端** | 4 页面 + 导航/主题接入 + demo 页退役 | lint/build/vitest 绿，手测链路通 |
| **M1.6 收尾** | AGENTS.md/README/CHANGELOG 更新、E2E、发布 v4.0.0 | CI 全绿 |

顺序建议：M1.1 → M1.2/M1.3（爬虫与导入可并行，契约为 02 文档）→ M1.4 → M1.5 → M1.6。

## 6. 风险与开放问题

| 风险 | 应对 |
|------|------|
| Codeforces 限流收紧 | 采集配置化（间隔/批次/退避），失败 checkpoint 可续 |
| 榜单巨大（Div2 数万行） | standings 分页拉取；M1 可按 Top 5000 截断并在报告中标注 |
| 选手无学校字段占比高 | 学校列允许为空，前端展示 `-`；不做强制清洗 |
| 多源后 handle 冲突 | source_code 隔离天然解决；跨源合并留给 unified_person_id（M3+ 研究） |
| demo 页真假混排的前科 | 正式页只渲染真实库数据，空库显示空态（评审已记录此教训） |
