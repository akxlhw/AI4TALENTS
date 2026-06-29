# 设计文档：AI Lab 人才采集 Skill（ai-lab-talent-crawler）

- **状态**：草案，待用户复核
- **日期**：2026-06-29
- **类型**：独立 Hermes skill 项目（生产者侧）
- **前置**：v1/v2 已在 AI4Talent 内实现消费者侧（`lab_web` / `lab_web_site` 域）；本 spec 设计独立的生产者侧
- **关联调研**：`docs/superpowers/research/2026-06-29-sail-data-source-research.md`

---

## 1. 背景与定位

### 1.1 从 v2 到本 spec 的转变

v1（代码选择器抓 SAIL /faculty/）和 v2（域内 LLM 解析实验室站点）都在 AI4Talent **内部**实现采集。实践中发现两个问题：
- 爬虫运行时（浏览器自动化 + LLM agent 循环）很重，不该住在 FastAPI 请求路径里。
- 异构站点结构多变，单次 LLM 调用（v2）力不从心，需要 agent 在循环里自主导航/适应。

本 spec 把采集能力**外移为独立的 Hermes skill**，AI4Talent 只保留轻量 importer（消费 JSONL）。这是关注点分离：生产者（skill）独立迭代，消费者（平台）只管导入。

### 1.2 最终形态

一个 Hermes skill（`~/.agents/skills/ai-lab-talent-crawler/`），封装"agent 自主探索 AI 实验室官网 → 提取人才数据 → 输出标准 JSONL"的完整能力。agent 被触发后，读 SKILL.md 执行采集。

### 1.3 在整体愿景中的位置

用户最终要三个能力：(1) 采集 → (2) 导入 AI4Talent → (3) 人才洞察报告。本 spec 只覆盖 **(1) 采集**——它是数据链源头，其余两个依赖它的输出。(2)(3) 留后续 spec。

---

## 2. 技术栈

| 组件 | 角色 | 第一版默认实现 |
|------|------|--------------|
| **Hermes agent** | 编排器，运行半自主 agent 循环 | Hermes（用户环境） |
| **浏览器自动化服务** | agent 的"手"：navigate/snapshot/click/翻页 | Camofox (:9377) 或 kimi-webbridge (:10086)，agent 用当前可用的 |
| **LLM** | agent 的"大脑"：理解页面、提取人员、决定下一步 | agent 运行时的 LLM，**skill 不指定具体模型** |

**关键设计原则**：skill 定义"做什么"（用浏览器探索 + LLM 理解），**不写死具体模型/工具实现**。SKILL.md 用抽象角色（"浏览器服务"/"LLM"），前置依赖检查能力而非检查具体服务名。

---

## 3. 架构：配置驱动 + 全自主 agent 循环

### 3.1 运行模型

agent 收到任务后，**从实验室主域名出发，自主探索**找人才入口和跳转路径——不靠配置喂死 URL。配置退化为极简（name + domain + 可选 hints），所有结构性判断交给 agent。

### 3.2 配置 vs agent 分工

| 维度 | 配置提供（最小） | agent 自主判断 |
|------|-----------------|---------------|
| 入口 | 实验室主域名/名称 | 从主域名出发，找 People/Faculty/Team 页的真实 URL |
| 跳转路径 | 无 | agent 自己发现跳转链（主站→research-groups→子站→people） |
| 角色分区 | 无 | agent 遇到页面后自己识别分区 |
| 输出 | 输出目录约定 | — |
| 完成判据 | 角色覆盖期望（软约束） | agent 自己判断"采完了" |

### 3.3 数据流（agent 循环三阶段）

