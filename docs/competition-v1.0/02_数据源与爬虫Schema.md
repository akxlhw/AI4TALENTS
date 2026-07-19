# 02 数据源与爬虫 Schema

> 竞赛人才域 v1.0 —— 数据源评估、`comp-talent-crawler` 设计、JSONL 输出契约

## 1. 数据源评估矩阵

> 以用户确认的关注清单为准（2026-07-18）：ICPC、国际奥林匹克（IOI 为主）、IMC、CTF、Kaggle、RoboCup、超算三赛（ASC/SC/ISC）。Codeforces 作为配套采集源保留（官方 API + 与 ICPC/IOI 人群高度重叠）。

| 源 | 个人/团队 | 官方数据渠道 | 可得字段 | 采集难度 | 分期 |
|----|----------|-------------|---------|---------|------|
| **Codeforces**（配套） | 个人 | ✅ 官方 REST API，无需 Key，≤1 req/2s | 画像（rating/max/title/organization/country/头像）+ 榜单（名次/rating 变动） | **低**（HTTP+JSON） | **M1** |
| **ICPC** | 团队（3 人+教练） | icpc.global 赛果页（HTML）、ICPC Live standings | 队伍名次/奖牌、学校、队员名单（部分年份） | 中（HTML 解析 + 队拆人） | M2 |
| **国际奥林匹克（IOI/IMO/IPhO 主线）** | 个人 | ioinformatics.org + stats.ioinformatics.org（信息学）、imo-official.org（数学）、iphounesco.org（物理）历年成绩 | 个人名次/奖牌/分数、国家/地区 | 中 | M2 |
| **Kaggle** | 个人+团队混合 | kaggle.com 竞赛榜单（JS 渲染）+ 用户档案 tier | 竞赛名次、用户段位（Grandmaster 等）、队伍成员 | 高（无官方 API） | M2-M3 |
| **IMC 国际大学生数学竞赛** | 个人 | imc-math.org.uk 历年结果（HTML/PDF） | 个人奖项（Grand Prize/一/二/三等奖）、学校、国籍 | 中 | M3 |
| **CTF 安全夺旗赛** | 团队为主 | CTFtime.org 队伍排名/赛事结果（HTML） | 队伍名次、队名、国家；**成员信息弱** | 高 | M3（先队伍级） |
| **RoboCup 机器人世界杯** | 团队 | robocup.org 历年成绩（HTML/PDF） | 队伍名次、学校、国家；成员弱 | 高 | M3（先队伍级） |
| **ASC / SC / ISC 超算** | 团队 | ASC 官网、SC 会议官网、ISC-HPCAC 赛果 | 队伍名次/奖项、学校；成员名单部分可得 | 高（分散、PDF 多） | M3（先队伍级） |
| AtCoder（候选插入） | 个人 | kenkoooo 三方 API + 页面 HTML | 用户 rating/段位、榜单 | 中 | 视优先级插 M2-M3 |

**团队赛占大头的结构性结论**：ICPC/CTF/RoboCup/超算三赛均以队伍为参赛单元，且成员信息公开度普遍较弱——模型层新增 `comp_team`（见 [01 文档 §3.5](01_架构与数据模型.md)），schema 层新增 `type: "team"` 行（见本文 §3.5）；成员拿不全的源先落队伍级数据，`team_members` 有多少收多少，不为难爬虫。

**M1 只用 Codeforces**，关键端点：

| 端点 | 用途 | 说明 |
|------|------|------|
| `GET /api/contest.list?gym=false` | 赛事清单 | 过滤近 N 年、CF 正式轮次 |
| `GET /api/contest.standings?contestId=<id>&from=1&count=<n>&showUnofficial=false` | 榜单 | 含 rank、party.members(handles)、oldRating/newRating；单次最多 10000 行 |
| `GET /api/user.info?handles=<h1;h2;...>` | 选手画像 | rating/maxRating/titlePhoto/avatar/organization/country/firstName+lastName |

## 2. 爬虫 skill：`comp-talent-crawler`

与 `ai-lab-talent-crawler` 同目录级别的兄弟 skill（用户目录 `~/.agents/skills/comp-talent-crawler/`）。

### 2.1 模式选择

- **M1（Codeforces）：纯 HTTP+JSON 模式**，不依赖浏览器服务——官方 API 就是 JSON，零 LLM、零渲染，最快最稳
- M2+（AtCoder/ICPC）：复用 lab skill 的「HTTP 直连判定」策略——能静态解析就 HTTP+parser，否则浏览器模式

### 2.2 采集流程（Codeforces）

```
输入：sources.yaml（源配置）+ 采集范围（如：近 3 年 Div1/Div2、单赛事 id、或全量历史）
1. contest.list → 过滤目标赛事集合（按时间/类型/状态）
2. 对每个赛事：
   a. contest.standings → 全量/Top N 榜单行
   b. 取榜单中涉及的 handles（M1：全部收录；画像补全取 Top 500）
   c. user.info 批量（每次 ≤ 10k handles 拼接，分块请求）
   d. 按 §3 schema 写 JSONL（meta → series → contest → person 行）
   e. 每个赛事完成立即落盘 checkpoint（中断可续采，同 lab skill 惯例）
3. 产出：output/codeforces/<contest_id>/_YYYY-MM-DD.jsonl（一场一个文件 = 导入原子单位）
```

