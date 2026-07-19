# 竞赛人才域（Competition Talent）设计文档 v1.0

> 目标版本：**V4.0.0**　状态：设计评审稿　日期：2026-07-18

## 1. 背景与目标

竞赛人才库是平台第四个业务域（学术 / 开源 / 实验室 / 竞赛），面向招聘团队发现顶尖竞赛选手：ACM-ICPC、Codeforces、AtCoder、NOI/NOIP、Kaggle、数学建模（MCM/ICM）、CTF 等赛事的参赛者。

设计原则（全部继承自既有三域的教训与惯例）：

1. **跨域隔离铁律**：独立 `comp_*` 表族 + 独立 `domains/competition/` 包，不复用 `core_talent`、不导入其他业务域内部模块
2. **爬虫-导入契约分离**：爬虫（独立 skill，产出 JSONL）与导入服务（后端 `CompImportService`）之间只通过版本化 schema 通信，如同 lab 域的 `ai-lab-talent-crawler` 模式
3. **官方 API 优先**：首选有官方公开 API 的数据源（Codeforces），浏览器爬取作为无 API 源的降级手段
4. **导入防御性**：空文件/全无效行**不得清空既有数据**（lab 域 V3.1.0 已踩过此坑，本设计直接内置守卫）

## 2. 范围

### 2.1 目标赛事（用户确认的关注清单，2026-07-18）

| # | 赛事 | 个人/团队 | 数据可得性 | 分期 |
|---|------|----------|-----------|------|
| 1 | **ICPC 国际大学生程序设计竞赛** | 团队（3 人 + 教练） | icpc.global 赛果页 + ICPC Live standings | M2 |
| 2 | **国际奥林匹克竞赛**（主线：IOI 信息学 / IMO 数学 / IPhO 物理；化学、生物暂缓） | 个人 | ioinformatics.org（含 stats.ioinformatics.org）、imo-official.org、iphounesco.org 历年成绩 | M2 |
| 3 | **IMC 国际大学生数学竞赛** | 个人 | imc-math.org.uk 历年结果 | M3 |
| 4 | **CTF 安全夺旗赛** | 团队为主 | CTFtime.org 队伍排名/赛事结果（成员信息弱，先队伍级） | M3 |
| 5 | **Kaggle 大数据科学竞赛** | 个人+团队混合 | kaggle.com 榜单（需 JS 渲染）+ 用户 tier 档案 | M2-M3 |
| 6 | **RoboCup 机器人世界杯** | 团队 | robocup.org 历年成绩（先队伍级） | M3 |
| 7 | **超算三赛**：ASC 世界大学生超算 / SC 国际大学生超算 / ISC 国际大学生超算 | 团队 | ASC 官网、SC 会议官网、ISC-HPCAC 赛果（先队伍级） | M3 |

**配套采集源（不在清单内但保留）**：**Codeforces** 仍为 M1 首发源——它是唯一有官方免费 API 的渠道，且与 ICPC/IOI 参赛人群高度重叠（ICPC 选手几乎都有 Codeforces 账号与 rating），能以最低成本先把选手画像库立起来，为清单内赛事的采集提供 handle 锚点。清单内赛事按上表分期接入；AtCoder 视优先级插入 M2-M3。

M1 只交付 Codeforces 一个源，但 schema、模型、导入、前端全部按多源设计（`source_code` 贯穿所有主键与去重键），后续源只加爬虫、不动结构。

### 2.2 M1 功能范围

- 爬虫 skill `comp-talent-crawler`：Codeforces 赛事榜单 + 选手画像采集 → 标准 JSONL
- 后端 `domains/competition/`：4 张表、导入接口、查询 API、统计 API
- 前端竞赛域 4 个页面：概览 / 选手搜索 / 选手详情 / 赛事详情（替换现有 demo 页）
- 管理端：管理员手动上传 JSONL 导入（与 lab 同构）

### 2.3 非目标（本期不做）

- 跨平台身份合并（同一个人在 Codeforces/AtCoder 是两条记录，`unified_person_id` 预留）
- 收藏/对比（lab 域同样未做，后续统一考虑）
- 三维权限（学校/国家/技术要素）对竞赛人才的映射——本期全员可读，仅导入限管理员
- 实时/定时自动同步（M1 为管理员手动触发导入）

## 3. 文档导航

| 文档 | 内容 |
|------|------|
| [01_架构与数据模型.md](01_架构与数据模型.md) | 域结构、数据流、4 张表 DDL 级设计、迁移与索引 |
| [02_数据源与爬虫Schema.md](02_数据源与爬虫Schema.md) | 数据源评估矩阵、`comp-talent-crawler` 设计、**JSONL 输出契约（字段表 + 示例 + 校验规则）** |
| [03_导入接口与标准.md](03_导入接口与标准.md) | 导入端点、校验规则、去重键、替换策略、事务与幂等、错误报告格式 |
| [04_API与前端设计.md](04_API与前端设计.md) | REST 端点、前端 4 页面、权限、测试策略、里程碑拆解 |

## 4. 一句话数据流

```
Codeforces API ──> comp-talent-crawler（HTTP+JSON，无浏览器）
                ──> output/<series>/<contest>/_YYYY-MM-DD.jsonl
                ──> 管理员上传 ──> CompImportService（校验→去重→单事务替换）
                ──> comp_series / comp_contest / comp_talent / comp_result
                ──> 查询/统计 API ──> 竞赛域前端 4 页
```

## 5. 关键设计决策速览

| 决策点 | 结论 | 理由 |
|--------|------|------|
| 导入原子单位 | **按 (source, contest) 全量替换** | 与 lab 按实验室替换同构；榜单天然按场次完整产出 |
| 人员身份键 | `(source_code, lower(handle))` 唯一 | 平台账号稳定；真名不可靠（可选、可重名） |
| 团队建模 | **独立 `comp_team` 表**，`comp_result` 关联 | 用户关注清单中团队赛占大头（ICPC/CTF/RoboCup/超算三赛），队伍是招聘视角的真实单元 |
| 爬虫模式 | M1 纯 HTTP+JSON（官方 API），不引入浏览器依赖 | Codeforces 有公开 REST API，快且稳 |
| 选手聚合字段 | 导入时重算（rating/场次/奖牌）落库 | 查询端零计算成本，榜单页直接排序 |
|  schema 版本 | `schema_version: "1.0"` 写进 meta 行，导入端强校验 | 后续源扩展不破坏旧文件 |
