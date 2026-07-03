# AI Lab 人才采集 Skill 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一个独立的 Hermes skill（`ai-lab-talent-crawler`），封装"agent 自主探索 AI 实验室官网 → 提取人才数据 → 输出标准 JSONL"的完整能力。

**Architecture:** skill 由 SKILL.md（流程定义）+ labs.yaml（结构化实验室清单）+ references（输出 schema/提取提示词/入口发现规则/importer 契约）+ scripts/crawl.py（辅助执行脚本）组成。agent 从实验室主域名全自主探索入口，用浏览器服务（Camofox/kimi-webbridge，抽象不写死）+ LLM（不指定模型）采集人员，全量跟进 bio 详情，输出 JSONL 供 AI4Talent importer 消费。

**Tech Stack:** Hermes agent、Camofox（:9377）/ kimi-webbridge（:10086）浏览器服务、LLM（agent 运行时）、Python（crawl.py 辅助脚本）、JSONL/YAML。

**Spec:** `docs/superpowers/specs/2026-06-29-ai-lab-talent-crawler-skill-design.md`

**工作目录约定：** 先在 `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\` 暂存开发，完成后（Task 10）部署到 `~/.agents/skills/ai-lab-talent-crawler/`。

**关键事实（写计划时已核实）：**
- Camofox API：`POST /tabs`（创建标签页）→ `POST /tabs/:tabId/navigate`（导航）→ `GET /tabs/:tabId/snapshot`（可访问性树，含 `e1`/`e2` 元素引用）→ `POST /tabs/:tabId/click`（点击引用）→ `POST /tabs/:tabId/scroll`（滚动）→ `GET /tabs/:tabId/links`（提取链接）。
- Camofox 无显式 `/health` 端点——用 `GET /tabs?userId=probe` 探活（返回标签列表即存活）。
- kimi-webbridge 核心 tools：navigate/snapshot/click/fill/evaluate/screenshot（与 Camofox 能力对齐，都可作浏览器服务）。
- skill 的主要交付物是**文档**（SKILL.md + references + yaml），crawl.py 是辅助脚本（封装调用、写 JSONL/报告），不是核心逻辑载体。

---

## File Structure

工作目录：`D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\`

| 文件 | 职责 | 类型 |
|------|------|------|
| `SKILL.md` | skill 主体：能力描述/触发/前置检查/三阶段流程/约束 | 文档 |
| `labs.yaml` | 目标实验室清单（name+domain+hints） | 配置 |
| `references/output-schema.md` | JSONL 输出字段定义 | 文档 |
| `references/extraction-prompt.md` | LLM 提取提示词（列表页+bio，无模型名） | 文档 |
| `references/entry-discovery.md` | 入口发现判定规则 | 文档 |
| `references/importer-contract.md` | 与 AI4Talent importer 的接口契约 | 文档 |
| `scripts/crawl.py` | 辅助脚本：浏览器探活/JSONL 写入/报告生成/labs.yaml 读取 | 代码 |
| `scripts/test_crawl.py` | crawl.py 的单元测试 | 测试 |

---

## Task 1: skill 骨架 + SKILL.md 主体

**Files:**
- Create: `ai-lab-talent-crawler/SKILL.md`

- [ ] **Step 1: 创建 skill 骨架目录 + SKILL.md 主体**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\SKILL.md`:

```markdown
---
name: ai-lab-talent-crawler
description: |
  采集全球顶尖 AI 实验室的人才数据。用浏览器服务驱动自主探索实验室官网，
  找到人员页面并提取结构化数据，输出标准 JSONL，供 AI4Talent 导入。
  触发场景："采集 X 实验室人才" / "爬取 AI Lab 人员" / "crawl lab talent" /
  "更新某实验室的人才数据" / "批量采集多个实验室"。
---

# AI Lab 人才采集

本 skill 让 agent 自主探索 AI 实验室官网，提取教授/博士生/博后等人才数据，
输出标准 JSONL 文件。agent 从实验室主域名出发，自己发现人才入口和跳转路径
（不依赖硬编码 URL），适应各实验室不同的页面结构。

## 何时触发

- 用户要求采集/爬取某 AI 实验室的人员/人才/教授/学生
- 用户要求更新某实验室的人才数据
- 用户要求批量采集多个实验室

## 前置依赖（执行前检查）

执行前必须确认两项依赖可用：

1. **浏览器自动化服务**（二选一，用当前可用的）：
   - Camofox：`GET http://localhost:9377/tabs?userId=probe` 返回标签列表即存活
   - kimi-webbridge：`GET http://127.0.0.1:10086` 可达即存活
   - 都不可用 → 停止，提示用户："请先启动浏览器服务（Camofox: `cd camofox-browser && npm start`，或 kimi-webbridge）"

