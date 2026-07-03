# v2 验收审计报告（lab_web_site LLM 采集）

- **日期**：2026-06-29
- **审计对象**：spec `2026-06-29-lab-site-llm-collection-design.md` §9 的 10 条验收标准
- **结论**：10 条中 9 条完成（证据确凿），第 8 条（真实 LLM 验收）被**外部凭证依赖**阻塞——非工程缺陷。

---

## 验收标准逐条审计

### ✅ §9.1 — lw_site_config + lw_site_raw_page 两表建出，预置 3 站点
**证据**：迁移 `051_add_lab_web_site`（commit `6aa30ca`）。
```
lw_site_config 3   (stanford_nlp_group / stanford_snap / stanford_ermon)
lw_site_raw_page 0
```
`alembic upgrade head` 实际执行成功（输出 `Running upgrade 050 -> 051`）。

### ✅ §9.2 — SourceType.LAB_WEB_SITE 枚举 + 模型注册
**证据**：enums.py（commit `272cc61`）；model_registry.py 含 `LWSiteConfig, LWSiteRawPage`（commit `6aa30ca`）。
```python
SourceType.LAB_WEB_SITE = "lab_web_site"  # 存在
```

### ✅ §9.3 — BaseLabSiteCollector LLM 管线跑通（mock 测试覆盖全流程）
**证据**：commit `f4b3395`，3 个集成测试全过：
- `test_collect_writes_raw_and_syncs_core_talent`
- `test_collect_uses_cache_on_html_hash_hit`（断言 LLM 未被调用）
- `test_collect_needs_review_on_empty_parse`

### ✅ §9.4 — 缓存逻辑工作（同 html_hash 不重复调 LLM；force_reparse 强制重解析）
**证据**：`test_collect_uses_cache_on_html_hash_hit` 断言 `llm.complete.assert_not_awaited()`；`find_cached_page` 仅在 `parse_status='parsed'` 时命中。

### ✅ §9.5 — schema 校验拦截非法 LLM 输出（重试 + needs_review）
**证据**：`test_parse_invalid_json_flagged` / `test_parse_missing_name_flagged` / `test_parse_retries_once_then_fails`（commit `d3a1f00`）。

### ✅ §9.6 — 人员写入 core_talent（source_type=lab_web_site），role_type 正确映射
**证据**：`test_sync_creates_core_talent_with_role`（commit `daf214c`）断言 PhD Students → STUDENT（conf 1.0）。

### ✅ §9.7 — 跨源隔离（v2 不碰 v1/openalex）
**证据**：`test_sync_isolates_from_v1_and_openalex`（commit `daf214c`）。

### ⚠️ §9.8 — 手动验收：真实 LLM 抓 NLP Group，拿到带角色的学生数据
**状态：被外部凭证依赖阻塞，非工程缺陷。**

#### 准验收（已通过，证明除真实 LLM 准确率外的整条链路）
真实抓取 NLP Group 页面（160KB）+ mock LLM（模拟返回）→ `parse_status='parsed'` → 3 人写入 core_talent，角色分类正确：
```
Christopher Manning  | role_type=professor | conf=1.0 | section=Faculty
Aryaman Arora        | role_type=student   | conf=1.0 | section=PhD Students
Jane Student         | role_type=student   | conf=1.0 | section=PhD Students
```

#### 真实 LLM 验收（未执行 — 阻塞原因证据）
环境中**无任何可用 LLM**（三次独立验证，证据一致）：
- `backend/.env`：21 行，`grep -ic llm` = **0**（mtime 2026-06-28 23:14，自复制以来未被修改）
- `settings.LLM_ENABLED` = `False`，`settings.LLM_API_KEY` = 空（清缓存后仍如此）
- 环境变量：无 `DEEPSEEK/OPENAI/ZHIPU/LLM/API_KEY` 相关
- 主仓库 `D:/AI/AI4TALENT/backend/.env`：也无 LLM 配置
- `system_config` 表：开发库不存在（未跑种子）
- 本地服务：无 ollama（:11434）/ LM Studio（:1234）/ vLLM（:8080）

#### 解除阻塞
需在 `.env` 配置 `LLM_ENABLED=true` + `LLM_API_KEY=<真实key>`，然后：
```bash
cd D:/AI/AI4TALENT-lab-web/backend && uv run python scripts/ops/accept_lab_web_site.py
```
脚本（commit `8d0a9e6`）已就绪，会真实抓取 NLP Group + 真实 LLM 解析 + 报告角色分布供人工核对准确率。

### ✅ §9.9 — ruff + black + mypy gate + check_architecture 全绿
**证据**（本次审计实测）：
```
85 passed                                    # 全量 lab_web 测试
ruff: All checks passed!
black: 32 files would be left unchanged
mypy gate: PASS (1298 errors, all in baseline)
architecture: PASSED (cross-domain / endpoint / http client 三项)
```

### ✅ §9.10 — 不破坏 v1（v1 的 43 测试仍通过）
**证据**：85 总数 = v1 43 + v2 42，全部 PASSED。

---

## 终审修复（commit `c19f695`）

独立 Explore subagent 终审发现的 6 个问题全部处理：
- **M3**：_run_collection except 分支 now checks latest page status before defaulting to 'failed'
- **M5**：_resolve_lab_id → resolve_lab_id（公开，service 不再碰 repo 内部）
- **M4**：/review endpoint 返回 parsed_persons + html_hash（人工审核需要）
- **I1**：retry 层叠成本文档化（parser retry × gateway retry = 最多 6 次）
- **I3**：cache 用 raw HTML hash 文档化（动态内容可能 bust cache）
- **I2**：编排 happy-path 测试（_run_collection 调 collector 一次，不抛异常）

---

## 总结

| 维度 | 状态 |
|------|------|
| 计划拆解 | ✅ `55d8826` |
| 代码实施（10 task） | ✅ 12 commit |
| 单元/集成测试 | ✅ 85 全绿 |
| 独立终审 + 修复 | ✅ 6 问题处理 |
| 4 道质量门禁 | ✅ 全 PASS |
| 准验收（真实 HTML + mock LLM） | ✅ 链路 + 角色分类正确 |
| 真实 LLM 验收 | ⚠️ 阻塞于无 API key（外部凭证依赖） |

**代码与工程验证 100% 完成**。唯一未执行的 §8 真实 LLM 验收，其前置条件（LLM API 凭证）不存在于本环境中，且无法由代码工作自主获得——这是外部依赖阻塞，不是工程缺陷。验收脚本已就绪，凭证就位即可一键完成。
