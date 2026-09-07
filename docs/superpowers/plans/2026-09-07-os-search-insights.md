# 开源人才库搜索页洞察统计模块 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在开源人才搜索页列表下方新增随筛选条件联动的「命中人才洞察」折叠面板（技术要素分布 / 来源仓库 Top10 / 可触达率 / 公司 Top10），仅 admin 及以上可见。

**Architecture:** 新增专用聚合端点 `GET /api/v1/open-source/developers/insights`（参数与列表完全一致），Repository 层对全部命中集做 4 组聚合 SQL（与列表共享 WHERE 条件组）；前端新增 `OsInsightsPanel` 折叠面板，展开时请求、筛选变化自动刷新。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async（JSONB unnest / LATERAL）+ React 18 + AntD Collapse + echarts-for-react（现有依赖）。

**Spec:** `docs/superpowers/specs/2026-09-07-os-search-insights-design.md`

**关键背景（实现者须知）：**
- 后端工作目录 `backend/`，测试命令 `uv run pytest <path> -q`；前端工作目录 `frontend/`。
- Endpoint 分层铁律：api 只 import Service/schemas/shared 依赖，禁止 import Repository/models。
- `OSDeveloper.tech_tags` 是 `JSON().with_variant(JSONB)` 列； unnest 前需 cast(JSONB) 并用 `jsonb_typeof` 守卫非标量数组（参照 `repositories/open_source/advanced.py` get_stats 的 raw SQL 先例）。
- `os_developer_service.py` 的 `list_developers` 现有 filters 组装段（约 100-119 行）本次抽为 `_build_filters`。
- `api/developers.py` 中 `/developers/ids` 注册在 `/developers/{developer_id}` 之前（静态路径优先），新端点紧跟其后。
- 前端 `useAuth()`（`src/contexts/AuthContext.tsx`）已暴露 `isAdmin`（admin || super_admin），搜索页第 18 行已在用。
- ECharts 用法参照 `src/pages/lab/components/lab-distribution-chart.tsx`（`import ReactECharts from 'echarts-for-react'`）。

---

### Task 1: 后端 Schema — OSInsightsResponse

**Files:**
- Modify: `backend/app/domains/open_source/schemas/open_source.py`（追加到文件末尾）

- [ ] **Step 1: 追加 schema**

在 `schemas/open_source.py` 末尾（保持既有分组注释风格）追加：

```python
# ============= Search Insights =============


class OSRepoInsightItem(BaseModel):
    """单仓库的命中开发者数。"""

    repo_full_name: str
    developer_count: int


class OSInsightsResponse(BaseModel):
    """命中人才洞察（随筛选条件联动的聚合统计，仅管理员可见）。"""

    total: int
    contactable: int  # 有有效联系方式人数（主页/邮箱/社媒任一）
    tech_element_distribution: dict[str, int]
    repo_distribution: list[OSRepoInsightItem]
    company_distribution: dict[str, int]
```

- [ ] **Step 2: 验证导入**

Run: `cd backend && uv run python -c "from app.domains.open_source.schemas.open_source import OSInsightsResponse, OSRepoInsightItem; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/open_source/schemas/open_source.py
git commit -m "feat(open-source): insights 响应 schema"
```

---

### Task 2: Repository 聚合查询（TDD）

**Files:**
- Modify: `backend/app/domains/open_source/repositories/open_source/developers.py`
- Test: `backend/tests/domains/open_source/services/test_os_insights.py`（新建）

**Context:** `developers.py` 已 import `and_, or_, func, exists, not_, select, cast, Text, JSONB, pg_array`，`has_contact` 判定表达式当前内联在 `list_developers` 约 96-108 行。

- [ ] **Step 1: 写失败测试**

新建 `backend/tests/domains/open_source/services/test_os_insights.py`：