2. **LLM**：当前 agent 运行时已具备 LLM 能力（用于页面理解和人员提取），无需额外配置。

## 执行流程

采集分三个阶段，全部由 agent 自主完成：

### 阶段一：入口发现
1. 从 `labs.yaml` 匹配目标实验室，获取其主域名
2. 浏览器 navigate → 主域名
3. 浏览器 snapshot → LLM 分析页面导航和链接
4. 目标：找到 People/Faculty/Team/Members/Research Groups 类页面入口
5. 详细的链接判定规则见 `references/entry-discovery.md`
6. 记录发现的入口 URL 和跳转路径（写入 `_crawl_path_*.md`）

### 阶段二：结构探索
1. 浏览器 navigate → 发现的人才入口
2. 浏览器 snapshot → LLM 识别页面结构：
   - 有角色分区吗？（Faculty/PhD Students/Postdocs/Staff/Alumni）
   - 有分页吗？
   - 每个人有 bio 详情页链接吗？
   - 有子实验室链接吗？（如 research-groups）
3. 基于结构形成采集计划（哪些页要采、跳转链路、预计人数）

### 阶段三：数据提取（循环每个目标页）
1. 浏览器 snapshot → LLM 按 `references/extraction-prompt.md` 提取人员 JSON
2. 每个人记录：name / role_section / homepage / department（列表页字段）
3. **bio 详情全量跟进**：每个人的 bio 链接都跟进，补充 role_raw / cohort_year / email / research_areas（详见 extraction-prompt.md 的 bio 提取部分）
4. 有分页 → 浏览器翻页 → 继续
5. 有子实验室 → 跟进其 people 页 → 继续
6. 累积所有人员

### 输出
1. 写 JSONL：`output/<lab_slug>/_YYYY-MM-DD.jsonl`（schema 见 `references/output-schema.md`）
2. 写完成报告：`output/<lab_slug>/_report_YYYY-MM-DD.md`（人数/角色分布/质量提示/异常）
3. 写探索路径：`output/<lab_slug>/_crawl_path_YYYY-MM-DD.md`（入口/跳转链/跳过决策）

## 完成标准

一次采集视为成功，需满足：
- 总人数 > 0
- 输出 JSONL 文件已生成且每行可被 JSON 解析
- 每行必含 name 字段
- 完成报告已生成

未满足 → 在报告中标注 "needs review" 并列出原因。**部分成功优于完全失败**：单个子站失败时，已采的数据正常输出，失败的子站记入报告。

## 约束（硬边界，必须遵守）

| 约束 | 说明 |
|------|------|
| 探索深度上限 5 跳 | 从主域名最多跟随 5 层链接，防止无限爬 |
| 单次时间预算 30min | 超限时停止，已采集的数据正常输出 |
| 跳过非人员页面 | twitter/github/会议/PDF/新闻/博客 → LLM 判定后跳过 |
| bio 详情全量跟进 | 列表页每个人都跟进其 bio 详情页；不采样、不限制；靠 30min 预算自然约束 |
| 不伪造字段 | 提取不到的字段直接省略（不写 null/空串/猜测值） |
| 每页提取校验 | LLM 输出的每人 JSON 必须含 name 字段，否则丢弃该条 |
| robots.txt 遵守 | 访问前检查，disallow 则跳过该路径 |
| 不登录/不绕验证码 | 遇到登录墙或验证码 → 跳过，记入报告 |

