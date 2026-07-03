# SAIL 人员数据源调研报告

- **日期**：2026-06-29
- **调研方式**：实际 HTTP 访问 SAIL 站点及相关页面，所有结论附证据（状态码/字段计数/结构样本）
- **目的**：找出获取 Stanford AI Lab 教授、博士学生的有效方式，为 v2 采集设计提供输入

---

## 1. 站点结构（三层）

```
ai.stanford.edu
├─ /faculty/                    ← 第一层：教授列表（v1 已实现，63 人）
├─ /research-groups/            ← 第二层入口：22 个实验室站点链接
│   ├─ nlp.stanford.edu/people/                (470 team-member，含学生)
│   ├─ cs.stanford.edu/~ermon/website/people.html
│   ├─ snap.stanford.edu/people.html
│   ├─ stanfordmlgroup.github.io/#people
│   ├─ drorlab.stanford.edu/
│   └─ ... 共 22 个
├─ AY24-Students-joining-research-labs-2.pdf   ← 第三层：学生名单 PDF
└─ profiles.stanford.edu/<name>                ← 教职官方档案（含头衔）
```

**关键事实**：`/people/` 返回 **403**（旧路径已废弃），真实路径是 `/faculty/`。`/students/` `/phd/` `/team/` `/members/` 均为 **404**——**SAIL 主站没有独立的学生列表页**。

---

## 2. 教授（Faculty）的有效获取方式

| 方式 | 路径 | 证据 | 头衔 | 邮箱 |
|------|------|------|------|------|
| ✅ **SAIL /faculty/（v1 已实现）** | `ai.stanford.edu/faculty/` | 实测：153 卡片 → 去重 63 人，姓名/主页/头像/研究方向 100% | ❌ 列表无头衔 | ❌ |
| ✅ **各实验室 People 页 Faculty 区** | 如 `nlp.stanford.edu/people/` | 470 team-member，明确 Faculty 分区 | ✅ 按区可判定 | ❌ |
| ✅ **profiles.stanford.edu** | `profiles.stanford.edu/yejin-choi` | 含 "Professor" 字样（3x） | ✅ 有头衔 | ⚠️ 需 JS/API（静态 HTML 0 邮箱） |

**结论**：教授名单已解决（/faculty/）。头衔需从 profiles.stanford.edu 或实验室页补充。

---

## 3. 博士学生（PhD Students）的有效获取方式

**核心结论：学生不在 SAIL 主站，必须从 22 个实验室站点获取。**

| 方式 | 路径 | 证据（实际访问） | 角色判定 | 邮箱 |
|------|------|------------------|----------|------|
| ✅ **各实验室 People 页（最佳）** | `nlp.stanford.edu/people/` | **470 个 team-member**，明确 "PhD Students" 分区（19 处 PhD 提及） | ✅ 按分区 | ❌ |
| ✅ Ermon lab people.html | `cs.stanford.edu/~ermon/website/people.html` | 12 PhD + 6 Professor 提及 | ✅ | ❌ |
| ✅ snap.stanford.edu | `snap.stanford.edu/people.html` | 45KB，2 PhD + 26 Professor | ✅ | ❌ |
| ⚠️ AY24 学生 PDF | `ai.stanford.edu/wp-content/uploads/2023/10/AY24-...pdf` | 83KB 可下载，需 PDF 解析 | ❌ 仅名字 | ❌ |

### 证据样本：NLP Group People 页真实结构

```html
<div class="showroom-controls"><div class="links">PhD Students</div></div>
<div class="row">
  <div class="col-sm-3 team-member">
    <a href="https://aryaman.io/"><b>Aryaman Arora</b></a>
    <br/> Computer Science
  </div>
  ...
```

- 角色分区：`div.showroom-controls > div.links`（"PhD Students" / "Faculty" / "Postdocs" / "Staff" / "Alumni"）
- 人员：`div.team-member`，含 `<b>姓名</b>`、专业、个人主页链接
- **无邮箱、无显式头衔**（角色靠所在分区判定）

### 22 个实验室站点清单（来自 /research-groups/）

