# JSONL 输出 Schema

采集的最终产物是 JSONL 文件（每行一个 JSON 对象代表一个人）。本文件定义字段。

## 文件位置

```
output/<lab_slug>/_YYYY-MM-DD.jsonl
```

`lab_slug` 是 labs.yaml 里 lab name 的 slug 化（小写+下划线，如 "Stanford AI Lab" → `stanford_ai_lab`）。

## 字段定义

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` | ✅ | string | 姓名 |
| `role_section` | ✅ | string | 页面分区原始标签（Faculty/PhD Students/Postdocs/Staff/Alumni）；无分区填 "Unknown" |
| `role_raw` | 可选 | string | bio 详情页的完整头衔原文（如 "Associate Professor of Computer Science"） |
| `homepage` | 可选 | string | 个人主页 URL |
| `email` | 可选 | string | 邮箱（从 bio 详情页提取） |
| `department` | 可选 | string | 院系/专业（如 "Computer Science"） |
| `research_areas` | 可选 | array[string] | 研究方向列表 |
| `cohort_year` | 可选 | integer | PhD 入学/加入年份（如 2020） |
| `cohort_source` | 可选 | string | 届别推断来源，格式 `<来源类型>:<原文片段>`（如 `bio_detail:"PhD since 2021"`） |
| `lab_name` | ✅ | string | 所属子实验室/研究组（如 "Stanford NLP Group"） |
| `parent_lab` | ✅ | string | 所属顶层实验室（对应 labs.yaml 的 name，如 "Stanford AI Lab"） |
| `source_url` | ✅ | string | 采集该人员的列表页 URL |
| `source_detail_url` | 可选 | string | bio 详情页 URL（若 agent 进了详情页） |
| `collected_at` | ✅ | string | ISO8601 采集时间戳（如 "2026-06-29T11:04:00Z"） |

## 关键规则

1. **提取不到的字段直接省略**——不写 `null`、不写空字符串、不猜测。
2. **name 必填**——缺 name 的条目必须丢弃。
3. **role_section + role_raw 双轨**：
   - `role_section` 来自页面分区（粗分类，用于 role_type 映射）
   - `role_raw` 来自 bio 详情页（精确头衔，用于展示）
   - 两者独立，列表页只有 role_section，进了 bio 才有 role_raw
4. **cohort_year 只从明确表述提取**（"PhD since 2020"/"joined in 2021"），禁止从论文年份推断。提取到 cohort_year 必须同时填 cohort_source。
5. **lab_name vs parent_lab**：一个 SAIL 下有多个子实验室（NLP/SNAP/Ermon），parent_lab 始终是顶层实验室名。

## 示例（一行 JSONL）

```json
{"name":"Aryaman Arora","role_section":"PhD Students","role_raw":"PhD Candidate","homepage":"https://aryaman.io/","department":"Computer Science","cohort_year":2020,"cohort_source":"bio_detail:\"PhD since 2020\"","lab_name":"Stanford NLP Group","parent_lab":"Stanford AI Lab","source_url":"https://nlp.stanford.edu/people/","source_detail_url":"https://aryaman.io/","collected_at":"2026-06-29T11:04:00Z"}
```

## 质量校验（写完 JSONL 后自检）

- 每行是合法 JSON（`python -c "import json; [json.loads(l) for l in open('file.jsonl')]"` 无报错）
- 每行含 name 字段且非空
- 总人数 > 0