## 参考文件

执行时按需查阅：
- `references/output-schema.md` — JSONL 输出字段定义
- `references/extraction-prompt.md` — LLM 提取提示词（列表页 + bio 详情页）
- `references/entry-discovery.md` — 入口发现判定规则
- `references/importer-contract.md` — 与 AI4Talent importer 的接口契约
- `labs.yaml` — 目标实验室清单
- `scripts/crawl.py` — 辅助脚本（探活/写 JSONL/写报告/读 labs.yaml）
```

- [ ] **Step 2: 验证 SKILL.md 可解析（frontmatter 合法）**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web && head -8 ai-lab-talent-crawler/SKILL.md
```
Expected: 显示 frontmatter（`---` 开头，含 name/description），结构完整。

- [ ] **Step 3: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/SKILL.md
git commit -m "feat(crawler-skill): add SKILL.md main body — triggers, flow, constraints"
```

---

## Task 2: labs.yaml 实验室清单

**Files:**
- Create: `ai-lab-talent-crawler/labs.yaml`

- [ ] **Step 1: 创建 labs.yaml（含 Stanford 参考 + 几个候选）**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\labs.yaml`:

```yaml
# AI 实验室人才采集清单
# 新增实验室只需加一条：最少 name + domain；hints 全可选（降低 agent 探索成本）
# agent 从 domain 出发自主探索入口，不依赖硬编码 URL

labs:
  # === 已验证可采集（Hermes 已跑通） ===
  - name: "Stanford AI Lab"
    domain: "https://ai.stanford.edu"
    hints:
      known_sublabs: ["NLP Group", "SNAP", "Ermon Lab"]
      expected_roles: ["Faculty", "PhD Students", "Postdocs", "Staff", "Alumni"]

  # === 候选（待 agent 首次探索验证） ===
  - name: "MIT CSAIL"
    domain: "https://www.csail.mit.edu"

  - name: "Google DeepMind"
    domain: "https://www.deepmind.com"

  - name: "FAIR"
    domain: "https://ai.meta.com"

  - name: "OpenAI"
    domain: "https://openai.com"

  - name: "Anthropic"
    domain: "https://www.anthropic.com"

  - name: "Microsoft Research"
    domain: "https://www.microsoft.com/en-us/research"

  - name: "Berkeley AI Research"
    domain: "https://bair.berkeley.edu"

  - name: "北京智源"
    domain: "https://www.baai.ac.cn"
    hints:
      expected_roles: ["研究员", "博士生", "博士后"]

  - name: "清华大学人工智能研究院"
    domain: "https://www.ai.tsinghua.edu.cn"
```

- [ ] **Step 2: 验证 YAML 可解析**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web && uv run python -c "
import yaml
with open('ai-lab-talent-crawler/labs.yaml') as f:
    data = yaml.safe_load(f)
labs = data['labs']
print(f'labs count: {len(labs)}')
for lab in labs:
    print(f'  {lab[\"name\"]:30} {lab[\"domain\"]}')
"
```
Expected: 打印 10 个实验室的 name + domain，无 YAML 解析错误。

- [ ] **Step 3: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/labs.yaml
git commit -m "feat(crawler-skill): add labs.yaml with 10 target labs (Stanford as reference)"
```

---

## Task 3: references/output-schema.md（JSONL 输出契约）

**Files:**
- Create: `ai-lab-talent-crawler/references/output-schema.md`

- [ ] **Step 1: 创建 output-schema.md**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\references\output-schema.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/references/output-schema.md
git commit -m "feat(crawler-skill): add JSONL output schema reference"
```

---

## Task 4: references/extraction-prompt.md（LLM 提取提示词）

**Files:**
- Create: `ai-lab-talent-crawler/references/extraction-prompt.md`

- [ ] **Step 1: 创建 extraction-prompt.md（列表页 + bio，无模型名）**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\references\extraction-prompt.md`:

```markdown
# LLM 提取提示词

本文件定义 agent 调用 LLM 提取人员数据时使用的提示词。**不绑定具体模型**——任何
能理解文本并输出 JSON 的 LLM 都适用。agent 在调用时把 snapshot 内容拼入 user 消息。

---

## 列表页提取（从 People 页面 snapshot 提取人员）

### 系统提示词

```
你是人才数据抽取助手。下面是一个大学实验室人员页面的可访问性树（accessibility tree）。
请提取页面中所有真实人员，并按他们在页面中所属的角色分区分类。

输出严格的 JSON 数组，每个元素是一个人员对象。不要输出任何额外文字或 markdown：

[
  {"name": "...", "role_section": "...", "homepage": "...", "department": "..."},
  ...
]

规则：
1. name 必填——必须是真实人名。跳过 "Read More"、"Back"、"Home" 等按钮或导航文字。
2. role_section：该人员所在页面分区的标签（如 "Faculty"、"PhD Students"、"Postdocs"、
   "Staff"、"Alumni"）。如果页面没有分区结构，填 "Unknown"。
3. homepage：从人员卡片中提取的个人主页链接（如有）。没有则省略此字段。
4. department：从卡片提取的院系/专业（如有，如 "Computer Science"）。没有则省略。
5. 跳过已毕业/校友，除非分区明确标注为 "Alumni"（此时 role_section 填 "Alumni"）。
6. 不要编造任何字段——提取不到的字段直接省略，不要填 null 或空字符串。

如果页面包含"下一页"、"Next"、"Load more" 或分页控件，在 JSON 数组末尾追加一个
特殊对象（不计入人员数）：
  {"_next_page": true}
以便 agent 决定是否翻页继续提取。
```

### 用户消息

```
=== 页面可访问性树开始 ===
{snapshot_content}
=== 页面可访问性树结束 ===
```

---

## bio 详情页提取（跟进个人页面补充详细字段）

当 agent 从列表页发现某人有 bio/个人主页链接，跟进该页面时使用此提示词。

### 系统提示词

```
你是人才数据抽取助手。下面是一个研究者的个人 bio 页面（可访问性树）。
请从中提取以下字段——只能提取明确出现的信息，找不到的字段必须省略（不猜测、不推断）：

{
  "name": "姓名（必填）",
  "role_raw": "完整头衔原文，如 'Associate Professor of Computer Science'",
  "email": "邮箱地址（如有）",
  "research_areas": ["研究方向1", "研究方向2"],
  "cohort_year": 2020,
  "cohort_source": "来源类型:原文片段"
}

字段规则：
1. name：必填。页面上该人的姓名。
2. role_raw：页面上写的完整职位/头衔原文。这是精确身份（区别于列表页的粗分区）。
3. email：邮箱地址。注意可能被混淆（如 "john [at] stanford [dot] edu"），还原为标准格式。
4. research_areas：研究方向关键词列表。只从明确列出的提取。
5. cohort_year（PhD 届别）——只从明确表述提取，例如：
   - "PhD since 2020" / "PhD candidate since 2021" → cohort_year=2020/2021
   - "joined the lab in 2022" → cohort_year=2022
   - "2020–present" 在教育经历里 → cohort_year=2020
   禁止从论文发表年份推断入学年份（不可靠）。
   找不到明确表述 → 省略 cohort_year 和 cohort_source 两个字段。
6. cohort_source：提取 cohort_year 时必须同时填，格式为 "来源类型:原文片段"。
   来源类型：bio_detail（bio 页明确写的）/ homepage（个人主页的教育经历段）。

输出单个 JSON 对象（不是数组）。不要输出额外文字。
```

### 用户消息

```
=== bio 页面可访问性树开始 ===
{snapshot_content}
=== bio 页面可访问性树结束 ===
```

---

## 提取后校验

agent 拿到 LLM 输出后，对每个人员对象执行：
1. 解析 JSON——失败则丢弃整批，记入报告"该页提取失败"
2. 每个对象必须有非空 name——缺 name 的丢弃
3. homepage 若存在，必须是合法 URL（http/https 开头）——非法的省略该字段（不丢弃整个人）
4. cohort_year 若存在，必须是 4 位整数（1990-2030 范围）——非法的省略
```