### 2.3 限流与重试

- 请求间隔 ≥ 2s（可配置）；HTTP 429/5xx → 指数退避（2s/4s/8s，3 次）
- `status != "OK"` 的 API 响应视为失败行，记 skip 原因继续
- 断点：`<contest_id>/_checkpoint_*.jsonl`；重启时跳过已完成的 contest 目录

## 3. JSONL 输出契约（schema_version "1.0"）

### 3.1 文件约定

- 路径：`output/<source_code>/<contest_external_id>/_YYYY-MM-DD.jsonl`
- 行序固定：**meta → series → contest → team × 0..N → person × N**（团队赛可有 team 行；person 必须最后，不允许交错）
- 编码 UTF-8，一行一个合法 JSON

### 3.2 `meta` 行（第 1 行，必有且仅一条）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | ✅ | string | 固定 `"meta"` |
| `schema_version` | ✅ | string | 固定 `"1.0"`；导入端不兼容即拒收 |
| `source_code` | ✅ | string | 源机器码（`codeforces`） |
| `contest_external_id` | ✅ | string | 本文件对应的源站赛事 ID（导入替换键） |
| `crawler` | ✅ | string | `comp-talent-crawler` |
| `crawler_version` | ✅ | string | 爬虫版本（如 `1.0.0`） |
| `collected_at` | ✅ | string | ISO8601 采集时间 |

### 3.3 `series` 行（第 2 行，必有且仅一条）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | ✅ | string | 固定 `"series"` |
| `code` | ✅ | string | 系列机器码，与 meta.source_code 一致 |
| `name` | ✅ | string | 展示名（如 "Codeforces"） |
| `name_en` | 可选 | string | |
| `homepage` | 可选 | string | |
| `description` | 可选 | string | |
| `logo_url` | 可选 | string | |

### 3.4 `contest` 行（第 3 行，必有且仅一条）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | ✅ | string | 固定 `"contest"` |
| `external_id` | ✅ | string | 与 meta.contest_external_id 一致 |
| `name` | ✅ | string | 赛事名 |
| `start_time` | 可选 | string | ISO8601（UTC） |
| `duration_seconds` | 可选 | integer | |
| `season` | 可选 | string | 如 `"2026"` |
| `status` | 可选 | string | `finished`（默认）/ `ongoing` / `upcoming` |
| `source_url` | 可选 | string | 源站榜单页 |
| `raw_meta` | 可选 | object | 源站附加字段（phase/type/frozen 等） |

### 3.5 `team` 行（contest 行之后，0..N 条；团队赛使用，个人赛省略）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | ✅ | string | 固定 `"team"` |
| `name` | ✅ | string | 队名（原始大小写，非空） |
| `school` | 可选 | string | 学校/组织（ICPC/超算的学校队） |
| `country_code` | 可选 | string | ISO 两字母 |
| `logo_url` | 可选 | string | 队徽/校徽 |
| `members` | 可选 | array[object] | 本场队员 `[{handle?, real_name, role?}]`——handle 拿不到就只给 real_name，成员信息弱的源允许只给队名 |
| `result` | ✅ | object | 该队在本场赛事的成绩（字段同 person 的 result，见 §3.6） |

> 队伍成绩落在 team 行的 `result` 里；队员个人若同时有个人成绩（如 ICPC 无个人分），不必重复出 person 行——person 行只放"以个体身份参赛"的记录。

### 3.6 `person` 行（最后，≥1 条；团队赛可为 0 条）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `type` | ✅ | string | 固定 `"person"` |
| `handle` | ✅ | string | 平台账号（非空；无账号类源用 `name:<姓名>` 约定形参，见关键规则 3） |
| `real_name` | 可选 | string | |
| `school` | 可选 | string | 学校/组织（Codeforces organization） |
| `country_code` | 可选 | string | ISO 两字母 |
| `avatar_url` | 可选 | string | |
| `profile_url` | 可选 | string | 源站个人主页 |
| `rating` | 可选 | integer | 选手当前积分（user.info.rating；聚合优先取它） |
| `max_rating` | 可选 | integer | user.info.maxRating |
| `rank_title` | 可选 | string | user.info.rank/maxRank（原样保留，展示层再汉化） |
| `specialties` | 可选 | array[string] | 源站可得才填 |
| `team_name` | 可选 | string | 该选手本场所属队名（关联 team 行用，不写则视为个人参赛） |
| `result` | ✅ | object | 该选手在本场赛事的成绩（见下表） |

`result` 子对象（person 与 team 行共用）：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `rank` | ✅* | integer | 名次（榜单类必填；名单参与类可空但需给 `participated: true`） |
| `score` | 可选 | number | 得分 |
| `rating_before` | 可选 | integer | 赛前 rating（standings.oldRating，仅个人赛） |
| `rating_after` | 可选 | integer | 赛后 rating（standings.newRating，仅个人赛） |
| `award` | 可选 | string | `gold` / `silver` / `bronze` / `hm` / `none` |
| `team_name` | 可选 | string | 冗余展示用队名（实体关联以 team 行/person.team_name 为准） |
| `raw_meta` | 可选 | object | 源站原始行（party/penalty 等） |

