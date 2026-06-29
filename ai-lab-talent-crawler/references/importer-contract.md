# AI4Talent Importer 接口契约

本文件定义 crawler 输出与 AI4Talent importer 之间的接口契约。crawler 只管产出
符合此契约的 JSONL，importer（独立 spec 实现）只管消费。

## 输入

importer 读取：`output/<lab_slug>/_YYYY-MM-DD.jsonl`

每行是一个符合 `references/output-schema.md` 的 Person JSON 对象。

## 字段映射（JSONL → core_talent）

| JSONL 字段 | → core_talent 字段 | 说明 |
|-----------|-------------------|------|
| name | name | 标准化（去多余空白）后写入 |
| role_section | extra_data.role_section_raw | 原始分区标签 |
| role_section | role_type（经 map_site_role 映射） | Faculty→PROFESSOR / PhD Students→STUDENT / Postdocs→GRADUATE / ... |
| role_section | role_confidence | 映射置信度（站点分区声明，通常 1.0） |
| role_raw | current_title | 精确头衔（bio 详情页提取的） |
| homepage | extra_data.homepage | — |
| email | extra_data.email | — |
| research_areas | extra_data.research_areas | — |
| cohort_year | extra_data.cohort_year | — |
| cohort_source | extra_data.cohort_source | — |
| lab_name | lab_name | 子实验室名 |
| parent_lab | department_name | 顶层实验室名 |
| source_url | extra_data.source_url | 列表页 URL |
| source_detail_url | extra_data.source_detail_url | bio 详情页 URL |
| collected_at | extra_data.collected_at | 采集时间戳 |
| (name+lab_name+role_section 的 sha256) | source_record_id | 去重键 |

## 隔离

- source_type = `lab_web_site`（复用 AI4Talent v2 的隔离机制）
- importer 的 upsert 查询限定 `WHERE source_type='lab_web_site'`，绝不碰 v1（lab_web）或 openalex 记录

## 触发方式（importer 实现后）

```bash
# 导入单个 JSONL 文件
import-lab-talent --file output/stanford_ai_lab/_2026-06-29.jsonl

# 导入某 lab 最新一次采集
import-lab-talent --lab "Stanford AI Lab"
```

## 校验（importer 导入前）

importer 导入前校验 JSONL：
1. 每行是合法 JSON
2. 每行含 name 字段且非空
3. 每行含 source_url / collected_at / parent_lab
4. 不合法的行跳过并记日志（不中断导入）