```python
"""Tests for OS developer search insights aggregation (repo layer)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.open_source.models.open_source import (
    OSContribution,
    OSDeveloper,
    OSRepoConfig,
    OSRepository,
)
from app.domains.open_source.repositories.open_source import OpenSourceRepository


def _dev(
    github_login: str,
    github_id: int,
    *,
    name: str | None = None,
    company: str | None = None,
    tech_tags: list[str] | None = None,
    email: str | None = None,
) -> OSDeveloper:
    return OSDeveloper(
        github_login=github_login,
        github_id=github_id,
        name=name or github_login,
        company=company,
        tech_tags=tech_tags or ["ai"],
        primary_languages=["Python"],
        total_stars_received=0,
        email=email,
        is_visible=True,
    )


async def _seed(test_session: AsyncSession) -> None:
    test_session.add(
        OSRepoConfig(repo_config_id=1, repo_full_name="pytorch/pytorch", tech_element=["ai"])
    )
    repo = OSRepository(repo_id=1, developer_id=0, full_name="pytorch/pytorch", name="pytorch")
    test_session.add(repo)
    devs = [
        _dev("d1", 501, company="Google", tech_tags=["ai", "systems"], email="a@b.com"),
        _dev("d2", 502, company="Google", tech_tags=["ai"]),
        _dev("d3", 503, company="SomeSmallCo", tech_tags=["robotics"], email="c@d.com"),
    ]
    test_session.add_all(devs)
    # d1、d2 对 pytorch/pytorch 有贡献；d3 没有
    test_session.add_all(
        [
            OSContribution(
                contribution_id=1, developer_id=501, repo_id=1, commits_count=10
            ),
            OSContribution(
                contribution_id=2, developer_id=502, repo_id=1, commits_count=5
            ),
        ]
    )
    await test_session.commit()


@pytest.mark.asyncio
async def test_insights_distributions(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    result = await repo.get_developer_insights({})

    assert result["total"] == 3
    assert result["contactable"] == 2  # d1、d3 有 email
    assert result["tech_element_distribution"] == {"ai": 2, "robotics": 1, "systems": 1}
    assert result["repo_distribution"] == [
        {"repo_full_name": "pytorch/pytorch", "developer_count": 2}
    ]
    assert result["company_distribution"] == {"Google": 2, "SomeSmallCo": 1}


@pytest.mark.asyncio
async def test_insights_follow_filters(test_session: AsyncSession) -> None:
    await _seed(test_session)
    repo = OpenSourceRepository(test_session)

    result = await repo.get_developer_insights({"company": "Google"})

    assert result["total"] == 2
    assert result["contactable"] == 1
    assert result["company_distribution"] == {"Google": 2}
    assert result["repo_distribution"][0]["developer_count"] == 2
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/open_source/services/test_os_insights.py -q 2>&1 | tail -3`
Expected: FAIL，`AttributeError: 'OpenSourceRepository' object has no attribute 'get_developer_insights'`

- [ ] **Step 3: 抽取联系条件 + 实现聚合**

在 `developers.py` 中，把 `list_developers` 里内联的 `contact_cond` 表达式抽为模块级函数（供列表与洞察共用）：

```python
def _contact_condition() -> Any:
    """有效联系方式：个人主页 / 邮箱 / 社媒任一；空串与空 JSON 视为无效。"""
    return or_(
        and_(OSDeveloper.blog_url.isnot(None), OSDeveloper.blog_url != ""),
        and_(OSDeveloper.email.isnot(None), OSDeveloper.email != ""),
        and_(
            OSDeveloper.social_links.isnot(None),
            cast(OSDeveloper.social_links, Text).notin_(("{}", "null")),
        ),
    )
```

`list_developers` 中的 `contact_cond = or_(...)` 整段替换为 `contact_cond = _contact_condition()`（保留原注释）。

在 `DevelopersMixin` 中新增方法：

