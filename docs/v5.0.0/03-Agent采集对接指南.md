# 行业人才采集 Agent 对接指导书

> 版本：v1.0 | 日期：2026-08-05 | 适用：smart-talent-sourcing skill / 采集 Agent
> 目标：实现「拉取岗位 → 定向采集 → 推送候选人」的全自动闭环

---

## 1. 闭环全景

```
┌──────────────┐   ① GET /industry/positions?status=open   ┌──────────────┐
│              │ ◄────────────────────────────────────────  │              │
│   采集 Agent │   岗位清单（JD/职级/技术方向/position_id）   │  AI4TALENT   │
│  （本 skill）│                                           │   行业人才库  │
│              │   ③ POST /industry/import（JSONL）          │              │
│              │ ────────────────────────────────────────►  │              │
└──────────────┘        ② 按岗位 JD 定向采集 + 三维打分       └──────────────┘
```

Agent 不需要登录账号，全程使用一个静态 API Key（`X-API-Key` 请求头）。

---

## 2. 认证

| 项 | 值 |
|----|----|
| 请求头 | `X-API-Key: <密钥>` |
| 密钥配置 | 系统配置 → 行业人才导入 Tab → API Key 配置面板（`INDUSTRY_IMPORT_API_KEY`） |
| 生效方式 | 热更新（缓存 5 分钟 TTL），改配置无需重启 |

**错误码**：`401` 密钥缺失或不匹配；`503` 管理员尚未配置密钥（提示管理员先配置）。

---

## 3. 第一步：拉取岗位清单

```
GET /api/v1/industry/positions?status=open
X-API-Key: <密钥>
```

`status` 可选 `open / closed / archived`，Agent 固定用 `open`（只在招岗位值得采集）。

**响应**：岗位对象数组（无分页，当前岗位量级直接全量返回）：

```json
[
  {
    "position_id": 4,
    "title": "语言大模型资深科学家",
    "department": "云平台事业部",
    "tech_direction_codes": ["llm", "llm_inference"],
    "level_min": 19,
    "level_max": 20,
    "jd_text": "负责大模型推理优化…",
    "jd_features": {"skills": ["CUDA", "vLLM"], "target_companies": ["…"]},
    "status": "open",
    "candidate_count": 0,
    "avg_match_score": null
  }
]
```

**Agent 侧要点**：

- `position_id` 是后续推送的必填关联键，原样保留
- `jd_text` / `jd_features` / `tech_direction_codes` / `level_min~max` 是采集与打分的输入
- 建议每次采集任务启动时拉取一次（岗位可能新增/归档），不要本地缓存过期清单

---

## 4. 第二步：定向采集与打分

对准每个岗位的 JD 执行采集（脉脉/LinkedIn 等），并产出三维打分：

| 分数 | 含义 | 说明 |
|------|------|------|
| `match_score` | 匹配总分 0-100 | 卡片视觉锚点，列表默认按它降序 |
| `score_school` | 院校维度 0-100 | 可空；全部为空时前端自动降级只显总分 |
| `score_company` | 企业维度 0-100 | 可空 |
| `score_direction` | 方向维度 0-100 | 可空 |

**采集建议**：

- 职级范围（level_min/max）映射为候选人资历过滤条件，避免采回明显不符的人
- `match_tags` 用短标签（如 `顶级院校`、`美企巨头`、`LLM`），卡片上直接展示，3-5 个为宜
- `match_reason` 一句话说明为什么推荐，详情页展示
- **同一候选人命中多个岗位**：分别按各岗位打分，推送时按岗位分批（见第 5 节）

---

## 5. 第三步：推送候选人 JSONL

```
POST /api/v1/industry/import?position_id=4&batch=2026-08-llm
X-API-Key: <密钥>
Content-Type: application/x-jsonlines

<JSONL 原始文本（请求体）>
```

| 参数 | 位置 | 必填 | 说明 |
|------|------|------|------|
| `position_id` | query | ✅ | 目标岗位（第 3 步拿到）；行内 `position_id` 字段可逐行覆盖 |
| `batch` | query | 强烈建议 | 批次标识（如 `2026-08-llm`），是「按批次删除」的唯一抓手——误导入可整批回滚 |
| body | body | ✅ | JSONL 文本，UTF-8，≤ 20MB |

**`batch` 必填级建议**：不带 batch 的数据无法在管理后台按批次识别和删除。建议命名规则 `{日期}-{岗位简称}`，同一岗位每天一批。

### 响应：导入报告

```json
{
  "total_lines": 100,
  "total_parsed": 98,
  "talents_inserted": 60,
  "talents_updated": 30,
  "links_inserted": 85,
  "links_updated": 13,
  "skipped": 2,
  "skip_reasons": [{"line": 17, "reason": "missing name"}],
  "warnings": 3,
  "aborted": false
}
```