- [ ] **Step 2: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/references/extraction-prompt.md
git commit -m "feat(crawler-skill): add LLM extraction prompts (list page + bio, model-agnostic)"
```

---

## Task 5: references/entry-discovery.md + importer-contract.md

**Files:**
- Create: `ai-lab-talent-crawler/references/entry-discovery.md`
- Create: `ai-lab-talent-crawler/references/importer-contract.md`

- [ ] **Step 1: 创建 entry-discovery.md（入口发现判定规则）**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\references\entry-discovery.md`:

```markdown
# 入口发现判定规则

agent 从实验室主域名出发，自主寻找人才相关页面入口。本文件定义判定规则，
帮助 agent 决定哪些链接值得跟进、哪些应跳过。

## 值得跟进的链接（人才入口信号）

链接文本或 URL 含以下关键词时，优先跟进：
- People / Faculty / Team / Members / Staff / Group
- Research Groups / Labs / 实验室 / 课题组
- PhD Students / Students / 研究员 / 博士生 / 博士后

## 应跳过的链接

- 社交媒体：twitter.com / x.com / linkedin.com / youtube.com / github.com
- 新闻/博客：/news / /blog / /press
- 文件：.pdf / .jpg / .png / .zip
- 课程/招生：/courses / /admissions / /apply
- 导航骨架：Login / Search / Accessibility / Copyright

## 探索深度限制

从主域名起算，最多跟随 5 跳：
- 第 1 跳：主域名首页
- 第 2 跳：People/Faculty 或 Research Groups 页
- 第 3 跳：具体子实验室站点（如 nlp.stanford.edu）
- 第 4 跳：子实验室的 People 页
- 第 5 跳：个人的 bio 详情页

超过 5 跳 → 停止跟进，记录到报告。

## 子实验室发现

许多 AI 实验室（如 SAIL）由多个独立子实验室组成，各有自己的站点和 People 页。
当 agent 在主站发现 "Research Groups" 或类似页面时：
1. 提取所有子实验室链接
2. 逐个跟进，找其 People 页
3. 每个子实验室的人员标注 `lab_name` = 子实验室名，`parent_lab` = 顶层实验室名

## 入口发现失败的处理

若 agent 在主域名 + 2 跳内找不到任何 People/Faculty 类页面：
- 记录到报告："未找到人才入口，主站结构可能需要人工指引"
- 标注本次采集为 "needs review"
- 输出已发现的链接清单（供人工判断哪个是入口）
```

- [ ] **Step 2: 创建 importer-contract.md（与 AI4Talent importer 的契约）**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\references\importer-contract.md`:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/references/entry-discovery.md ai-lab-talent-crawler/references/importer-contract.md
git commit -m "feat(crawler-skill): add entry-discovery rules + AI4Talent importer contract"
```

---

## Task 6: scripts/crawl.py 辅助脚本（TDD）

**Files:**
- Create: `ai-lab-talent-crawler/scripts/crawl.py`
- Create: `ai-lab-talent-crawler/scripts/test_crawl.py`

- [ ] **Step 1: 写失败测试（JSONL 写入 + labs.yaml 读取 + 报告生成）**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\scripts\test_crawl.py`:

```python
"""Tests for crawl.py helper functions (JSONL writing, labs.yaml reading, report gen)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from crawl import (
    generate_report,
    load_labs,
    slugify,
    write_jsonl,
)

pytestmark = pytest.mark.unit


class TestSlugify:
    def test_basic(self):
        assert slugify("Stanford AI Lab") == "stanford_ai_lab"

    def test_chinese(self):
        assert slugify("北京智源") == "北京智源"  # non-ascii preserved

    def test_special_chars(self):
        assert slugify("MIT  CSAIL!!") == "mit_csail"


class TestLoadLabs:
    def test_loads_labs_list(self, tmp_path):
        yaml_content = """
labs:
  - name: "Test Lab"
    domain: "https://test.example"
  - name: "Lab Two"
    domain: "https://two.example"