```python
    async def get_developer_insights(self, filters: dict[str, Any]) -> dict[str, Any]:
        """对筛选命中全集做聚合统计（技术要素/来源仓库/可触达率/公司）。

        WHERE 条件组与 list_developers 完全一致。
        """
        conditions = self._build_list_conditions(filters)
        base_where = and_(*conditions)

        # 技术要素分布（JSONB unnest + 非标量数组守卫）
        tags_jsonb = cast(OSDeveloper.tech_tags, JSONB)
        safe_tags = case(
            (func.jsonb_typeof(tags_jsonb) == "array", tags_jsonb),
            else_=cast(text("'[]'"), JSONB),
        )
        te = func.jsonb_array_elements_text(safe_tags).table_valued("te")
        te_stmt = (
            select(te.c.te, func.count())
            .select_from(OSDeveloper)
            .join(te, true())
            .where(base_where)
            .group_by(te.c.te)
        )
        tech_dist = {row[0]: row[1] for row in (await self.session.execute(te_stmt)).all()}

        # 来源仓库分布（仅已配置采集的仓库，distinct 开发者，Top 10）
        id_subq = select(OSDeveloper.developer_id).where(base_where).scalar_subquery()
        repo_dist_stmt = (
            select(
                OSRepository.full_name,
                func.count(func.distinct(OSContribution.developer_id)),
            )
            .select_from(OSContribution)
            .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
            .join(OSRepoConfig, OSRepository.full_name == OSRepoConfig.repo_full_name)
            .where(OSContribution.developer_id.in_(id_subq))
            .group_by(OSRepository.full_name)
            .order_by(func.count(func.distinct(OSContribution.developer_id)).desc())
            .limit(10)
        )
        repo_dist = [
            {"repo_full_name": row[0], "developer_count": row[1]}
            for row in (await self.session.execute(repo_dist_stmt)).all()
        ]

        # 总数 / 可触达数
        total = await self.session.scalar(
            select(func.count()).select_from(OSDeveloper).where(base_where)
        )
        contactable = await self.session.scalar(
            select(func.count())
            .select_from(OSDeveloper)
            .where(base_where, _contact_condition())
        )

        # 公司 Top 10
        company_stmt = (
            select(OSDeveloper.company, func.count())
            .where(
                base_where,
                OSDeveloper.company.isnot(None),
                OSDeveloper.company != "",
            )
            .group_by(OSDeveloper.company)
            .order_by(func.count().desc())
            .limit(10)
        )
        company_dist = {
            row[0]: row[1] for row in (await self.session.execute(company_stmt)).all()
        }

        return {
            "total": total or 0,
            "contactable": contactable or 0,
            "tech_element_distribution": tech_dist,
            "repo_distribution": repo_dist,
            "company_distribution": company_dist,
        }
```

同时把 `list_developers` 的条件组组装段（从 `conditions: list[Any] = [OSDeveloper.is_visible.is_(True)]` 到 `china_related`/`top_org` 等全部 `conditions.append` 段，不含排序/分页）抽为私有方法 `_build_list_conditions(self, filters: dict[str, Any]) -> list[Any]`，`list_developers` 开头改为 `conditions = self._build_list_conditions(filters)`。注意保留所有既有条件分支（q/tech_elements/languages/location/company/min_stars/is_committer/is_student/has_contact/china_related/top_org/repo_full_names）原样搬入。

`text` 与 `case` 需补入 import：`from sqlalchemy import ..., case, text`（该行已有 Text/and_ 等，注意区分大小写 `Text` 与 `text` 都要）。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/domains/open_source/services/test_os_insights.py -q 2>&1 | tail -3`
Expected: `2 passed`

- [ ] **Step 5: 回归既有开源域测试**

Run: `cd backend && uv run pytest tests/domains/open_source/ tests/modules/open_source/ -q 2>&1 | tail -2`
Expected: 全部 passed（`_build_list_conditions` 抽取无行为变化）

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/open_source/repositories/open_source/developers.py backend/tests/domains/open_source/services/test_os_insights.py
git commit -m "feat(open-source): 开发者命中集聚合查询（insights repo 层）"
```

---

### Task 3: Service 层与门面

**Files:**
- Modify: `backend/app/domains/open_source/services/os_developer_service.py`
- Modify: `backend/app/domains/open_source/services/open_source_service.py`

- [ ] **Step 1: 抽取 `_build_filters` 并新增 `get_developer_insights`**

