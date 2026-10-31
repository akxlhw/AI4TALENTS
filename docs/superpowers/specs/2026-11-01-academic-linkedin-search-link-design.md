# 学术人才 LinkedIn 搜索链接设计

**日期**：2026-11-01
**状态**：已确认（后端注入方案）
**范围**：学术域详情 + shared 复用函数 + 前端详情页

## 背景

学术人才来自 OpenAlex，无 LinkedIn 数据源。参考实验室域模式：无真实 LinkedIn 链接时，用已有信息组合 Google 搜索链接作为发现辅助。

## 已确认决策

| 决策点 | 结论 |
|--------|------|
| 实现路径 | 后端注入（对齐 Lab 模式），响应字段显式命名 `linkedin_search_url` 表明是搜索辅助而非真实主页 |
| 组合策略 | `name_en`（缺英文名回退 `name`）+ `primary_school_name`，如 `"Wei Wang" MIT linkedin` |
| 覆盖范围 | 仅详情接口（`GET /talents/{id}`），列表不加 |

## 改动

1. **shared**：新建 `domains/shared/services/common/linkedin_search.py` — `build_linkedin_search_url(name: str, affiliation: str = "") -> str`（引号包裹姓名 + 机构 + "linkedin" 关键词，Google 搜索 URL，quote_plus 编码）
2. **lab 域**：`lab_talent_service.py` 的 `_linkedin_search_url` 改为薄代理调用 shared 函数（行为不变，回归测试验证）
3. **学术后端**：`schemas/overview.py` 的 `TalentDetail` 加 `linkedin_search_url: str | None`；`api/talent_queries.py` 的 `get_talent` 构造时注入
4. **前端**：`academic-talent-detail-page.tsx` 接口加字段，ORCID 链接旁渲染 LinkedIn 图标按钮（新窗口）；词条进 academic 命名空间

## 测试

- 组合函数单测：空姓名、带/无机构、URL 编码正确性
- 学术详情端点：字段存在、含 name_en 与校名、缺英文名回退中文名
- Lab 域既有测试回归通过（代理不改行为）

## 不做的事

- ❌ 学术域加 social_links 存储字段（无数据源，永远为空）
- ❌ 列表接口注入（点击详情才需要）
- ❌ 真实 LinkedIn 采集