"""
        labs_file = tmp_path / "labs.yaml"
        labs_file.write_text(yaml_content, encoding="utf-8")
        labs = load_labs(str(labs_file))
        assert len(labs) == 2
        assert labs[0]["name"] == "Test Lab"
        assert labs[1]["domain"] == "https://two.example"

    def test_match_by_name(self, tmp_path):
        yaml_content = """
labs:
  - name: "Stanford AI Lab"
    domain: "https://ai.stanford.edu"
  - name: "MIT CSAIL"
    domain: "https://www.csail.mit.edu"
"""
        labs_file = tmp_path / "labs.yaml"
        labs_file.write_text(yaml_content, encoding="utf-8")
        match = load_labs(str(labs_file), match="Stanford")
        assert len(match) == 1
        assert match[0]["name"] == "Stanford AI Lab"


class TestWriteJsonl:
    def test_writes_valid_jsonl(self, tmp_path):
        persons = [
            {"name": "Alice", "role_section": "Faculty"},
            {"name": "Bob", "role_section": "PhD Students"},
        ]
        path = write_jsonl(persons, str(tmp_path), "test_lab", "2026-06-29")
        content = Path(path).read_text(encoding="utf-8")
        lines = [json.loads(l) for l in content.strip().split("\n")]
        assert len(lines) == 2
        assert lines[0]["name"] == "Alice"
        assert lines[1]["role_section"] == "PhD Students"

    def test_skips_entries_without_name(self, tmp_path):
        persons = [
            {"name": "Alice", "role_section": "Faculty"},
            {"role_section": "Unknown"},  # no name -> skipped
        ]
        path = write_jsonl(persons, str(tmp_path), "test_lab", "2026-06-29")
        content = Path(path).read_text(encoding="utf-8")
        lines = [json.loads(l) for l in content.strip().split("\n")]
        assert len(lines) == 1  # the nameless one dropped


class TestGenerateReport:
    def test_report_contains_counts_and_roles(self, tmp_path):
        persons = [
            {"name": "A", "role_section": "Faculty"},
            {"name": "B", "role_section": "PhD Students"},
            {"name": "C", "role_section": "PhD Students"},
        ]
        report = generate_report(
            persons,
            str(tmp_path),
            "test_lab",
            "https://test.example",
            "2026-06-29",
        )
        assert "3" in report  # total
        assert "Faculty" in report
        assert "PhD Students" in report
```

- [ ] **Step 2: 运行确认失败**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web/ai-lab-talent-crawler/scripts && uv run --project D:/AI/AI4TALENT-lab-web/backend pytest test_crawl.py -v 2>&1 | tail -5
```
Expected: FAIL `ModuleNotFoundError: No module named 'crawl'`

- [ ] **Step 3: 实现 crawl.py**

Create `D:\AI\AI4TALENT-lab-web\ai-lab-talent-crawler\scripts\crawl.py`:

```python
"""Helper functions for ai-lab-talent-crawler skill.

These are utilities the agent (or a human) can call to:
- load_labs: read labs.yaml and optionally filter by name/domain
- write_jsonl: write persons to a validated JSONL file
- generate_report: write a human-readable collection report
- check_browser_service: probe Camofox/kimi-webbridge availability

The agent's core logic (explore + extract) is driven by the LLM reading
SKILL.md + references; this script handles the mechanical I/O parts.
"""
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def slugify(name: str) -> str:
    """Convert a lab name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name.strip())
    slug = slug.strip("_")
    return slug.lower() if slug.isascii() else slug