```
[Hermes agent 接收任务: "采集 Stanford AI Lab 的人才"]
        │
        ▼
[读 labs.yaml 匹配目标实验室]
        │
        ▼
┌─────────── agent 循环 (全自主探索 + 采集) ───────────┐
│  阶段一: 入口发现                                       │
│  1. 浏览器服务 navigate → 主域名                        │
│  2. 浏览器服务 snapshot → LLM 分析链接                   │
│  3. 找到人才相关入口 (Faculty/People/Team/Research...)  │
│  4. 记录跳转路径                                        │
│                                                        │
│  阶段二: 结构探索                                       │
│  5. navigate → 人才入口                                 │
│  6. snapshot → LLM 识别结构:                            │
│     - 角色分区 / 分页 / bio 详情链接 / 子实验室链接      │
│  7. 形成采集计划                                        │
│                                                        │
│  阶段三: 数据提取 (循环每个目标页)                       │
│  8. snapshot → LLM 按 extraction-prompt 提取人员 JSON   │
│  9. 有下一页 → 翻页 → 继续                              │
│ 10. 有 bio 详情 → 跟进提取 role_raw/cohort_year 等      │
│ 11. 累积所有人员                                        │
└────────────────────────────────────────────────────────┘
        │
        ▼
[输出 JSONL + 完成报告 + 探索路径记录]
```

---

## 4. 文件结构

```
ai-lab-talent-crawler/
├── SKILL.md                         ← skill 主体（能力描述/触发/流程/约束）
├── labs.yaml                        ← 目标实验室清单（结构化数据）
├── references/
│   ├── output-schema.md             ← JSONL 输出 schema 字段定义
│   ├── extraction-prompt.md         ← LLM 提取提示词（列表页 + bio，不含模型名）
│   ├── entry-discovery.md           ← 入口发现判定规则
│   └── importer-contract.md         ← 与 AI4Talent importer 的接口契约
└── scripts/
    └── crawl.py                     ← 辅助脚本（可选：封装浏览器调用/JSONL 写入/报告生成）
```

**SKILL.md 与 labs.yaml 各司其职**：SKILL.md 是给 agent 读的流程文档（markdown）；labs.yaml 是结构化清单（程序化读取/匹配/校验）。两者不混淆。

### 4.1 labs.yaml 格式

单文件清单，每个 lab 最少 name + domain，hints 全可选：

```yaml
labs:
  - name: "Stanford AI Lab"
    domain: "https://ai.stanford.edu"
    hints:
      known_sublabs: ["NLP Group", "SNAP", "Ermon Lab"]
      expected_roles: ["Faculty", "PhD Students", "Postdocs"]

  - name: "MIT CSAIL"
    domain: "https://www.csail.mit.edu"
    # 最简：只有 name + domain，agent 完全自主探索

  - name: "Google DeepMind"
    domain: "https://www.deepmind.com"

  - name: "北京智源"
    domain: "https://www.baai.ac.cn"
    hints:
      expected_roles: ["研究员", "博士生", "博士后"]
```

`hints` 唯一作用是降低 agent 探索成本（"这个站已知有 NLP Group"省得瞎找），但 agent 仍自主决策。

### 4.2 触发方式

```bash
# 单 lab（按名字/域名模糊匹配 labs.yaml）
crawl --lab "Stanford"

# 全部
crawl --all

# 自然语言触发："采集 Stanford AI Lab 的人才"
```

---

## 5. JSONL 输出 schema

每行一个 JSON 对象代表一个人。是 v2 `ParsedPerson` 的超集（agent 能进 bio 拿更多）。

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 姓名 |
| `role_section` | ✅ | 页面分区原始标签（Faculty/PhD Students/...）；无分区填 Unknown |
| `role_raw` | 可选 | bio 详情页的完整头衔原文（如 "Associate Professor of CS"） |
| `homepage` | 可选 | 个人主页 URL |
| `email` | 可选 | 邮箱（若 agent 能从详情页提取） |
| `department` | 可选 | 院系/专业 |
| `research_areas` | 可选 | 研究方向列表 |
| `cohort_year` | 可选 | PhD 入学/加入年份（整数）；提取不到则省略 |
| `cohort_source` | 可选 | 届别推断来源：`bio_detail:"PhD since 2021"` / `homepage:"2020-present"` |
| `lab_name` | ✅ | 所属子实验室/研究组（如 "Stanford NLP Group"） |
| `parent_lab` | ✅ | 所属顶层实验室（对应 labs.yaml 的 name） |
| `source_url` | ✅ | 采集该人员的列表页 URL |
| `source_detail_url` | 可选 | bio 详情页 URL |
| `collected_at` | ✅ | ISO8601 采集时间戳 |