`os_developer_service.py` 中，将 `list_developers` 的 filters dict 组装段（约 100-119 行，`if q: filters["q"] = q` 到 `repo_full_names` 结束）抽为：

```python
    @staticmethod
    def _build_filters(
        q: str = "",
        tech_elements: list[str] | None = None,
        languages: list[str] | None = None,
        location: str | None = None,
        company: str | None = None,
        min_stars: int | None = None,
        is_committer: bool | None = None,
        is_student: bool | None = None,
        has_contact: bool | None = None,
        china_related: bool | None = None,
        top_org: bool | None = None,
        repo_full_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """列表/洞察共用的筛选 dict 组装。"""
        filters: dict[str, Any] = {}
        if q:
            filters["q"] = q
        if tech_elements:
            filters["tech_elements"] = tech_elements
        if languages:
            filters["languages"] = languages
        if location:
            filters["location"] = location
        if company:
            filters["company"] = company
        if min_stars is not None:
            filters["min_stars"] = min_stars
        if is_committer is not None:
            filters["is_committer"] = is_committer
        if is_student is not None:
            filters["is_student"] = is_student
        if has_contact is not None:
            filters["has_contact"] = has_contact
        if china_related is not None:
            filters["china_related"] = china_related
        if top_org is not None:
            filters["top_org"] = top_org
        if repo_full_names is not None:
            filters["repo_full_names"] = repo_full_names
        return filters
```

`list_developers` 签名不变，函数体开头改为：

```python
        filters = self._build_filters(
            q=q,
            tech_elements=tech_elements,
            languages=languages,
            location=location,
            company=company,
            min_stars=min_stars,
            is_committer=is_committer,
            is_student=is_student,
            has_contact=has_contact,
            china_related=china_related,
            top_org=top_org,
            repo_full_names=repo_full_names,
        )
```

新增方法（紧跟 `list_developers` 之后）：

```python
    async def get_developer_insights(self, **kwargs: Any) -> dict[str, Any]:
        """命中集聚合洞察。kwargs 与 list_developers 的筛选参数一致
        （sort_by/page/page_size 不适用，忽略）。"""
        filters = self._build_filters(**kwargs)
        return await self.repo.get_developer_insights(filters)
```

- [ ] **Step 2: 门面转发**

`open_source_service.py` 的 Developer 区段（`list_developers` 转发方法附近）新增：

```python
    async def get_developer_insights(self, **kwargs: Any) -> dict[str, Any]:
        return await self._developer.get_developer_insights(**kwargs)
```

- [ ] **Step 3: 验证**

Run: `cd backend && uv run python -c "from app.domains.open_source.services.open_source_service import OpenSourceService; print('ok')"`
Expected: 输出 `ok`

Run: `cd backend && uv run pytest tests/domains/open_source/ -q 2>&1 | tail -2`
Expected: 全部 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/open_source/services/os_developer_service.py backend/app/domains/open_source/services/open_source_service.py
git commit -m "feat(open-source): insights service 层（filters 组装抽取共用）"
```

---

### Task 4: API 端点（TDD，权限）

**Files:**
- Modify: `backend/app/domains/open_source/api/developers.py`
- Test: `backend/tests/domains/open_source/services/test_os_insights.py`（追加）

- [ ] **Step 1: 追加端点测试**

向 `test_os_insights.py` 追加（文件头部补 import：`from httpx import AsyncClient`）：

```python
@pytest.mark.asyncio
async def test_insights_endpoint_forbidden_for_normal_user(
    client: AsyncClient, test_user
) -> None:
    r = await client.get("/api/v1/open-source/developers/insights")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_insights_endpoint_admin_ok(
    client: AsyncClient, test_session: AsyncSession, mock_admin_user
) -> None:
    await _seed(test_session)
    r = await client.get("/api/v1/open-source/developers/insights")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["contactable"] == 2
    assert body["tech_element_distribution"]["ai"] == 2
```

（`test_user` / `mock_admin_user` 为 conftest 既有 fixture；若 `client` fixture 的鉴权覆盖方式不同，参照 `tests/domains/shared/test_open_api_query_endpoints.py` 的既有写法对齐。）

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/open_source/services/test_os_insights.py -q 2>&1 | tail -3`
Expected: 两个新用例 FAIL（404 或鉴权不符）