| 字段 | 含义 |
|------|------|
| `talents_inserted / updated` | 人才主表新增 / 已有更新（dedup 命中） |
| `links_inserted / updated` | 岗位关联新增 / 更新（分数刷新） |
| `skipped` + `skip_reasons` | 无效行（最多返回 50 条，含行号和原因） |
| `warnings` | 缺 `current_org` 的行数（去重区分度弱，建议数据源补齐公司字段） |
| `aborted` | **true = 0 有效行，什么都没写入**（空文件/全无效行的硬守卫） |

**错误码**：`400` 非 UTF-8 / 超 20MB；`401/503` 密钥问题；`404` position_id 不存在；`500` 服务端导入失败（已记审计，可重试）。

### Agent 侧处理建议

- `aborted=true` → 检查 JSONL 生成逻辑，不要把 abort 当成功
- `skipped > 0` → 记录 skip_reasons，修数据后**直接重推整个批次**（幂等，见第 7 节）
- `warnings` 高 → 下次采集补全公司字段

---

## 6. JSONL 契约（schema v1.0）

每行一个候选人 JSON 对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 姓名 |
| `current_org` | string | 强烈建议 | 现任职公司（缺失计入 warnings，去重区分度弱） |
| `current_title` | string | 建议 | 现任职头衔（参与去重 hash） |
| `degree` | string | 否 | 学历（博士/硕士/本科） |
| `years_of_exp` | string | 否 | 工作年限文本（"10年"），系统自动解析数值 |
| `experiences` | array | 否 | `[{"range": "2019-2023", "org": "…", "title": "…"}]`，详情页时间线展示 |
| `expect` | string | 否 | 求职意向 |
| `location` | string | 否 | 所在地 |
| `profile_url` | string | 否 | 脉脉/LinkedIn 主页链接 |
| `photo_url` | string | 否 | 头像 URL |
| `source` | string | 建议 | `maimai` / `linkedin` |
| `match_score` | float | 建议 | 匹配总分 0-100 |
| `score_school` / `score_company` / `score_direction` | float | 否 | 三维子分数 0-100 |
| `match_tags` | array | 否 | 命中标签字符串数组 |
| `match_reason` | string | 否 | 推荐理由（一句话） |
| `position_id` | int | 否 | 行内覆盖 query 参数（一人多岗位场景） |

**完整示例**：

```json
{"name": "张三", "current_org": "亚马逊云科技", "current_title": "应用科学家", "degree": "博士", "years_of_exp": "10年", "experiences": [{"range": "2016-至今", "org": "亚马逊云科技", "title": "应用科学家"}, {"range": "2011-2016", "org": "CMU", "title": "博士"}], "expect": "大模型推理方向技术专家", "location": "北京", "profile_url": "https://…", "source": "maimai", "match_score": 98, "score_school": 95, "score_company": 90, "score_direction": 99, "match_tags": ["顶级院校", "美企巨头", "LLM"], "match_reason": "CMU 博士，AWS 大模型推理团队 10 年"}
```

---

## 7. 增量语义（对 Agent 最重要的三条保证）

推送是**幂等**的，同一批次可以反复推：

1. **人才去重**：`sha256(name + current_org + current_title)` 命中即更新，不重复创建
2. **空字段不覆盖**：本次缺的字段不会抹掉库里的旧值——放心只推你有数据的字段
3. **招聘状态保留**：招聘方在系统里改的触达状态/备注（touched/status/notes）**永远不会被推送覆盖**；分数和标签会刷新
4. **缺席不删除**：本次没推的人不受影响——不是全量替换语义

---

## 8. 注意事项速查

| 项 | 值 |
|----|----|
| 单文件上限 | 20MB（超了分批推） |
| 编码 | 必须 UTF-8 |
| 单批次行数 | 无硬限制；建议 ≤5000 行/批，便于定位问题 |
| 重复推送 | 安全（幂等 upsert） |
| 误导入回滚 | 管理后台「行业人才岗位/导入」按 `batch` 整批删除 |
| 审计 | 每次推送记录来源 IP、岗位、批次、行数 |

## 9. 排错速查

| 现象 | 原因 | 处理 |
|------|------|------|
| 503 | 管理员未配置 API Key | 提醒管理员在导入 Tab 配置 |
| 401 | 密钥错误/缺失 | 检查 X-API-Key 头 |
| 404 | position_id 不存在 | 重新拉岗位清单核对（可能已归档） |
| `aborted=true` | 0 有效行 | 检查 JSONL 生成（常见：name 缺失、JSON 语法错误） |
| skipped 行多 | 字段类型不符 | 按 skip_reasons 的行号定位修复后重推 |