def load_labs(labs_file: str, match: str | None = None) -> list[dict[str, Any]]:
    """Load labs from labs.yaml. If match is given, filter by name/domain substring."""
    with open(labs_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    labs = data.get("labs", [])
    if match:
        m_lower = match.lower()
        labs = [
            lab
            for lab in labs
            if m_lower in lab.get("name", "").lower()
            or m_lower in lab.get("domain", "").lower()
        ]
    return labs


def write_jsonl(
    persons: list[dict[str, Any]],
    output_dir: str,
    lab_slug: str,
    date_str: str,
) -> str:
    """Write persons to output/<lab_slug>/_<date>.jsonl.

    Validates each entry: must have non-empty name. Drops entries without name.
    """
    lab_dir = Path(output_dir) / lab_slug
    lab_dir.mkdir(parents=True, exist_ok=True)
    path = lab_dir / f"_{date_str}.jsonl"
    valid = 0
    with open(path, "w", encoding="utf-8") as f:
        for person in persons:
            name = person.get("name")
            if not name or not str(name).strip():
                continue  # drop nameless entries
            f.write(json.dumps(person, ensure_ascii=False))
            f.write("\n")
            valid += 1
    return str(path)


def generate_report(
    persons: list[dict[str, Any]],
    output_dir: str,
    lab_name: str,
    lab_domain: str,
    date_str: str,
    notes: str = "",
) -> str:
    """Generate a human-readable collection report markdown."""
    total = len(persons)
    role_counts = Counter(p.get("role_section", "Unknown") for p in persons)
    cohort_known = sum(1 for p in persons if "cohort_year" in p)
    email_known = sum(1 for p in persons if "email" in p)

    lines = [
        f"# {lab_name} 采集报告 — {date_str}",
        "",
        "## 采集概况",
        f"- 目标实验室: {lab_name} ({lab_domain})",
        f"- 采集时间: {date_str}",
        f"- 总人数: {total}",
        "## 角色分布",
    ]
    for role, count in role_counts.most_common():
        lines.append(f"  - {role}: {count}")
    lines.extend(
        [
            "",
            "## 数据质量提示",
            f"- 博士生届别覆盖率: {cohort_known}/{total} ({(100 * cohort_known // total) if total else 0}%)"
            if total
            else "- 博士生届别覆盖率: 0/0",
            f"- 有邮箱: {email_known}/{total}",
        ]
    )
    if notes:
        lines.extend(["", "## 异常与人工待确认", notes])
    report = "\n".join(lines)

    lab_slug = slugify(lab_name)
    lab_dir = Path(output_dir) / lab_slug
    lab_dir.mkdir(parents=True, exist_ok=True)
    report_path = lab_dir / f"_report_{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    return report


def check_browser_service() -> str | None:
    """Probe browser automation services. Returns which one is available, or None.

    Tries Camofox first (:9377), then kimi-webbridge (:10086).
    """
    for name, url in [
        ("camofox", "http://localhost:9377/tabs?userId=probe"),
        ("kimi-webbridge", "http://127.0.0.1:10086"),
    ]:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status < 500:
                    return name
        except Exception:
            continue
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web/ai-lab-talent-crawler/scripts && uv run --project D:/AI/AI4TALENT-lab-web/backend pytest test_crawl.py -v 2>&1 | tail -5
```
Expected: PASS (all tests: slugify x3, load_labs x2, write_jsonl x2, generate_report x1)

- [ ] **Step 5: Commit**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/scripts/
git commit -m "feat(crawler-skill): add crawl.py helpers (labs loader, JSONL writer, report gen, browser probe) with tests"
```

---

## Task 7: 手动验收 — 用真实浏览器服务跑 Stanford 采集

**Files:** 无新文件（验收现有产物）

- [ ] **Step 1: 确认浏览器服务可用**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web && uv run python -c "
import sys; sys.path.insert(0, 'ai-lab-talent-crawler/scripts')
from crawl import check_browser_service
avail = check_browser_service()
print('browser service:', avail or 'NONE AVAILABLE')
"
```
Expected: `browser service: camofox` 或 `kimi-webbridge`（取决于哪个在跑）。若 NONE → 启动 Camofox 后重试。

- [ ] **Step 2: 手动触发 agent 采集 Stanford AI Lab**

这是手动验收步骤（agent 自主探索，无法脚本化）：
1. 启动 Hermes agent
2. 触发 skill：告诉 agent "采集 Stanford AI Lab 的人才数据"
3. 观察 agent 执行三阶段（入口发现 → 结构探索 → 数据提取）
4. 确认 agent 从 `ai.stanford.edu` 自主找到 `/faculty/` 和子实验室 people 页

- [ ] **Step 3: 核对输出 JSONL**

Run:
```bash
cd D:/AI/AI4TALENT-lab-web && ls ai-lab-talent-crawler/output/stanford_ai_lab/ 2>&1
# 校验 JSONL 合法
uv run python -c "
import json
path = 'ai-lab-talent-crawler/output/stanford_ai_lab/_2026-06-29.jsonl'
lines = open(path, encoding='utf-8').read().strip().split(chr(10))
persons = [json.loads(l) for l in lines]
print(f'total persons: {len(persons)}')
roles = {}
for p in persons: roles[p.get('role_section','?')] = roles.get(p.get('role_section','?'),0)+1
print('roles:', roles)
students = [p for p in persons if 'PhD' in p.get('role_section','') or 'Student' in p.get('role_section','')]
print(f'PhD Students: {len(students)}')
# check required fields
for p in persons[:3]:
    assert p.get('name'), 'missing name'
    assert p.get('source_url'), 'missing source_url'
print('validation passed')
"
```
Expected: total > 0, 含 PhD Students 角色，验证通过。

- [ ] **Step 4: 核对完成报告 + 探索路径**

Run:
```bash
cat ai-lab-talent-crawler/output/stanford_ai_lab/_report_2026-06-29.md
cat ai-lab-talent-crawler/output/stanford_ai_lab/_crawl_path_2026-06-29.md
```
Expected: 报告含人数/角色分布/质量提示；探索路径含入口和跳转链。

- [ ] **Step 5: Commit 验收产出（JSONL + 报告）**

```bash
cd D:/AI/AI4TALENT-lab-web
git add ai-lab-talent-crawler/output/
git commit -m "test(crawler-skill): Stanford AI Lab acceptance — real agent crawl output"
```

---

## Task 8: 部署 skill 到 ~/.agents/skills/

**Files:**
- Copy: `ai-lab-talent-crawler/` → `~/.agents/skills/ai-lab-talent-crawler/`

- [ ] **Step 1: 复制 skill 到正式位置**

Run:
```bash
cp -r D:/AI/AI4TALENT-lab-web/ai-lab-talent-crawler ~/.agents/skills/ai-lab-talent-crawler
ls ~/.agents/skills/ai-lab-talent-crawler/
```
Expected: 显示 SKILL.md / labs.yaml / references/ / scripts/

- [ ] **Step 2: 验证 skill 可被发现**

Run:
```bash
ls ~/.agents/skills/ | grep ai-lab
```
Expected: `ai-lab-talent-crawler`

- [ ] **Step 3: 在新 agent 会话中测试触发**

启动新的 Hermes/ZCode agent 会话，输入："采集 Stanford AI Lab 的人才"。
Expected: agent 识别到 ai-lab-talent-crawler skill 并开始执行采集流程。

- [ ] **Step 4: Commit 部署记录**

```bash
cd D:/AI/AI4TALENT-lab-web
git add -A
git commit -m "chore(crawler-skill): deploy to ~/.agents/skills/ai-lab-talent-crawler"
```

---

## 完工核对清单（对应 spec §11 验收标准）

- [ ] 1. skill 可被触发（Task 8 Step 3）
- [ ] 2. agent 从 ai.stanford.edu 自主探索到 /faculty/ 和子实验室（Task 7 Step 2）
- [ ] 3. 输出符合 schema 的 JSONL（Task 7 Step 3）
- [ ] 4. 区分教授与 PhD 学生（Task 7 Step 3 角色分布）
- [ ] 5. cohort_year 可达时正确提取（Task 7 Step 3 — 检查有 cohort_source 的条目）
- [ ] 6. 完成报告 + 探索路径生成（Task 7 Step 4）
- [ ] 7. 部分成功（单子站失败不丢全部）（Task 7 Step 2 观察）
- [ ] 8. JSONL 能被 importer 契约消费（字段对齐，Task 3 schema + Task 5 contract）
```