**设计要点**：
- `role_section`（页面分区）+ `role_raw`（详情页头衔）双轨——前者做 role_type 映射，后者存精确身份。
- 提取不到的字段**直接省略**（不写 null/空串/猜测）。
- `cohort_year` 禁止从论文年份推断（不可靠），只从明确表述提取。

### 5.1 输出文件组织

```
output/
├── stanford_ai_lab/
│   ├── _2026-06-29.jsonl           ← 本次采集全量人员
│   ├── _report_2026-06-29.md       ← 完成报告（给人工核查）
│   └── _crawl_path_2026-06-29.md   ← agent 探索的入口/跳转链路
```

---

## 6. 完成报告与探索路径记录

### 6.1 完成报告（`_report_*.md`）

```markdown
# Stanford AI Lab 采集报告 — 2026-06-29

## 采集概况
- 目标实验室: Stanford AI Lab (https://ai.stanford.edu)
- 采集时间: 2026-06-29 11:04
- 总人数: 187
- 角色分布: Faculty 42 / PhD Students 98 / Postdocs 25 / Staff 12 / Alumni 10

## 子实验室覆盖
- 主站 /faculty/: 42 教授
- NLP Group: 87 人 / SNAP: 34 人 / Ermon Lab: 24 人

## 数据质量提示
- 博士生届别覆盖率: 62/98 (63%) [bio_detail 45 高可信 / homepage 17 中可信]
- 缺 email: 23 人 / role_section 无法判定: 5 人
- 未采子站: 2 (iliad.stanford.edu 超时)

## 异常与人工待确认
- 需核对: NLP "Visitors" 分区是否算在册人员
```

**部分成功原则**：采到 80% 就输出 80%，剩下的标到报告，不因一个子站失败丢全部。

### 6.2 探索路径记录（`_crawl_path_*.md`）

记录 agent 走过的 URL 链路 + 跳过决策，便于复现/审计。

---

## 7. SKILL.md 核心内容

### 7.1 结构

```markdown
---
name: ai-lab-talent-crawler
description: |
  采集全球顶尖 AI 实验室的人才数据。用浏览器服务驱动自主探索
  实验室官网，找到人员页面并提取结构化数据，输出标准 JSONL。
  触发："采集 X 实验室人才" / "爬取 AI Lab 人员" / "crawl lab talent"
---

# AI Lab 人才采集
## 何时触发 / 前置依赖检查 / 执行流程(3阶段) / 完成标准 / 约束
```

### 7.2 前置依赖（检查能力，不写死服务名）

```markdown
## 前置依赖（执行前检查）
1. 浏览器自动化服务可用:
   - 尝试 Camofox (http://localhost:9377/health) 或
   - 尝试 kimi-webbridge (http://127.0.0.1:10086)
   - 都不可用 → 提示用户启动其一
2. LLM 可用（当前 agent 运行时已具备，无需额外配置）
```

### 7.3 agent 执行约束（硬边界）

| 约束 | 说明 |
|------|------|
| 探索深度上限 5 跳 | 从主域名最多跟随 5 层链接 |
| 单次时间预算 30min | 防止无限消耗 |
| 跳过非人员页面 | twitter/github/会议/PDF/新闻 → LLM 判定跳过 |
| bio 详情采样 | 列表页人员 > 50 时，只抽 5 个 bio 补充（成本控制） |
| 不伪造字段 | 提取不到的字段省略，不填 null/猜测 |
| 每页提取校验 | LLM 输出的 JSON 必须含 name 字段，否则丢弃 |
| robots.txt 遵守 | 访问前检查，disallow 则跳过 |
| 不登录/不绕验证码 | — |

---

## 8. LLM 提取提示词（references/extraction-prompt.md）

**不含任何模型名**，纯提示词，任何 LLM 可用。

### 8.1 列表页提取

