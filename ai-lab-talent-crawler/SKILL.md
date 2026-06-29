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