- [ ] **Step 3: 实现端点**

`api/developers.py` 顶部 import 追加：

```python
from app.domains.open_source.schemas.open_source import OSInsightsResponse
from app.domains.shared.api.auth_deps import require_admin
```

在 `/developers/ids` 端点之后、`/developers/{developer_id}` 之前新增：

```python
@router.get("/developers/insights", response_model=OSInsightsResponse)
async def get_developer_insights(
    q: str = Query("", description="Keyword search"),
    tech_elements: list[str] | None = Query(None),
    languages: list[str] | None = Query(None),
    location: str | None = Query(None),
    company: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
    is_committer: bool | None = Query(None),
    is_student: bool | None = Query(None),
    has_contact: bool | None = Query(None),
    china_related: bool | None = Query(None),
    top_org: bool | None = Query(None),
    repo_full_names: list[str] | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
    _admin: dict = Depends(require_admin),
) -> OSInsightsResponse:
    """命中集聚合洞察（仅 admin 及以上）。

    semantic/hybrid 模式下按关键词等价条件统计（不走向量召回）。
    """
    service = OpenSourceService(session)
    result = await service.get_developer_insights(
        q=q,
        tech_elements=tech_elements,
        languages=languages,
        location=location,
        company=company,
        min_stars=min_stars,
        is_committer=is_committer,
        is_student=is_student,
        has_contact=has_contact,
        china_related=china_related,
        top_org=top_org,
        repo_full_names=repo_full_names,
    )
    return OSInsightsResponse(**result)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/domains/open_source/services/test_os_insights.py -q 2>&1 | tail -3`
Expected: `4 passed`

- [ ] **Step 5: 质量门禁**

Run: `cd backend && uv run ruff check app tests && uv run black --check app tests 2>&1 | tail -1 && uv run python scripts/ops/mypy_gate.py 2>&1 | tail -1 && uv run python scripts/check_architecture.py 2>&1 | tail -1`
Expected: 全部 PASS（black 若报重排则先 `uv run black app tests` 再提交）

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/open_source/api/developers.py backend/tests/domains/open_source/services/test_os_insights.py
git commit -m "feat(open-source): /developers/insights 聚合洞察端点（admin 专属）"
```

---

### Task 5: 前端 API 方法与类型

**Files:**
- Modify: `frontend/src/services/api/openSource.ts`

- [ ] **Step 1: 追加类型与方法**

`openSource.ts` 中追加（`OSSearchFilters` 接口之后）：

```typescript
export interface OSRepoInsightItem {
  repo_full_name: string
  developer_count: number
}

export interface OSInsightsResponse {
  total: number
  contactable: number
  tech_element_distribution: Record<string, number>
  repo_distribution: OSRepoInsightItem[]
  company_distribution: Record<string, number>
}
```

在 `openSource` API 对象中（`listDevelopers` 方法附近）新增：

```typescript
  getDeveloperInsights: (params?: Record<string, unknown>) =>
    apiClient.get<OSInsightsResponse>('/open-source/developers/insights', { params }),
```

- [ ] **Step 2: 验证类型**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api/openSource.ts
git commit -m "feat(open-source): insights API 方法与类型"
```

---

### Task 6: 前端洞察面板组件

**Files:**
- Create: `frontend/src/pages/open-source/components/os-insights-panel.tsx`
- Test: `frontend/src/pages/open-source/components/os-insights-panel.test.tsx`
- Modify: `frontend/src/pages/open-source/open-source-search-page.tsx`

- [ ] **Step 1: 写组件测试（先看失败）**

新建 `os-insights-panel.test.tsx`：