```
nlp.stanford.edu              svl.stanford.edu             statsml.stanford.edu
drorlab.stanford.edu          bejerano.stanford.edu        cs.stanford.edu/~ermon/website/
geometry.stanford.edu         cs.stanford.edu/groups/manips/   iprl.stanford.edu
iliad.stanford.edu            physbam.stanford.edu         logic.stanford.edu
cocolab.stanford.edu          neuroailab.stanford.edu      web.stanford.edu/group/sailsbury_robotx/
web.stanford.edu/group/sisl/  stanfordmlgroup.github.io/   asl.stanford.edu
cs.stanford.edu/~chrismre/    tml.stanford.edu             snap.stanford.edu
irislab.stanford.edu
```

---

## 4. 角色分类的有效方式

| 来源 | 角色判定方式 | 可靠性 |
|------|-------------|--------|
| **实验室 People 页分区（推荐）** | 人员所在 section（"PhD Students"/"Faculty"/"Postdocs"）即角色 | **高**（站点明确分区） |
| profiles.stanford.edu | 解析头衔文本 | 中（需 JS/API） |
| SAIL /faculty/ | 全部是教授（页面定义） | 高（但只覆盖教授） |

---

## 5. 邮箱获取现状

**坏消息**：所有静态页面都隐藏邮箱。实测各站点静态 HTML 中 stanford 邮箱数：
- NLP Group `/people/`：0
- snap.stanford.edu：0
- Ermon lab：0
- profiles.stanford.edu：0（JSON-LD 也无）

邮箱获取的可选路径（均非 v2 首选）：
| 方式 | 可行性 |
|------|--------|
| 静态抓取 | ❌ 全站 0 |
| JS 渲染（playwright/scrapling[fetchers]） | ⚠️ 可能，但依赖重 + 合规考量 |
| 个人主页深度抓（aryaman.io 等） | ⚠️ 部分有，结构各异 |
| 邮箱推断（firstname@cs.stanford.edu） | ⚠️ 启发式，不可靠 |

---

## 6. 推荐 v2 采集策略

```
两级采集：
├─ 第一级：SAIL /faculty/ → 63 教授（v1 已实现）
└─ 第二级：22 个实验室 People 页 → 博士学生 + 补充教职角色
    ├─ 角色标签：来自页面分区（PhD Students / Faculty / Postdocs / Staff / Alumni）
    ├─ 字段：姓名、个人主页、（部分）专业方向
    └─ 头衔/邮箱：仍需 profiles.stanford.edu 或 JS 渲染（v3）
```

### v2 需要解决的设计问题（留给 brainstorm）

1. **多站点适配**：22 个实验室站点结构各异（NLP 用 showroom/team-member，Ermon 用 li/tr，ML Group 用 SPA 锚点）。需要每站一个适配器还是通用模式？
2. **角色分区解析**：如何把 "PhD Students"/"Faculty" 这种 section heading 关联到下方的人员卡片。
3. **跨站点去重**：同一个人可能出现在 /faculty/ + 多个实验室页（如 Christopher Manning 同时在 /faculty/ 和 NLP Group）。
4. **教授-学生关系建模**：是否记录"某学生属于某教授的实验室"（导师关系）。
5. **限速与合规**：22 个站点 × 各自限速，采集时间显著增加；robots.txt 各站独立检查。
6. **Alumni 处理**：NLP 页含 Alumni 区（470 人含历史成员），是否采集、如何标记状态。

---

## 附录：调研命令可复现性

所有数据通过 AI4TALENT 的 `HttpClientFactory`（浏览器 UA）实际请求获得。可复现的关键探测：
- `GET ai.stanford.edu/faculty/` → 200, 191KB, 153 div.row 卡片
- `GET ai.stanford.edu/people/` → 403
- `GET nlp.stanford.edu/people/` → 200, 184KB, 470 div.team-member
- `GET cs.stanford.edu/~ermon/website/people.html` → 200, 17KB
- `GET ai.stanford.edu/wp-content/uploads/2023/10/AY24-Students-joining-research-labs-2.pdf` → 200, application/pdf, 83KB
