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
```

> **分页判定由 agent 负责，不靠 LLM 输出**：agent 在拿到提取结果后，自己检查
> snapshot 里是否有 "Next"/"下一页"/"page 2"/"Load more" 等链接或分页控件，
> 有则翻页继续，无则结束本页。不要依赖 LLM 在 JSON 里输出分页信号（它可能漏判或幻觉）。

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