```tsx
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const insightsMock = vi.fn()

vi.mock('../../../services/api', () => ({
  api: {
    openSource: {
      getDeveloperInsights: (p: unknown) => insightsMock(p),
    },
  },
}))

import OsInsightsPanel from './os-insights-panel'
import type { OSSearchQuery } from '../../../types'

const baseQuery: OSSearchQuery = { q: '', page: 1, page_size: 20 }

describe('OsInsightsPanel', () => {
  beforeEach(() => {
    insightsMock.mockReset()
    insightsMock.mockResolvedValue({
      data: {
        total: 3,
        contactable: 2,
        tech_element_distribution: { ai: 2, robotics: 1 },
        repo_distribution: [{ repo_full_name: 'pytorch/pytorch', developer_count: 2 }],
        company_distribution: { Google: 2, SomeSmallCo: 1 },
      },
    })
  })

  it('does not fetch while collapsed, fetches on expand', async () => {
    render(<OsInsightsPanel query={baseQuery} />)
    expect(insightsMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText(/命中人才洞察/))
    await waitFor(() => expect(insightsMock).toHaveBeenCalledTimes(1), { timeout: 15000 })
    expect(await screen.findByText('2 / 3', undefined, { timeout: 15000 })).toBeTruthy()
    expect(screen.getByText('66.7%')).toBeTruthy()
  }, 30000)
})
```

Run: `cd frontend && npx vitest run src/pages/open-source/components/os-insights-panel.test.tsx 2>&1 | tail -3`
Expected: FAIL（组件不存在）

- [ ] **Step 2: 实现组件**

新建 `os-insights-panel.tsx`：

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Card, Col, Collapse, Empty, Row, Spin, Statistic, Typography } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { api } from '../../../services/api'
import type { OSInsightsResponse } from '../../../services/api/openSource'
import type { OSSearchQuery } from '../../../types'
import { getTechElementFullLabel } from '@/constants/tech-elements'

const { Text } = Typography

interface Props {
  query: OSSearchQuery
}

function barOption(entries: [string, number][], color: string): EChartsOption {
  return {
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: entries.map(([k]) => k).reverse() },
    series: [
      { type: 'bar', data: entries.map(([, v]) => v).reverse(), itemStyle: { color } },
    ],
    tooltip: { trigger: 'axis' },
  }
}

const OsInsightsPanel: React.FC<Props> = ({ query }) => {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OSInsightsResponse | null>(null)

  const fetchInsights = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.openSource.getDeveloperInsights({
        q: query.q,
        tech_elements: query.tech_elements,
        languages: query.languages,
        location: query.location,
        company: query.company,
        repo_full_names: query.repo_full_names,
        is_committer: query.is_committer,
        is_student: query.is_student,
        has_contact: query.has_contact || undefined,
        china_related: query.china_related || undefined,
        top_org: query.top_org || undefined,
      })
      setData(res.data)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [query])

  // 展开时请求；筛选变化且面板处于展开态时自动刷新
  useEffect(() => {
    if (open) fetchInsights()
  }, [open, fetchInsights])

  const techEntries = useMemo(
    () =>
      Object.entries(data?.tech_element_distribution ?? {}).map(([code, n]) => [
        getTechElementFullLabel(code),
        n,
      ]) as [string, number][],
    [data]
  )
  const repoEntries = useMemo(
    () =>
      (data?.repo_distribution ?? []).map(
        (r) => [r.repo_full_name, r.developer_count] as [string, number]
      ),
    [data]
  )
  const companyEntries = useMemo(
    () => Object.entries(data?.company_distribution ?? {}),
    [data]
  )

  const contactRate =
    data && data.total > 0 ? ((data.contactable / data.total) * 100).toFixed(1) : '0.0'

  return (
    <Collapse
      style={{ marginTop: 16 }}
      onChange={(keys) => setOpen(keys.length > 0)}
      items={[
        {
          key: 'insights',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 6 }} />
              命中人才洞察（管理员）
            </span>
          ),
          children: (
            <Spin spinning={loading}>
              {!data && !loading && <Empty description="展开后加载洞察数据" />}
              {data && data.total === 0 && <Empty description="当前筛选无命中人才" />}
              {data && data.total > 0 && (
                <>
                  <Row gutter={16} style={{ marginBottom: 8 }}>
                    <Col span={6}>
                      <Card size="small">
                        <Statistic title="命中人数" value={data.total} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card size="small">
                        <Statistic
                          title="可触达（有联系方式）"
                          value={`${data.contactable} / ${data.total}`}
                          suffix={
                            <Text type="secondary" style={{ fontSize: 14 }}>
                              {contactRate}%
                            </Text>
                          }
                        />
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="技术要素分布">
                        <ReactECharts option={barOption(techEntries, '#6B46C1')} style={{ height: 260 }} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="来源仓库 Top 10">
                        <ReactECharts option={barOption(repoEntries, '#0891B2')} style={{ height: 260 }} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="当前公司 Top 10">
                        <ReactECharts option={barOption(companyEntries, '#16A34A')} style={{ height: 260 }} />
                      </Card>
                    </Col>
                  </Row>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    统计范围为当前筛选条件的全部命中人才；语义/混合搜索模式下按关键词等价条件统计。
                  </Text>
                </>
              )}
            </Spin>
          ),
        },
      ]}
    />
  )
}