### 3.7 关键规则（与 lab schema 同款精神）

1. **提取不到的字段直接省略**——不写 null、不写空字符串、不猜测
2. **`handle` 必填且非空**——缺 handle 的 person 行爬虫侧直接丢弃并记入报告
3. **无账号类源的身份约定**：源站只有姓名没有账号时（ICPC/IMC 名单），handle 用 `name:<规范化姓名>`（小写、空格转下划线，如 `name:gennady_korotkevich`）作形参，后续发现真人账号时通过 `unified_person_id` 归并
4. **identity 只看 handle**：真名/学校是可变画像字段，不参与去重；handle 去重统一小写比较，存储保留原始大小写
5. **team 身份键**：`(source_code, lower(name), school)`；同名不同校是两个队（ICPC 校队重名常见）
6. **一个文件 = 一场赛事**：`meta.contest_external_id`、contest 行、team/person 行全部指向同一场；导入端发现不一致直接拒收
7. **rating 取数优先级**：person.rating（user.info 最新）> result.rating_after > result.rating_before——导入端按此规则重算 `comp_talent.current_rating`
8. **不写死平台特有字段**：Codeforces 特有信息（rank 段位原文、contribution 等）一律进 `raw_meta`，顶层字段保持多源通用
9. **团队赛人员归属**：队伍成绩写 team 行；队员个人信息不足的，只在 team.members 记录，不强行生成 person 行

### 3.7 示例

```json
{"type":"meta","schema_version":"1.0","source_code":"codeforces","contest_external_id":"1950","crawler":"comp-talent-crawler","crawler_version":"1.0.0","collected_at":"2026-07-20T08:00:00Z"}
{"type":"series","code":"codeforces","name":"Codeforces","name_en":"Codeforces","homepage":"https://codeforces.com","description":"Competitive programming platform","logo_url":"https://codeforces.org/s/0/codeforces-logo.png"}
{"type":"contest","external_id":"1950","name":"Codeforces Round 951 (Div. 1)","start_time":"2024-05-30T14:35:00Z","duration_seconds":7200,"season":"2024","status":"finished","source_url":"https://codeforces.com/contest/1950/standings","raw_meta":{"type":"CF","phase":"FINISHED"}}
{"type":"person","handle":"tourist","real_name":"Gennady Korotkevich","school":"ITMO University","country_code":"BY","avatar_url":"https://userpic.codeforces.org/422/title.jpg","profile_url":"https://codeforces.com/profile/tourist","rating":3948,"max_rating":3979,"rank_title":"legendary grandmaster","result":{"rank":1,"score":null,"rating_before":3904,"rating_after":3948,"award":"gold","raw_meta":{"points":5200.0,"penalty":0}}}
{"type":"person","handle":"jiangly","school":"Zhejiang University","country_code":"CN","profile_url":"https://codeforces.com/profile/jiangly","rating":3756,"max_rating":3812,"rank_title":"international grandmaster","result":{"rank":3,"rating_before":3711,"rating_after":3756,"award":"bronze"}}
```

**团队赛示例（ICPC，含 team 行、person 行可为 0 条）：**

```json
{"type":"meta","schema_version":"1.0","source_code":"icpc","contest_external_id":"icpc-2024-world-finals","crawler":"comp-talent-crawler","crawler_version":"1.1.0","collected_at":"2026-08-01T08:00:00Z"}
{"type":"series","code":"icpc","name":"国际大学生程序设计竞赛","name_en":"ICPC","homepage":"https://icpc.global","description":"International Collegiate Programming Contest"}
{"type":"contest","external_id":"icpc-2024-world-finals","name":"2024 ICPC World Finals","start_time":"2024-09-17T10:00:00Z","season":"2024","status":"finished","source_url":"https://icpc.global/worldfinals/results/2024"}
{"type":"team","name":"MIPT: Red Pine","school":"MIPT","country_code":"RU","members":[{"real_name":"Member A"},{"real_name":"Member B"},{"real_name":"Member C"}],"result":{"rank":1,"award":"gold","raw_meta":{"solved":10,"penalty":1350}}}
{"type":"team","name":"ZJU: Fantasia","school":"Zhejiang University","country_code":"CN","members":[{"real_name":"队员甲"},{"real_name":"队员乙"},{"real_name":"队员丙"}],"result":{"rank":5,"award":"bronze","raw_meta":{"solved":8,"penalty":1120}}}
```

### 3.8 爬虫自检（写盘前必过）

- 行序：meta(1) → series(1) → contest(1) → team(0..N) → person(≥0；个人赛 ≥1)
- 每行合法 JSON；person 行 `handle` 非空率 100%；team 行 `name` 非空率 100%
- meta.source_code == series.code；meta.contest_external_id == contest.external_id
- person 行数与源站榜单行数一致（±0，不一致记 warning 入采集报告）；团队赛以 team 行数对齐