```
你是人才数据抽取助手。下面是一个实验室人员页面的可访问性树。
请提取所有真实人员，按页面中的角色分区分类。

输出严格的 JSON 数组：
[{"name":"...","role_section":"...","homepage":"...","department":"..."}, ...]

规则：
1. name 必填，必须是真实人名（跳过按钮文字）
2. role_section: 所在分区标签（Faculty/PhD Students/Postdocs）；无分区填 Unknown
3. homepage/department: 从卡片提取，没有则省略
4. 跳过校友，除非分区标注 Alumni
5. 不编造字段——提取不到就不输出

若页面有分页控件，JSON 末尾输出 {"_next_page": true}
```

### 8.2 bio 详情页提取

```
你是人才数据抽取助手。下面是一个研究者的个人页面。
请提取（能找到的字段，找不到的省略）：
{"name":"...","role_raw":"完整头衔原文","email":"...","research_areas":[...],
 "cohort_year":2020,"cohort_source":"bio_detail:原文片段"}

cohort_year 规则：
- 只从明确表述提取（"PhD since 2020"/"joined in 2021"）
- 禁止从论文年份推断
- 找不到则省略
```

---

## 9. 与 AI4Talent importer 的接口契约

importer 实现留后续 spec，**契约现在定义清楚**（crawler 输出 = importer 输入）。

importer 行为契约：
1. 读 `output/<lab>/_YYYY-MM-DD.jsonl`
2. 每行解析为 Person
3. 字段映射到 core_talent（复用 v2 的 role 映射）：

| JSONL 字段 | → core_talent | 说明 |
|-----------|---------------|------|
| name | name | 标准化后 |
| role_section | extra_data.role_section_raw + role_type(经 map_site_role) | 复用 v2 |
| role_raw | current_title | 精确头衔 |
| homepage/email/research_areas | extra_data.* | — |
| lab_name | lab_name | 子实验室 |
| parent_lab | department_name | 顶层实验室 |
| cohort_year/cohort_source | extra_data.* | — |
| source_url/source_detail_url/collected_at | extra_data.* | 追溯 |
| (name+lab_name+role_section hash) | source_record_id | 去重键 |

4. `source_type = 'lab_web_site'`（复用 v2 隔离）
5. CLI：`import-lab-talent --file output/stanford_ai_lab/_2026-06-29.jsonl`

---

## 10. 范围

### 10.1 本 spec 覆盖

- SKILL.md（能力描述/触发/流程/约束）
- labs.yaml 格式 + Stanford SAIL 参考
- references/（output-schema / extraction-prompt / entry-discovery / importer-contract）
- scripts/crawl.py（辅助脚本，封装浏览器调用/JSONL 写入/报告）
- 错误处理 + 完成报告 + 探索路径

### 10.2 不在本 spec 范围

- AI4Talent importer 实现（契约已定义，实现留后续 spec）
- 人才洞察报告（第三能力，独立 spec）
- 50+ 实验室全量配置（架构预留，第一版聚焦格式 + 参考 lab）
- 增量更新/调度（一次性快照为主）

---

## 11. 成功标准

1. ✅ skill 可被 Hermes 触发（"采集 Stanford AI Lab 人才"）
2. ✅ agent 从 `ai.stanford.edu` 自主探索到 /faculty/ 和子实验室 people 页
3. ✅ 输出符合 schema 的 JSONL（含 name/role_section/lab_name/source_*）
4. ✅ 能区分教授与 PhD 学生（role_section 正确）
5. ✅ cohort_year 在可达时正确提取（并标 source）
6. ✅ 完成报告 + 探索路径记录生成
7. ✅ 部分成功：单个子站失败不丢全部数据
8. ✅ JSONL 能被 importer 契约消费（字段对齐）

---

## 12. 风险

| 风险 | 缓解 |
|------|------|
| agent 探索耗时/token 超预算 | 30min + 5 跳硬上限；超限停止，输出已采数据 |
| 异构站点 agent 无法理解 | 记录到报告"未采"，人工核查；hints 辅助 |
| 浏览器服务不稳定 | 前置检查 + 超时跳过该页 |
| LLM 提取幻觉（编造字段） | "不伪造字段"约束 + name 必填校验 + 报告质量统计 |
| cohort_year 普遍不可得 | 接受为可选字段 + 报告覆盖率统计；不硬推断 |
| labs.yaml 维护成本 | 单文件 + 极简字段（name+domain）；hints 可选 |