export default OsInsightsPanel
```

- [ ] **Step 3: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/pages/open-source/components/os-insights-panel.test.tsx 2>&1 | tail -3`
Expected: `1 passed`

- [ ] **Step 4: 接入搜索页**

`open-source-search-page.tsx`：import 追加 `import OsInsightsPanel from './components/os-insights-panel'`，在 `<OsSearchResults ... />` 之后、`<ExportConfirmModal` 之前插入：

```tsx
      {isAdmin && <OsInsightsPanel query={query} />}
```

（`isAdmin` 已在第 18 行从 `useAuth()` 解构，无需新增。）

- [ ] **Step 5: 前端质量门禁**

Run: `cd frontend && npx prettier --write src/pages/open-source/components/os-insights-panel.tsx src/pages/open-source/components/os-insights-panel.test.tsx src/pages/open-source/open-source-search-page.tsx && npx tsc --noEmit && npx eslint src/pages/open-source/`
Expected: 无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/open-source/components/os-insights-panel.tsx frontend/src/pages/open-source/components/os-insights-panel.test.tsx frontend/src/pages/open-source/open-source-search-page.tsx
git commit -m "feat(open-source): 搜索页命中人才洞察面板（admin 专属，随筛选联动）"
```

---

### Task 7: 端到端验证 + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`（5.1.0 条目的 Added 段追加一行）

- [ ] **Step 1: 后端全量相关测试**

Run: `cd backend && uv run pytest tests/domains/open_source/ tests/modules/open_source/ tests/domains/shared/ -q 2>&1 | tail -2`
Expected: 全部 passed

- [ ] **Step 2: 前端全量测试 + 构建**

Run: `cd frontend && npx vitest run 2>&1 | tail -3 && npm run build 2>&1 | tail -2`
Expected: 全部 passed + `✓ built`

- [ ] **Step 3: CHANGELOG**

`CHANGELOG.md` 的 `## [5.1.0]` → `### Added` 段追加：

```markdown
- 开源人才搜索页新增「命中人才洞察」面板（管理员专属）：技术要素分布 / 来源仓库 Top10 / 可触达率 / 公司 Top10，随筛选条件联动
```

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md docs/superpowers/specs/2026-09-07-os-search-insights-design.md docs/superpowers/plans/2026-09-07-os-search-insights.md
git commit -m "docs: 开源搜索洞察模块设计文档与实现计划 + CHANGELOG"
```

---

## Self-Review 记录

- **Spec 覆盖**：4 个维度（Task 2）、权限 admin（Task 4）、折叠面板点开才算+联动刷新（Task 6）、filters 共用抽取（Task 2/3）、语义模式边界注明（Task 4/6）、测试（Task 2/4/6）、CHANGELOG（Task 7）——全覆盖。
- **类型一致性**：`OSInsightsResponse`（schema Task 1 / 前端 Task 5）字段一致；`get_developer_insights` 签名 service/repo/endpoint 一致（repo 收 filters dict，service/endpoint 收 kwargs）。
- **无占位符**：所有代码步骤含完整代码。
