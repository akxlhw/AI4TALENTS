# lab_web_site v2 实验室站点 LLM 采集 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 lab_web 域新增 v2——用 LLM 驱动解析 3 个实验室站点（NLP/snap/Ermon）的 People 页，获取博士学生 + 角色标签，写入 `core_talent`（`source_type='lab_web_site'`）。

**Architecture:** 抓取层复用 v1 的 ScraplingFetcher（HttpClientFactory + Scrapling Selector）；解析层用项目已有 LLM 网关（需先加通用 `complete()` 方法）。`BaseLabSiteCollector` 固化"抓取→缓存判断→LLM解析→schema校验→入库"流程，子类零代码（config 驱动）。HTML-hash 缓存避免重复 LLM 调用；Pydantic schema 校验 + needs_review 兜底质量。

**Tech Stack:** Python 3.11、FastAPI、SQLAlchemy 2.x（异步）、Alembic、Pydantic v2、OpenAI 兼容 LLM 网关、Scrapling Selector（HTML 预处理）、pytest。

**Spec:** `docs/superpowers/specs/2026-06-29-lab-site-llm-collection-design.md`

**Conventions（来自 AI4TALENT AGENTS.md，务必遵守）:**
- 工作目录：worktree `D:\AI\AI4TALENT-lab-web`，所有后端命令在 `backend/` 下用 `uv run`。
- Endpoint 只能 import Service/Schema/`app.core`；禁止 import Repository/底层 client/LLMGateway。
- 所有出站 HTTP 经 HttpClientFactory；LLM 调用经 LLMGateway。
- 测试用 `talent_db_test`；LLM 全程 mock，绝不真实调 API。
- Conventional Commits。

**运行测试：**
```bash
cd backend && uv run pytest tests/domains/lab_web/ -v
```

---

## 关键决策（自主处理，已记入计划）

**决策：LLMGateway 需新增通用 `complete()` 方法。**
现有 `LLMGateway` 只有特定方法（`parse_jd`/`generate_embedding`），无通用 chat 接口。v2 需要把 HTML 喂给 LLM 做通用解析。最优方案：在 `LLMGateway` 加 `async def complete(messages, temperature=0.1, json_mode=False) -> str`，复用 `self.client.chat.completions.create`（参照 `parse_jd` 第 197 行的写法）+ `with_retry`/`with_timeout`。理由：(1) 复用既有 OpenAI 客户端+代理+重试；(2) 不违反 HTTP 铁律；(3) 给网关加通用方法是合理扩展。

---

## File Structure

新建文件（v2 域代码）：

| 文件 | 职责 |
|------|------|
| `backend/app/domains/lab_web/constants/site_role_mapping.py` | role_section → RoleType 映射规则 |
| `backend/app/domains/lab_web/models/lab_web_site.py` | `LWSiteConfig`, `LWSiteRawPage` ORM |
| `backend/app/domains/lab_web/schemas/lab_web_site.py` | `ParsedPerson`, DTO |
| `backend/app/domains/lab_web/repositories/lab_web/site.py` | `LWSiteRepository` |
| `backend/app/domains/lab_web/services/lw_site_person_service.py` | raw → core_talent 同步（source_type=lab_web_site） |
| `backend/app/domains/lab_web/services/lw_site_collection_service.py` | 编排 |
| `backend/app/domains/lab_web/services/collectors/base_site_collector.py` | `BaseLabSiteCollector`（LLM 管线） |
| `backend/app/domains/lab_web/services/collectors/llm_parser.py` | LLM 调用 + 提示词 + schema 校验 |
| `backend/app/domains/lab_web/services/collectors/html_preprocessor.py` | HTML 预处理（去 script/style、压缩） |
| `backend/app/domains/lab_web/api/site_collection.py` | 5 个 endpoint |

修改既有文件：

| 文件 | 改动 |
|------|------|
| `backend/app/domains/shared/models/enums.py` | `SourceType` 加 `LAB_WEB_SITE` |
| `backend/app/domains/shared/services/llm/llm_gateway.py` | 加 `complete()` 通用方法 |
| `backend/app/model_registry.py` | 注册 `LWSiteConfig`, `LWSiteRawPage` |
| `backend/app/api_router.py` | 注册 site_collection router |
| `backend/migrations/versions/051_add_lab_web_site.py` | 两张新表 + 种子 |

测试文件：

| 文件 | 内容 |
|------|------|
| `tests/domains/lab_web/test_site_role_mapping.py` | role 映射单测 |
| `tests/domains/lab_web/test_html_preprocessor.py` | HTML 预处理单测 |
| `tests/domains/lab_web/test_llm_parser.py` | LLM 解析+校验单测（mock LLM） |
| `tests/domains/lab_web/test_site_repository.py` | Repository 集成测试 |
| `tests/domains/lab_web/test_site_person_service.py` | 同步服务集成测试（mock LLM） |
| `tests/domains/lab_web/test_base_site_collector.py` | 基类主流程单测（mock 全程） |
| `tests/domains/lab_web/test_site_collection_service.py` | 编排服务单测 |
| `tests/domains/lab_web/test_llm_gateway_complete.py` | LLMGateway.complete 单测（mock openai client） |

---

## Task 1: 枚举扩展 + LLMGateway.complete 方法

**Files:**
- Modify: `backend/app/domains/shared/models/enums.py`
- Modify: `backend/app/domains/shared/services/llm/llm_gateway.py`
- Test: `backend/tests/domains/lab_web/test_llm_gateway_complete.py`

- [ ] **Step 1: 在 SourceType 加 LAB_WEB_SITE**

Modify `backend/app/domains/shared/models/enums.py`，`SourceType` 加一行：

```python
class SourceType(str, enum.Enum):
    """Data source type enumeration."""

    OPENALEX = "openalex"
    MANUAL = "manual"
    IMPORT = "import"
    LAB_WEB = "lab_web"
    LAB_WEB_SITE = "lab_web_site"
```

- [ ] **Step 2: 写 LLMGateway.complete 的失败测试**

Create `backend/tests/domains/lab_web/test_llm_gateway_complete.py`:

```python
"""Tests for LLMGateway.complete (the generic chat method added for v2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.shared.services.llm.llm_gateway import LLMGateway

pytestmark = pytest.mark.unit


def _make_gateway_with_mock_client(response_content: str) -> tuple[LLMGateway, MagicMock]:
    """Build a gateway whose OpenAI client is mocked to return response_content."""
    gw = LLMGateway(
        api_key="test-key",
        api_base="https://api.test.example",
        model="test-model",
        api_format="openai",
    )
    mock_choice = MagicMock()
    mock_choice.message.content = response_content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    gw.client = MagicMock()
    gw.client.chat = MagicMock()
    gw.client.chat.completions = MagicMock()
    gw.client.chat.completions.create = AsyncMock(return_value=mock_response)
    return gw, mock_response


async def test_complete_returns_content_string():
    gw, _ = _make_gateway_with_mock_client('{"name": "Alice"}')
    messages = [{"role": "user", "content": "hi"}]
    result = await gw.complete(messages)
    assert result.content == '{"name": "Alice"}'


async def test_complete_passes_temperature_and_json_mode():
    gw, mock_response = _make_gateway_with_mock_client("{}")
    messages = [{"role": "user", "content": "hi"}]
    await gw.complete(messages, temperature=0.2, json_mode=True)
    # Verify create was called with the right params
    gw.client.chat.completions.create.assert_awaited_once()
    call_kwargs = gw.client.chat.completions.create.await_args.kwargs
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs.get("response_format") == {"type": "json_object"}


async def test_complete_returns_token_usage():
    gw, mock_response = _make_gateway_with_mock_client("{}")
    result = await gw.complete([{"role": "user", "content": "hi"}])
    assert result.tokens_used == 30


async def test_complete_raises_on_empty_response():
    gw, _ = _make_gateway_with_mock_client("")
    with pytest.raises(Exception):
        await gw.complete([{"role": "user", "content": "hi"}])
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_llm_gateway_complete.py -v`
Expected: FAIL with `AttributeError: 'LLMGateway' object has no attribute 'complete'`

- [ ] **Step 4: 实现 LLMGateway.complete**

在 `backend/app/domains/shared/services/llm/llm_gateway.py`，在 `parse_jd` 方法之后（约第 276 行 `health_check` 之前）加入。先在文件顶部附近定义返回类型 dataclass（放在 import 之后、class LLMGateway 之前）：

```python
@dataclass
class CompletionResult:
    """Result of a generic LLM chat completion."""

    content: str
    tokens_used: int = 0
```

（需要 `from dataclasses import dataclass` import，加到文件顶部 import 区。）

然后在 `LLMGateway` 类内，`parse_jd` 之后加入：

```python
    @with_retry(max_retries=3)
    @with_timeout(timeout_seconds=60.0)
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        json_mode: bool = False,
    ) -> CompletionResult:
        """Generic chat completion. Returns the assistant content + token usage.

        Added for lab_web_site v2 (LLM-driven HTML parsing). Reuses the same
        OpenAI client + proxy + retry as parse_jd, but without JD-specific logic.
        """
        try:
            request_params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if self.api_format == "openai" and json_mode:
                request_params["response_format"] = {"type": "json_object"}
            response = await self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            if not content:
                raise LLMError(
                    error_type=LLMErrorType.INVALID_RESPONSE,
                    message="Empty response from LLM",
                )
            tokens = 0
            if response.usage and response.usage.total_tokens:
                tokens = response.usage.total_tokens
            return CompletionResult(content=content, tokens_used=tokens)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                error_type=LLMErrorType.API_ERROR, message=f"complete() failed: {exc}"
            ) from exc
```

（需要确认 `Any` 已 import；`LLMError`/`LLMErrorType` 已在本文件 import。）

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_llm_gateway_complete.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/domains/shared/models/enums.py app/domains/shared/services/llm/llm_gateway.py tests/domains/lab_web/test_llm_gateway_complete.py
git commit -m "feat(llm): add LLMGateway.complete() generic chat method + SourceType.LAB_WEB_SITE

Adds a generic complete(messages, temperature, json_mode) -> CompletionResult
to LLMGateway for lab_web_site v2's LLM-driven HTML parsing. Reuses the
existing OpenAI client + proxy + retry. Also adds SourceType.LAB_WEB_SITE
enum for the new data source."
```

---

## Task 2: site_role_mapping（TDD）

**Files:**
- Create: `backend/app/domains/lab_web/constants/site_role_mapping.py`
- Test: `backend/tests/domains/lab_web/test_site_role_mapping.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_site_role_mapping.py`:

```python
"""Tests for lab_web_site role_section -> role_type mapping."""
from app.domains.lab_web.constants.site_role_mapping import map_site_role
from app.domains.shared.models.enums import RoleType


class TestMapSiteRole:
    def test_faculty(self):
        assert map_site_role("Faculty") == (RoleType.PROFESSOR, 1.0)
        assert map_site_role("professors") == (RoleType.PROFESSOR, 1.0)

    def test_pi(self):
        assert map_site_role("Principal Investigator") == (RoleType.PROFESSOR, 1.0)

    def test_phd_students(self):
        assert map_site_role("PhD Students") == (RoleType.STUDENT, 1.0)
        assert map_site_role("Ph.D. Students") == (RoleType.STUDENT, 1.0)
        assert map_site_role("Graduate Students") == (RoleType.STUDENT, 1.0)

    def test_postdocs(self):
        assert map_site_role("Postdocs") == (RoleType.GRADUATE, 1.0)
        assert map_site_role("Postdoctoral Researchers") == (RoleType.GRADUATE, 1.0)

    def test_staff_research_scientist(self):
        assert map_site_role("Staff") == (RoleType.PROFESSOR, 0.9)
        assert map_site_role("Research Scientists") == (RoleType.PROFESSOR, 0.9)

    def test_alumni(self):
        assert map_site_role("Alumni") == (RoleType.UNKNOWN, 1.0)

    def test_visiting(self):
        assert map_site_role("Visiting Scholars") == (RoleType.UNKNOWN, 0.6)

    def test_none_returns_unknown_zero(self):
        assert map_site_role(None) == (RoleType.UNKNOWN, 0.0)

    def test_no_match_returns_unknown_zero(self):
        assert map_site_role("Some Random Section") == (RoleType.UNKNOWN, 0.0)

    def test_case_insensitive(self):
        assert map_site_role("FACULTY") == (RoleType.PROFESSOR, 1.0)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_role_mapping.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现**

Create `backend/app/domains/lab_web/constants/site_role_mapping.py`:

```python
"""Map lab-site role-section labels to the unified RoleType enumeration.

Lab-site People pages segment members into named sections (Faculty / PhD
Students / Postdocs / Staff / Alumni). These labels are authoritative (the
site explicitly declares the role), so confidence is high (1.0 for clear
matches). The original section label is preserved in extra_data.role_section_raw.
"""
from __future__ import annotations

from app.domains.shared.models.enums import RoleType

# Rules ordered by specificity; first match wins. Substring match on lowercased
# role_section. NOTE: postdoc rules MUST come before research-scientist/staff,
# because "Postdoctoral Researcher" contains "researcher".
# (keywords lowercased, role, confidence)
SITE_ROLE_RULES: list[tuple[list[str], RoleType, float]] = [
    (["faculty", "professor", "principal investigator"], RoleType.PROFESSOR, 1.0),
    (["postdoc", "postdoctoral", "post-doc"], RoleType.GRADUATE, 1.0),
    (["phd", "ph.d", "doctoral", "graduate student", "student"], RoleType.STUDENT, 1.0),
    (["research scientist", "research engineer", "staff scientist", "staff"], RoleType.PROFESSOR, 0.9),
    (["alumni", "alumnus", "alumna"], RoleType.UNKNOWN, 1.0),
    (["visiting"], RoleType.UNKNOWN, 0.6),
]


def map_site_role(role_section: str | None) -> tuple[RoleType, float]:
    """Map a lab-site role-section label to (RoleType, confidence).

    Returns (RoleType.UNKNOWN, 0.0) when the label is missing or no rule matches.
    Matching is case-insensitive substring matching.
    """
    if not role_section:
        return RoleType.UNKNOWN, 0.0
    text = role_section.lower()
    for keywords, role, confidence in SITE_ROLE_RULES:
        if any(keyword in text for keyword in keywords):
            return role, confidence
    return RoleType.UNKNOWN, 0.0
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_role_mapping.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/domains/lab_web/constants/site_role_mapping.py tests/domains/lab_web/test_site_role_mapping.py
git commit -m "feat(lab_web_site): add site role-section to RoleType mapping with tests"
```

---

## Task 3: HTML 预处理器（TDD）

**Files:**
- Create: `backend/app/domains/lab_web/services/collectors/html_preprocessor.py`
- Test: `backend/tests/domains/lab_web/test_html_preprocessor.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_html_preprocessor.py`:

```python
"""Tests for lab_web_site HTML preprocessor."""
from app.domains.lab_web.services.collectors.html_preprocessor import preprocess_html


class TestPreprocessHtml:
    def test_removes_script_and_style(self):
        html = "<html><body><style>.x{color:red}</style><script>alert(1)</script><p>Alice</p></body></html>"
        result = preprocess_html(html)
        assert "alert" not in result
        assert "color:red" not in result
        assert "Alice" in result

    def test_removes_nav_footer_header(self):
        html = "<body><nav>Menu</nav><main><p>Bob</p></main><footer>Copyright</footer></body>"
        result = preprocess_html(html)
        assert "Menu" not in result
        assert "Copyright" not in result
        assert "Bob" in result

    def test_collapses_whitespace(self):
        html = "<body><p>Alice\n\n\n   Smith</p></body>"
        result = preprocess_html(html)
        assert "Alice Smith" in result  # collapsed

    def test_truncates_when_too_long(self):
        html = "<body>" + ("Alice " * 20000) + "</body>"
        result = preprocess_html(html, max_chars=5000)
        assert len(result) <= 5100  # small buffer for truncation marker
        assert result.endswith("...[truncated]")

    def test_preserves_name_like_text(self):
        html = "<body><div class='team-member'><b>Carol Jones</b> Faculty</div></body>"
        result = preprocess_html(html)
        assert "Carol Jones" in result
        assert "Faculty" in result
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_html_preprocessor.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现**

Create `backend/app/domains/lab_web/services/collectors/html_preprocessor.py`:

```python
"""HTML preprocessing for lab_web_site LLM parsing.

Raw People-page HTML can be large (NLP Group ~184KB) with scripts/styles/nav
that bloat LLM tokens and distract parsing. This module strips noise, keeps
people-relevant structure, and caps size so the LLM gets a clean, focused input.
"""
from __future__ import annotations

import re

from scrapling.parser import Selector

_WHITESPACE = re.compile(r"\s+")
TRUNCATION_MARKER = "...[truncated]"


def preprocess_html(html: str, max_chars: int = 50000) -> str:
    """Strip noise from People-page HTML and cap size for LLM input.

    - Removes <script>, <style>, <nav>, <footer>, <header> nodes.
    - Extracts body text, collapsing whitespace.
    - Truncates to max_chars with a marker if still too long.
    """
    sel = Selector(html)
    # Drop noise nodes by selecting body and removing the unwanted subtrees.
    body_nodes = sel.css("body")
    root = body_nodes[0] if body_nodes else sel

    # scrapling Selector nodes support .drop_subtrees or similar; if not, fall
    # back to regex-based removal on the stringified node.
    text = str(root)
    for tag in ("script", "style", "nav", "footer", "header"):
        text = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", text, flags=re.DOTALL | re.IGNORECASE)

    # Strip remaining tags, keep text content.
    text = re.sub(r"<[^>]+>", " ", text)
    text = _WHITESPACE.sub(" ", text).strip()

    if len(text) > max_chars:
        text = text[:max_chars] + TRUNCATION_MARKER
    return text
```

> Note: The implementation uses regex on the stringified node as a robust fallback. If Scrapling's Selector exposes a cleaner `drop_subtrees`/`remove` API after verification in Step 3, prefer that. The tests are the contract.

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_html_preprocessor.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/domains/lab_web/services/collectors/html_preprocessor.py tests/domains/lab_web/test_html_preprocessor.py
git commit -m "feat(lab_web_site): add HTML preprocessor for LLM input"
```

---

## Task 4: ParsedPerson schema + llm_parser（TDD，mock LLM）

**Files:**
- Create: `backend/app/domains/lab_web/schemas/lab_web_site.py`
- Create: `backend/app/domains/lab_web/services/collectors/llm_parser.py`
- Test: `backend/tests/domains/lab_web/test_llm_parser.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_llm_parser.py`:

```python
"""Tests for llm_parser (LLM call + Pydantic schema validation). Mocks LLMGateway."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.lab_web.schemas.lab_web_site import ParsedPerson
from app.domains.lab_web.services.collectors.llm_parser import (
    ParseResult,
    parse_persons_from_html,
)

pytestmark = pytest.mark.unit


def _mock_gateway(content: str):
    gw = MagicMock()
    gw.complete = AsyncMock()
    gw.complete.return_value = MagicMock(content=content, tokens_used=42)
    return gw


SYSTEM_PROMPT = "test prompt"


async def test_parse_valid_json():
    gw = _mock_gateway(
        '[{"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example", "department": "CS"}]'
    )
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is True
    assert len(result.persons) == 1
    assert result.persons[0].name == "Alice Lee"
    assert result.persons[0].role_section == "PhD Students"
    assert result.tokens_used == 42


async def test_parse_empty_array_flagged():
    gw = _mock_gateway("[]")
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert "empty" in result.error.lower() or "0" in result.error


async def test_parse_invalid_json_flagged():
    gw = _mock_gateway("not json at all {")
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert result.error  # non-empty error message


async def test_parse_missing_name_flagged():
    gw = _mock_gateway('[{"role_section": "Faculty"}]')
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False  # name is required


async def test_parse_retries_once_then_fails():
    gw = MagicMock()
    gw.complete = AsyncMock(side_effect=Exception("LLM down"))
    result = await parse_persons_from_html(gw, "some html", SYSTEM_PROMPT)
    assert result.ok is False
    assert gw.complete.await_count == 2  # initial + 1 retry


class TestParsedPersonSchema:
    def test_valid(self):
        p = ParsedPerson(name="Bob", role_section="Faculty", homepage="https://b.example", department="EE")
        assert p.name == "Bob"

    def test_blank_name_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ParsedPerson(name="   ")

    def test_invalid_homepage_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ParsedPerson(name="Bob", homepage="not-a-url")

    def test_none_homepage_ok(self):
        p = ParsedPerson(name="Bob", homepage=None)
        assert p.homepage is None
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_llm_parser.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现 ParsedPerson schema**

Create `backend/app/domains/lab_web/schemas/lab_web_site.py`:

```python
"""Pydantic DTOs for lab_web_site (v2)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator
from urllib.parse import urlparse


class ParsedPerson(BaseModel):
    """One person extracted by the LLM from a lab-site People page."""

    name: str
    role_section: str = "Unknown"
    homepage: str | None = None
    department: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("homepage")
    @classmethod
    def valid_url_if_present(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"invalid homepage URL: {v}")
        return v


class SiteBrief(BaseModel):
    """Site config row for listing."""

    model_config = ConfigDict(from_attributes=True)

    site_id: int
    site_code: str
    site_name: str
    parent_lab_code: str
    people_url: str
    fetch_mode: str
    is_active: bool
    last_collected_at: str | None = None


class SiteCollectStartResponse(BaseModel):
    task_id: int
    status: str


class SiteCollectTaskResponse(BaseModel):
    """Reuses lw_collect_task; response fields are the same shape as v1."""

    model_config = ConfigDict(from_attributes=True)

    task_id: int
    task_name: str
    status: str
    progress_percent: int
    current_step: str | None = None
    total_records: int
    error_message: str | None = None
```

- [ ] **Step 4: 实现 llm_parser**

Create `backend/app/domains/lab_web/services/collectors/llm_parser.py`:

```python
"""LLM call + Pydantic schema validation for lab-site People-page parsing."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError, TypeAdapter

from app.domains.lab_web.schemas.lab_web_site import ParsedPerson

logger = logging.getLogger(__name__)

_persons_adapter: TypeAdapter[list[ParsedPerson]] = TypeAdapter(list[ParsedPerson])


@dataclass
class ParseResult:
    """Outcome of one LLM parse attempt (after retries)."""

    ok: bool
    persons: list[ParsedPerson] | None = None
    error: str = ""
    tokens_used: int = 0


async def parse_persons_from_html(
    llm_gateway,
    html: str,
    system_prompt: str,
) -> ParseResult:
    """Call the LLM, validate output against ParsedPerson schema, retry once.

    Returns ParseResult(ok=False) on schema failure after one retry, or when the
    LLM returns zero persons (a People page should have people).
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": html},
    ]
    last_error = ""
    for attempt in range(2):  # initial + 1 retry
        try:
            result = await llm_gateway.complete(messages, temperature=0.1, json_mode=False)
            content = result.content.strip()
            # Tolerate markdown code fences around JSON.
            if content.startswith("```"):
                content = content.strip("`")
                if content.lower().startswith("json"):
                    content = content[4:]
            persons = _persons_adapter.validate_json(content)
            if not persons:
                return ParseResult(ok=False, error="LLM returned 0 persons (empty array)", tokens_used=result.tokens_used)
            return ParseResult(ok=True, persons=persons, tokens_used=result.tokens_used)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = f"schema/parse error: {exc}"
            logger.warning("LLM parse attempt %d failed: %s", attempt + 1, last_error)
        except Exception as exc:
            last_error = f"LLM call error: {exc}"
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, last_error)
    return ParseResult(ok=False, error=last_error)
```

- [ ] **Step 5: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_llm_parser.py -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/domains/lab_web/schemas/lab_web_site.py app/domains/lab_web/services/collectors/llm_parser.py tests/domains/lab_web/test_llm_parser.py
git commit -m "feat(lab_web_site): add ParsedPerson schema + llm_parser with retry/validation"
```

---

## Task 5: ORM 模型 + 迁移 + model_registry 注册

**Files:**
- Create: `backend/app/domains/lab_web/models/lab_web_site.py`
- Modify: `backend/app/domains/lab_web/models/__init__.py`
- Modify: `backend/app/model_registry.py`
- Create: `backend/migrations/versions/051_add_lab_web_site.py`

- [ ] **Step 1: 实现 ORM 模型**

Create `backend/app/domains/lab_web/models/lab_web_site.py`:

```python
"""lab_web_site domain ORM models (v2): site config + raw page snapshots."""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class LWSiteConfig(Base, TimestampMixin):
    """Registry of lab sites whose People pages we LLM-parse."""

    __tablename__ = "lw_site_config"

    site_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_code = Column(String(50), nullable=False, unique=True, index=True)
    site_name = Column(String(255), nullable=False)
    parent_lab_code = Column(String(50), nullable=False, index=True)
    people_url = Column(String(500), nullable=False)
    fetch_mode = Column(String(20), nullable=False, default="static")
    is_active = Column(Boolean, nullable=False, default=True)
    last_collected_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<LWSiteConfig(site_id={self.site_id}, site_code={self.site_code})>"


class LWSiteRawPage(Base):
    """Append-only snapshot of a site People page + LLM parse result (cached by html_hash)."""

    __tablename__ = "lw_site_raw_page"

    page_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_code = Column(String(50), nullable=False, index=True)
    people_url = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    html_hash = Column(String(64), nullable=False, index=True)
    parsed_persons = Column(JSON, nullable=True)
    parse_status = Column(String(20), nullable=False, default="pending", index=True)
    parse_error = Column(Text, nullable=True)
    llm_model = Column(String(100), nullable=True)
    llm_tokens_used = Column(Integer, nullable=True)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)
    parsed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LWSiteRawPage(page_id={self.page_id}, site_code={self.site_code}, status={self.parse_status})>"
```

- [ ] **Step 2: 更新 models/__init__.py**

Modify `backend/app/domains/lab_web/models/__init__.py` 追加 v2 模型导出：

```python
"""lab_web ORM models."""
from app.domains.lab_web.models.lab_web import (
    LWCollectTask,
    LWLabRegistry,
    LWRawPerson,
)
from app.domains.lab_web.models.lab_web_site import (
    LWSiteConfig,
    LWSiteRawPage,
)

__all__ = [
    "LWLabRegistry",
    "LWRawPerson",
    "LWCollectTask",
    "LWSiteConfig",
    "LWSiteRawPage",
]
```

- [ ] **Step 3: 注册到 model_registry.py**

Modify `backend/app/model_registry.py`：
- 在 lab_web import 块追加 `LWSiteConfig, LWSiteRawPage`：

```python
from app.domains.lab_web.models.lab_web import (
    LWCollectTask,
    LWLabRegistry,
    LWRawPerson,
)
from app.domains.lab_web.models.lab_web_site import (
    LWSiteConfig,
    LWSiteRawPage,
)
```

- 在 `__all__` 的 lab_web 区块追加：

```python
    # lab_web (v2.x)
    "LWSiteConfig",
    "LWSiteRawPage",
```

- [ ] **Step 4: 创建迁移**

Create `backend/migrations/versions/051_add_lab_web_site.py`:

```python
"""add_lab_web_site

Revision ID: 051_add_lab_web_site
Revises: 050_add_lab_web_domain
Create Date: 2026-06-29 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "051_add_lab_web_site"
down_revision: Union[str, None] = "050_add_lab_web_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lw_site_config",
        sa.Column("site_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_code", sa.String(length=50), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("parent_lab_code", sa.String(length=50), nullable=False),
        sa.Column("people_url", sa.String(length=500), nullable=False),
        sa.Column("fetch_mode", sa.String(length=20), nullable=False, server_default="static"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_collected_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("site_id"),
        sa.UniqueConstraint("site_code", name="uq_lw_site_config_site_code"),
    )
    op.create_index("ix_lw_site_config_site_code", "lw_site_config", ["site_code"])
    op.create_index("ix_lw_site_config_parent_lab_code", "lw_site_config", ["parent_lab_code"])

    op.create_table(
        "lw_site_raw_page",
        sa.Column("page_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_code", sa.String(length=50), nullable=False),
        sa.Column("people_url", sa.String(length=500), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("html_hash", sa.String(length=64), nullable=False),
        sa.Column("parsed_persons", sa.JSON(), nullable=True),
        sa.Column("parse_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["site_code"], ["lw_site_config.site_code"]),
        sa.PrimaryKeyConstraint("page_id"),
    )
    op.create_index("ix_lw_site_raw_page_site_code", "lw_site_raw_page", ["site_code"])
    op.create_index("ix_lw_site_raw_page_html_hash", "lw_site_raw_page", ["html_hash"])
    op.create_index("ix_lw_site_raw_page_parse_status", "lw_site_raw_page", ["parse_status"])

    op.execute(
        """
        INSERT INTO lw_site_config (site_code, site_name, parent_lab_code, people_url, fetch_mode, is_active)
        VALUES
          ('stanford_nlp_group', 'Stanford NLP Group', 'stanford_sail', 'https://nlp.stanford.edu/people/', 'static', true),
          ('stanford_snap', 'SNAP Group', 'stanford_sail', 'http://snap.stanford.edu/people.html', 'static', true),
          ('stanford_ermon', 'Ermon Lab', 'stanford_sail', 'https://cs.stanford.edu/~ermon/website/people.html', 'static', true)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_lw_site_raw_page_parse_status", table_name="lw_site_raw_page")
    op.drop_index("ix_lw_site_raw_page_html_hash", table_name="lw_site_raw_page")
    op.drop_index("ix_lw_site_raw_page_site_code", table_name="lw_site_raw_page")
    op.drop_table("lw_site_raw_page")
    op.drop_index("ix_lw_site_config_parent_lab_code", table_name="lw_site_config")
    op.drop_index("ix_lw_site_config_site_code", table_name="lw_site_config")
    op.drop_table("lw_site_config")
```

- [ ] **Step 5: 应用迁移并验证**

Run:
```bash
cd backend && uv run alembic upgrade head
```
Expected: `Running upgrade 050_add_lab_web_domain -> 051_add_lab_web_site, add_lab_web_site`

Run:
```bash
cd backend && uv run python -c "
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
async def main():
    async with AsyncSessionLocal() as s:
        for t in ['lw_site_config','lw_site_raw_page']:
            r = await s.execute(text(f'SELECT count(*) FROM {t}'))
            print(t, r.scalar())
        r = await s.execute(text('SELECT site_code, people_url FROM lw_site_config ORDER BY site_code'))
        for row in r:
            print('seed:', row.site_code, '->', row.people_url)
asyncio.run(main())
"
```
Expected:
```
lw_site_config 3
lw_site_raw_page 0
seed: stanford_ermon -> https://cs.stanford.edu/~ermon/website/people.html
seed: stanford_nlp_group -> https://nlp.stanford.edu/people/
seed: stanford_snap -> http://snap.stanford.edu/people.html
```

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/domains/lab_web/models/lab_web_site.py app/domains/lab_web/models/__init__.py app/model_registry.py migrations/versions/051_add_lab_web_site.py
git commit -m "feat(lab_web_site): add LWSiteConfig + LWSiteRawPage models and migration with 3 seeded sites"
```

---

## Task 6: LWSiteRepository（TDD）

**Files:**
- Create: `backend/app/domains/lab_web/repositories/lab_web/site.py`
- Modify: `backend/app/domains/lab_web/repositories/lab_web/__init__.py`
- Test: `backend/tests/domains/lab_web/test_site_repository.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_site_repository.py`:

```python
"""Integration tests for LWSiteRepository (uses talent_db_test)."""
from __future__ import annotations

import pytest

from app.domains.lab_web.models.lab_web_site import LWSiteConfig
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def sample_site(test_session):
    site = LWSiteConfig(
        site_code="test_site",
        site_name="Test Site",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/people/",
        fetch_mode="static",
        is_active=True,
    )
    test_session.add(site)
    await test_session.commit()
    await test_session.refresh(site)
    return site


async def test_site_crud(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    fetched = await repo.get_site_by_code("test_site")
    assert fetched is not None
    assert fetched.site_id == sample_site.site_id

    sites = await repo.list_sites(only_active=True)
    assert any(s.site_code == "test_site" for s in sites)


async def test_find_cached_page_hit(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    # Insert a parsed page snapshot.
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parsed_persons=[{"name": "Alice"}],
        parse_status="parsed",
        llm_model="test-model",
        llm_tokens_used=10,
    )
    cached = await repo.find_cached_page("test_site", "hash123")
    assert cached is not None
    assert cached.parse_status == "parsed"
    assert cached.parsed_persons == [{"name": "Alice"}]


async def test_find_cached_page_miss_on_different_hash(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parsed_persons=[],
        parse_status="parsed",
    )
    assert await repo.find_cached_page("test_site", "different_hash") is None


async def test_find_cached_page_miss_on_non_parsed_status(test_session, sample_site):
    repo = LWSiteRepository(test_session)
    await repo.insert_raw_page(
        site_code="test_site",
        people_url="https://example.test/people/",
        html_content="<html>x</html>",
        html_hash="hash123",
        parse_status="needs_review",
    )
    # Same hash but not 'parsed' status -> cache miss (must reparse).
    assert await repo.find_cached_page("test_site", "hash123") is None


async def test_insert_raw_upserts_raw_persons(test_session, sample_site):
    """Repository converts parsed persons to lw_raw_person rows."""
    repo = LWSiteRepository(test_session)
    drafts = [
        {"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example"},
        {"name": "Bob", "role_section": "Faculty"},
    ]
    rows = await repo.upsert_site_raw_persons(
        site_code="test_site",
        parent_lab_code="stanford_sail",
        parsed_persons=drafts,
        task_id=1,
    )
    assert len(rows) == 2
    names = {r.name_raw for r in rows}
    assert names == {"Alice Lee", "Bob"}
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_repository.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现 Repository**

Create `backend/app/domains/lab_web/repositories/lab_web/site.py`:

```python
"""Data access layer for lab_web_site tables (v2)."""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.lab_web.constants.normalizers import normalize_name
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.models.lab_web_site import LWSiteConfig, LWSiteRawPage


class LWSiteRepository:
    """Read/write access to lw_site_config and lw_site_raw_page."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ===== Sites =====

    async def get_site_by_code(self, site_code: str) -> LWSiteConfig | None:
        stmt = select(LWSiteConfig).where(LWSiteConfig.site_code == site_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sites(self, only_active: bool = False) -> list[LWSiteConfig]:
        stmt = select(LWSiteConfig)
        if only_active:
            stmt = stmt.where(LWSiteConfig.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_site_collected_at(self, site_code: str, collected_at: Any) -> None:
        site = await self.get_site_by_code(site_code)
        if site:
            site.last_collected_at = collected_at
            await self.session.commit()

    # ===== Raw page cache =====

    async def find_cached_page(
        self, site_code: str, html_hash: str
    ) -> LWSiteRawPage | None:
        """Return a parsed cached page for (site_code, html_hash), or None.

        Cache hits ONLY when parse_status='parsed' (needs_review/failed/pending
        are cache misses and must be re-parsed).
        """
        stmt = select(LWSiteRawPage).where(
            LWSiteRawPage.site_code == site_code,
            LWSiteRawPage.html_hash == html_hash,
            LWSiteRawPage.parse_status == "parsed",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_raw_page(
        self,
        site_code: str,
        people_url: str,
        html_content: str,
        html_hash: str,
        parsed_persons: list[dict] | None = None,
        parse_status: str = "pending",
        parse_error: str | None = None,
        llm_model: str | None = None,
        llm_tokens_used: int | None = None,
    ) -> LWSiteRawPage:
        row = LWSiteRawPage(
            site_code=site_code,
            people_url=people_url,
            html_content=html_content,
            html_hash=html_hash,
            parsed_persons=parsed_persons,
            parse_status=parse_status,
            parse_error=parse_error,
            llm_model=llm_model,
            llm_tokens_used=llm_tokens_used,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    # ===== Raw persons =====

    async def upsert_site_raw_persons(
        self,
        site_code: str,
        parent_lab_code: str,
        parsed_persons: list[dict],
        task_id: int,
    ) -> list[LWRawPerson]:
        """Convert LLM-parsed persons to lw_raw_person rows.

        Dedups within this batch by content_hash. raw layer is append-only.
        """
        seen: set[str] = set()
        created: list[LWRawPerson] = []
        for p in parsed_persons:
            name = normalize_name(p.get("name")) or p.get("name")
            role_section = p.get("role_section") or "Unknown"
            homepage = p.get("homepage")
            department = p.get("department")
            hash_ = hashlib.sha256(
                f"{site_code}|{name}|{role_section}|{homepage or ''}".encode("utf-8")
            ).hexdigest()
            if hash_ in seen:
                continue
            seen.add(hash_)
            row = LWRawPerson(
                lab_id=0,  # v2 doesn't map to lw_lab_registry.lab_id; site tracked in raw_data
                source_url=None,
                name_raw=p.get("name"),
                title_raw=None,  # lab-site has role_section, not a job title
                email_raw=None,
                homepage_url=homepage,
                avatar_url=None,
                raw_data={
                    "site_code": site_code,
                    "parent_lab_code": parent_lab_code,
                    "role_section": role_section,
                    "department": department,
                    "homepage": homepage,
                    "source_type": "lab_web_site",
                },
                collect_task_id=task_id,
                content_hash=hash_,
            )
            self.session.add(row)
            created.append(row)
        await self.session.commit()
        return created

    async def get_raw_persons_by_task(self, task_id: int) -> list[LWRawPerson]:
        stmt = select(LWRawPerson).where(LWRawPerson.collect_task_id == task_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

> Note on `lab_id=0`: v2 reuses `lw_raw_person` but doesn't map to `lw_lab_registry`. The FK `lw_raw_person.lab_id -> lw_lab_registry.lab_id` exists, so `lab_id=0` would violate it. **This must be resolved before running tests.** Two options:
> 1. Make `lw_raw_person.lab_id` nullable + drop FK (migration change) — touches v1 table, risky.
> 2. Resolve `lab_id` to the real `lw_lab_registry.lab_id` for `parent_lab_code` (e.g. stanford_sail -> its lab_id) at runtime.
>
> **Decision (autonomous): Option 2** — look up the parent lab's lab_id from lw_lab_registry by parent_lab_code and use it. Avoids touching v1 schema. The implementer must add a `get_lab_id_by_code` lookup in the repository and pass the real lab_id. Update Task 6 Step 3 implementation: replace `lab_id=0` with a lookup.

- [ ] **Step 4: 修正 lab_id（按上述自主决策，Option 2）**

在 `LWSiteRepository` 加一个 helper，并在 `upsert_site_raw_persons` 里用真实 lab_id：

在 `LWSiteRepository` 类内加：

```python
    async def _resolve_lab_id(self, parent_lab_code: str) -> int:
        """Resolve parent_lab_code -> lw_lab_registry.lab_id (for FK compliance)."""
        from app.domains.lab_web.models.lab_web import LWLabRegistry

        stmt = select(LWLabRegistry.lab_id).where(LWLabRegistry.lab_code == parent_lab_code)
        result = await self.session.execute(stmt)
        lab_id = result.scalar_one_or_none()
        if lab_id is None:
            raise ValueError(
                f"parent_lab_code {parent_lab_code!r} not found in lw_lab_registry; "
                "cannot insert lw_raw_person without a valid lab_id FK"
            )
        return int(lab_id)
```

并把 `upsert_site_raw_persons` 的 `lab_id=0` 改为：

```python
        lab_id = await self._resolve_lab_id(parent_lab_code)
        seen: set[str] = set()
        created: list[LWRawPerson] = []
        for p in parsed_persons:
            ...
                lab_id=lab_id,
```

- [ ] **Step 5: 更新 repositories __init__**

Modify `backend/app/domains/lab_web/repositories/lab_web/__init__.py`:

```python
"""LWRepository exports."""
from app.domains.lab_web.repositories.lab_web.core import LWRepository
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository

__all__ = ["LWRepository", "LWSiteRepository"]
```

- [ ] **Step 6: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_repository.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/domains/lab_web/repositories/lab_web/site.py app/domains/lab_web/repositories/lab_web/__init__.py tests/domains/lab_web/test_site_repository.py
git commit -m "feat(lab_web_site): add LWSiteRepository with cache lookup and raw-person conversion"
```

---

## Task 7: lw_site_person_service（raw → core_talent 同步，TDD）

**Files:**
- Create: `backend/app/domains/lab_web/services/lw_site_person_service.py`
- Test: `backend/tests/domains/lab_web/test_site_person_service.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_site_person_service.py`:

```python
"""Integration tests for LWSitePersonService (raw -> core_talent, source_type=lab_web_site)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService
from app.domains.shared.models.enums import RoleType, SourceType

pytestmark = pytest.mark.integration


async def _make_site_raw(
    lab_id: int, name: str, role_section: str, content_hash: str, **extra
):
    return LWRawPerson(
        lab_id=lab_id,
        name_raw=name,
        content_hash=content_hash,
        raw_data={
            "site_code": "test_site",
            "parent_lab_code": "stanford_sail",
            "role_section": role_section,
            "department": extra.get("department"),
            "homepage": extra.get("homepage"),
            "source_type": "lab_web_site",
        },
    )


async def test_sync_creates_core_talent_with_role(test_session, sample_lab):
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice Lee", "PhD Students", "sh1")
    result = await svc.sync_to_core_talent([raw])
    assert result.synced == 1
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1
    t = rows[0]
    assert t.name == "Alice Lee"
    assert t.source_type == SourceType.LAB_WEB_SITE.value
    assert t.role_type == RoleType.STUDENT.value
    assert t.role_confidence == 1.0
    assert t.extra_data["role_section_raw"] == "PhD Students"


async def test_sync_upsert_no_duplicate(test_session, sample_lab):
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice", "Faculty", "sh1")
    await svc.sync_to_core_talent([raw])
    raw2 = await _make_site_raw(
        sample_lab.lab_id, "Alice", "Faculty", "sh1", homepage="https://new.example"
    )
    await svc.sync_to_core_talent([raw2])
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 1  # upsert, not insert
    assert rows[0].extra_data.get("homepage") == "https://new.example"


async def test_sync_isolates_from_v1_and_openalex(test_session, sample_lab):
    existing = Talent(
        name="Other",
        source_type=SourceType.OPENALEX.value,
        source_record_id="oa-1",
        role_type=RoleType.UNKNOWN.value,
        is_visible=True,
    )
    test_session.add(existing)
    await test_session.commit()
    svc = LWSitePersonService(test_session)
    raw = await _make_site_raw(sample_lab.lab_id, "Alice", "Faculty", "site-sh1")
    await svc.sync_to_core_talent([raw])
    rows = (await test_session.execute(select(Talent))).scalars().all()
    assert len(rows) == 2
    oa = [r for r in rows if r.source_type == SourceType.OPENALEX.value][0]
    assert oa.name == "Other"  # untouched
    site = [r for r in rows if r.source_type == SourceType.LAB_WEB_SITE.value][0]
    assert site.name == "Alice"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_person_service.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现**

Create `backend/app/domains/lab_web/services/lw_site_person_service.py`:

```python
"""Sync lab_web_site raw persons into core_talent (source_type=lab_web_site).

Upserts by source_record_id (= content_hash) scoped to source_type='lab_web_site'.
Never touches v1 (lab_web) or openalex records. Role from the site's role_section.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.academic.models.talent import Talent
from app.domains.lab_web.constants.normalizers import normalize_name
from app.domains.lab_web.constants.site_role_mapping import map_site_role
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.shared.models.enums import SourceType, VisibilityStatus

logger = logging.getLogger(__name__)


@dataclass
class SiteSyncResult:
    synced: int = 0
    created: int = 0
    updated: int = 0


class LWSitePersonService:
    """Sync lab_web_site raw persons into core_talent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_to_core_talent(self, raw_persons: list[LWRawPerson]) -> SiteSyncResult:
        result = SiteSyncResult()
        commit_batch = int(getattr(settings, "SYNC_COMMIT_BATCH_SIZE", 100))
        for i, raw in enumerate(raw_persons):
            raw_data = raw.raw_data or {}
            role_section = raw_data.get("role_section", "Unknown")
            role_type, confidence = map_site_role(role_section)
            name = normalize_name(raw.name_raw) or raw.name_raw
            homepage = raw_data.get("homepage")
            department = raw_data.get("department")
            site_code = raw_data.get("site_code", "")
            existing = await self._find_existing(str(raw.content_hash))
            extra = {
                "site_code": site_code,
                "role_section_raw": role_section,
                "department": department,
                "homepage": homepage,
                "source_url": raw.source_url,
            }
            if existing is None:
                self.session.add(
                    Talent(
                        name=name,  # type: ignore[arg-type]
                        source_type=SourceType.LAB_WEB_SITE.value,
                        source_record_id=str(raw.content_hash),
                        role_type=role_type.value,  # type: ignore[assignment]
                        role_confidence=confidence,  # type: ignore[assignment]
                        current_title=role_section,  # site role section as a displayable title
                        lab_name=site_code,
                        visibility_status=VisibilityStatus.ACTIVE.value,  # type: ignore[assignment]
                        is_visible=True,  # type: ignore[assignment]
                        extra_data=extra,  # type: ignore[assignment]
                    )
                )
                result.created += 1
            else:
                existing.name = name  # type: ignore[assignment]
                existing.role_type = role_type.value  # type: ignore[assignment]
                existing.role_confidence = confidence  # type: ignore[assignment]
                existing.current_title = role_section  # type: ignore[assignment]
                existing.lab_name = site_code  # type: ignore[assignment]
                existing.is_visible = True  # type: ignore[assignment]
                existing.extra_data = extra  # type: ignore[assignment]
                result.updated += 1
            result.synced += 1
            if (i + 1) % commit_batch == 0:
                await self.session.commit()
        await self.session.commit()
        return result

    async def _find_existing(self, content_hash: str) -> Talent | None:
        stmt = select(Talent).where(
            Talent.source_type == SourceType.LAB_WEB_SITE.value,
            Talent.source_record_id == content_hash,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_person_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/domains/lab_web/services/lw_site_person_service.py tests/domains/lab_web/test_site_person_service.py
git commit -m "feat(lab_web_site): add LWSitePersonService for raw->core_talent sync (source_type=lab_web_site)"
```

---

## Task 8: BaseLabSiteCollector + 系统提示词（TDD，mock 全程）

**Files:**
- Create: `backend/app/domains/lab_web/services/collectors/base_site_collector.py`
- Create: `backend/app/domains/lab_web/services/collectors/prompts.py`
- Test: `backend/tests/domains/lab_web/test_base_site_collector.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/domains/lab_web/test_base_site_collector.py`:

```python
"""Unit tests for BaseLabSiteCollector end-to-end (mock fetcher + mock LLM)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.domains.academic.models.talent import Talent
from app.domains.lab_web.models.lab_web import LWRawPerson
from app.domains.lab_web.models.lab_web_site import LWSiteConfig
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
from app.domains.lab_web.services.collectors.base_site_collector import (
    BaseLabSiteCollector,
    SiteCollectContext,
)
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService
from app.domains.shared.models.enums import SourceType

pytestmark = pytest.mark.integration


class _FakeFetcher:
    robots_disallows: set = set()

    def __init__(self, html: str) -> None:
        self.html = html

    async def is_allowed_by_robots(self, url: str) -> bool:
        return True

    async def fetch(self, url: str) -> str:
        return self.html


def _mock_llm_gateway(persons_json: str):
    gw = MagicMock()
    gw.complete = AsyncMock(return_value=MagicMock(content=persons_json, tokens_used=10))
    gw.model = "test-model"
    return gw


async def test_collect_writes_raw_and_syncs_core_talent(test_session, sample_lab):
    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="test_site",
        site_name="Test Site",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    task = await repo.session.execute(select(LWSiteConfig))  # ensure flushed
    await test_session.commit()

    fetcher = _FakeFetcher("<body><div>Faculty: Alice</div></body>")
    llm = _mock_llm_gateway(
        '[{"name": "Alice Lee", "role_section": "PhD Students", "homepage": "https://alice.example"}]'
    )
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    from app.domains.lab_web.models.lab_web import LWCollectTask

    t = LWCollectTask(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    test_session.add(t)
    await test_session.commit()
    ctx = SiteCollectContext(task_id=int(t.task_id), site_code="test_site")
    await collector.collect(ctx)

    # raw persons written
    raw = (await test_session.execute(select(LWRawPerson))).scalars().all()
    assert len(raw) == 1
    assert raw[0].name_raw == "Alice Lee"
    # core_talent written with lab_web_site source + STUDENT role
    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 1
    assert talents[0].name == "Alice Lee"


async def test_collect_uses_cache_on_html_hash_hit(test_session, sample_lab):
    """When a parsed cached page exists for the same html_hash, LLM is NOT called."""
    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="cache_site",
        site_name="Cache Site",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    await test_session.commit()

    import hashlib

    html = "<body>cached page</body>"
    html_hash = hashlib.sha256(html.encode()).hexdigest()
    # Pre-seed a cached parsed page.
    await repo.insert_raw_page(
        site_code="cache_site",
        people_url="https://example.test/people/",
        html_content=html,
        html_hash=html_hash,
        parsed_persons=[{"name": "Cached Person", "role_section": "Faculty"}],
        parse_status="parsed",
        llm_model="prev-model",
    )

    fetcher = _FakeFetcher(html)
    llm = _mock_llm_gateway('[{"name": "SHOULD NOT BE USED"}]')  # must not be called
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    from app.domains.lab_web.models.lab_web import LWCollectTask

    t = LWCollectTask(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    test_session.add(t)
    await test_session.commit()
    ctx = SiteCollectContext(task_id=int(t.task_id), site_code="cache_site")
    await collector.collect(ctx)

    llm.complete.assert_not_awaited()  # cache hit -> no LLM call
    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 1
    assert talents[0].name == "Cached Person"


async def test_collect_needs_review_on_empty_parse(test_session, sample_lab):
    """LLM returning 0 persons -> needs_review, no core_talent written."""
    repo = LWSiteRepository(test_session)
    person_service = LWSitePersonService(test_session)
    site = LWSiteConfig(
        site_code="empty_site",
        site_name="Empty Site",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/people/",
    )
    test_session.add(site)
    await test_session.commit()
    fetcher = _FakeFetcher("<body>nobody here</body>")
    llm = _mock_llm_gateway("[]")
    collector = BaseLabSiteCollector(
        fetcher=fetcher, site=site, repo=repo, person_service=person_service, llm_gateway=llm
    )
    from app.domains.lab_web.models.lab_web import LWCollectTask

    t = LWCollectTask(task_name="t1", lab_id=sample_lab.lab_id, status="running")
    test_session.add(t)
    await test_session.commit()
    ctx = SiteCollectContext(task_id=int(t.task_id), site_code="empty_site")
    await collector.collect(ctx)

    talents = (
        await test_session.execute(
            select(Talent).where(Talent.source_type == SourceType.LAB_WEB_SITE.value)
        )
    ).scalars().all()
    assert len(talents) == 0  # needs_review -> nothing synced
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_base_site_collector.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现 prompts**

Create `backend/app/domains/lab_web/services/collectors/prompts.py`:

```python
"""LLM system prompt for lab-site People-page parsing (v2)."""

SITE_PEOPLE_PARSE_PROMPT = """你是一个网页数据抽取助手。下面是一个大学实验室的 People 页面 HTML（已预处理，去除了脚本和样式）。
请抽取页面中的所有人员，按他们在页面中所属的角色分区分类。

要求：
1. 只抽取真实人员（跳过导航、页脚、装饰性文字）。
2. 每个人员必须有 name（姓名）。
3. role_section 是该人员在页面中所属分区的原始标签（如 "Faculty"、"PhD Students"、"Postdocs"、"Staff"、"Alumni"）；如果页面无分区，填 "Unknown"。
4. 尽可能提取 homepage（个人主页 URL）和 department（院系/专业，如有）。
5. 跳过已毕业/离校的 Alumni（除非分区明确标注 Alumni，则 role_section 填 "Alumni"）。

输出严格的 JSON 数组，不要任何额外文字或 markdown 代码块：
[
  {"name": "...", "role_section": "...", "homepage": "...", "department": "..."}
]"""
```

- [ ] **Step 4: 实现 BaseLabSiteCollector**

Create `backend/app/domains/lab_web/services/collectors/base_site_collector.py`:

```python
"""Abstract base collector for lab-site People pages (v2, LLM-driven).

Flow (collect()):
  1. preflight (site active, people_url)
  2. robots.txt guard
  3. fetch HTML (reuses v1 ScraplingFetcher)
  4. compute html_hash
  5. cache check: parsed page for (site_code, html_hash)?
     -> hit: reuse parsed_persons, skip to step 8
  6. preprocess HTML (strip script/style/nav, cap size)
  7. LLM parse + schema validation (retry once; needs_review on failure/empty)
  8. write lw_site_raw_page snapshot
  9. convert to lw_raw_person rows
  10. sync to core_talent (source_type=lab_web_site)

All steps fixed in the base class; sites are config-driven (no subclasses).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.domains.lab_web.services.collectors.html_preprocessor import preprocess_html
from app.domains.lab_web.services.collectors.llm_parser import parse_persons_from_html
from app.domains.lab_web.services.collectors.prompts import SITE_PEOPLE_PARSE_PROMPT

if TYPE_CHECKING:
    from app.domains.lab_web.models.lab_web_site import LWSiteConfig
    from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
    from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
    from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService

logger = logging.getLogger(__name__)


@dataclass
class SiteCollectContext:
    task_id: int
    site_code: str
    force_reparse: bool = False
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)


class BaseLabSiteCollector:
    """LLM-driven collector for a lab-site People page. Config-driven, no subclasses."""

    def __init__(
        self,
        fetcher: "ScraplingFetcher",
        site: "LWSiteConfig",
        repo: "LWSiteRepository",
        person_service: "LWSitePersonService",
        llm_gateway: Any,
    ) -> None:
        self.fetcher = fetcher
        self.site = site
        self.repo = repo
        self.person_service = person_service
        self.llm_gateway = llm_gateway

    async def collect(self, ctx: SiteCollectContext) -> None:
        """Fixed main flow."""
        await self._preflight()
        await self._guard_robots_txt()
        html = await self.fetcher.fetch(str(self.site.people_url))
        if hasattr(html, "html"):
            html = html.html  # tolerate a response wrapper
        html_str = str(html)
        html_hash = hashlib.sha256(html_str.encode("utf-8")).hexdigest()

        # Step 5: cache check
        parsed_persons: list[dict] | None = None
        if not ctx.force_reparse:
            cached = await self.repo.find_cached_page(self.site.site_code, html_hash)
            if cached is not None and cached.parsed_persons:
                parsed_persons = cached.parsed_persons
                logger.info(
                    "lab_web_site cache hit: site=%s hash=%s -> %d persons (no LLM call)",
                    self.site.site_code, html_hash, len(parsed_persons),
                )

        # Step 6+7: parse if not cached
        parse_status = "parsed"
        parse_error: str | None = None
        llm_model: str | None = None
        llm_tokens: int | None = None
        if parsed_persons is None:
            cleaned = preprocess_html(html_str)
            result = await parse_persons_from_html(self.llm_gateway, cleaned, SITE_PEOPLE_PARSE_PROMPT)
            llm_tokens = result.tokens_used
            llm_model = getattr(self.llm_gateway, "model", None)
            if not result.ok or not result.persons:
                parse_status = "needs_review"
                parse_error = result.error or "unknown parse failure"
                logger.warning(
                    "lab_web_site parse needs_review: site=%s err=%s",
                    self.site.site_code, parse_error,
                )
                parsed_persons = None
            else:
                parsed_persons = [p.model_dump() for p in result.persons]

        # Step 8: write raw page snapshot
        await self.repo.insert_raw_page(
            site_code=self.site.site_code,
            people_url=str(self.site.people_url),
            html_content=html_str,
            html_hash=html_hash,
            parsed_persons=parsed_persons,
            parse_status=parse_status,
            parse_error=parse_error,
            llm_model=llm_model,
            llm_tokens_used=llm_tokens,
        )

        # Step 9+10: if parsed, write raw persons + sync core_talent
        if parse_status == "parsed" and parsed_persons:
            raw_rows = await self.repo.upsert_site_raw_persons(
                site_code=self.site.site_code,
                parent_lab_code=str(self.site.parent_lab_code),
                parsed_persons=parsed_persons,
                task_id=ctx.task_id,
            )
            sync_result = await self.person_service.sync_to_core_talent(raw_rows)
            logger.info(
                "lab_web_site collect done: site=%s raw=%d synced=%d",
                self.site.site_code, len(raw_rows), sync_result.synced,
            )
        else:
            logger.info("lab_web_site collect done: site=%s (needs_review, nothing synced)", self.site.site_code)

    async def _preflight(self) -> None:
        if not self.site.is_active:
            raise RuntimeError(f"Site {self.site.site_code} is not active")

    async def _guard_robots_txt(self) -> None:
        allowed = await self.fetcher.is_allowed_by_robots(str(self.site.people_url))
        if not allowed:
            raise PermissionError(
                f"people_url {self.site.people_url} disallowed by robots.txt"
            )
```

- [ ] **Step 5: 运行确认通过**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_base_site_collector.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/domains/lab_web/services/collectors/base_site_collector.py app/domains/lab_web/services/collectors/prompts.py tests/domains/lab_web/test_base_site_collector.py
git commit -m "feat(lab_web_site): add BaseLabSiteCollector LLM pipeline + parse prompt"
```

---

## Task 9: 编排服务 + API（TDD）

**Files:**
- Create: `backend/app/domains/lab_web/services/lw_site_collection_service.py`
- Create: `backend/app/domains/lab_web/api/site_collection.py`
- Modify: `backend/app/api_router.py`
- Test: `backend/tests/domains/lab_web/test_site_collection_service.py`

- [ ] **Step 1: 写编排服务失败测试**

Create `backend/tests/domains/lab_web/test_site_collection_service.py`:

```python
"""Unit tests for LWSiteCollectionService orchestration (no real network/LLM)."""
from __future__ import annotations

import pytest

from app.domains.lab_web.services.lw_site_collection_service import (
    LWSiteCollectionService,
)

pytestmark = pytest.mark.unit


async def test_start_collection_unknown_site(test_session):
    svc = LWSiteCollectionService(test_session)
    with pytest.raises(LookupError):
        await svc.start_collection("nonexistent_site")


async def test_start_collection_inactive_site(test_session):
    from app.domains.lab_web.models.lab_web_site import LWSiteConfig

    site = LWSiteConfig(
        site_code="inactive_site",
        site_name="Inactive",
        parent_lab_code="stanford_sail",
        people_url="https://example.test/",
        is_active=False,
    )
    test_session.add(site)
    await test_session.commit()
    svc = LWSiteCollectionService(test_session)
    with pytest.raises(RuntimeError):
        await svc.start_collection("inactive_site")
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && uv run pytest tests/domains/lab_web/test_site_collection_service.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 实现编排服务**

Create `backend/app/domains/lab_web/services/lw_site_collection_service.py`:

```python
"""Collection orchestration for lab_web_site (v2, LLM-driven)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domains.lab_web.repositories.lab_web import LWRepository
from app.domains.lab_web.repositories.lab_web.site import LWSiteRepository
from app.domains.lab_web.services.collectors.base_site_collector import (
    BaseLabSiteCollector,
    SiteCollectContext,
)
from app.domains.lab_web.services.lw_site_person_service import LWSitePersonService

logger = logging.getLogger(__name__)

SITE_COLLECTION_SEMAPHORE = asyncio.Semaphore(
    int(getattr(settings, "LAB_WEB_SITE_MAX_CONCURRENT", 2))
)


class LWSiteCollectionService:
    """Orchestrates one lab-site LLM collection run end-to-end."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LWSiteRepository(session)
        self.task_repo = LWRepository(session)

    async def list_sites(self, only_active: bool = False):
        return await self.repo.list_sites(only_active=only_active)

    async def get_task_status(self, task_id: int):
        return await self.task_repo.get_task(task_id)

    async def cancel_collection(self, task_id: int) -> bool:
        await self.task_repo.update_task(task_id, status="cancelled")
        return True

    async def get_review_items(self, site_code: str):
        from sqlalchemy import select

        from app.domains.lab_web.models.lab_web_site import LWSiteRawPage

        stmt = (
            select(LWSiteRawPage)
            .where(
                LWSiteRawPage.site_code == site_code,
                LWSiteRawPage.parse_status == "needs_review",
            )
            .order_by(LWSiteRawPage.created_at.desc())
            .limit(20)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def start_collection(
        self,
        site_code: str,
        force_reparse: bool = False,
        created_by: int | None = None,
    ) -> int:
        """Create a task and launch background collection. Returns task_id."""
        site = await self.repo.get_site_by_code(site_code)
        if site is None:
            raise LookupError(f"Site {site_code} not found")
        if not site.is_active:
            raise RuntimeError(f"Site {site_code} is not active")

        # Resolve a lab_id for the FK on lw_collect_task.
        lab_id = await self.repo._resolve_lab_id(str(site.parent_lab_code))
        task = await self.task_repo.create_task(
            task_name=f"lab_web_site_collect_{site_code}",
            lab_id=lab_id,
            status="pending",
            config_json={
                "source": "lab_web_site",
                "site_code": site_code,
                "force_reparse": force_reparse,
            },
            created_by=created_by,
        )
        asyncio.create_task(
            self._run_collection(int(task.task_id), site_code, force_reparse)
        )
        return int(task.task_id)

    async def _run_collection(
        self, task_id: int, site_code: str, force_reparse: bool
    ) -> None:
        async with SITE_COLLECTION_SEMAPHORE:
            async with AsyncSessionLocal() as session:
                site_repo = LWSiteRepository(session)
                person_service = LWSitePersonService(session)
                task_repo = LWRepository(session)
                try:
                    site = await site_repo.get_site_by_code(site_code)
                    if site is None:
                        raise LookupError(f"Site {site_code} not found during run")
                    await task_repo.update_task(
                        task_id,
                        status="running",
                        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    collector = self._make_collector(site, site_repo, person_service)
                    ctx = SiteCollectContext(
                        task_id=task_id, site_code=site_code, force_reparse=force_reparse
                    )
                    await collector.collect(ctx)
                    # Determine final status: if parse produced data -> success,
                    # else needs_review -> partial.
                    from sqlalchemy import select

                    from app.domains.lab_web.models.lab_web_site import LWSiteRawPage

                    latest = (
                        await session.execute(
                            select(LWSiteRawPage)
                            .where(LWSiteRawPage.site_code == site_code)
                            .order_by(LWSiteRawPage.created_at.desc())
                            .limit(1)
                        )
                    ).scalar_one_or_none()
                    final_status = "success"
                    if latest is not None and latest.parse_status == "needs_review":
                        final_status = "partial"
                    await task_repo.update_task(
                        task_id,
                        status=final_status,
                        progress_percent=100,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    await site_repo.update_site_collected_at(
                        site_code,
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                except Exception as exc:
                    logger.exception("lab_web_site collection failed: task=%s", task_id)
                    msg = str(exc)
                    max_len = int(getattr(settings, "COLLECT_ERROR_MAX_LENGTH", 500))
                    await task_repo.update_task(
                        task_id,
                        status="failed",
                        error_message=(msg[:max_len] if len(msg) > max_len else msg),
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    )

    @staticmethod
    def _make_collector(site, site_repo, person_service) -> BaseLabSiteCollector:
        from app.domains.lab_web.services.collectors.scrapling_fetcher import ScraplingFetcher
        from app.domains.shared.services.llm.llm_gateway import create_llm_gateway

        fetcher = ScraplingFetcher(fetch_mode=str(getattr(site, "fetch_mode", "static")))
        llm_gateway = create_llm_gateway()
        return BaseLabSiteCollector(
            fetcher=fetcher,
            site=site,
            repo=site_repo,
            person_service=person_service,
            llm_gateway=llm_gateway,
        )
```

- [ ] **Step 4: 实现 API**

Create `backend/app/domains/lab_web/api/site_collection.py`:

```python
"""lab_web_site collection endpoints (site listing + task triggering/status)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab_web.schemas.lab_web_site import (
    SiteBrief,
    SiteCollectStartResponse,
    SiteCollectTaskResponse,
)
from app.domains.lab_web.services.lw_site_collection_service import (
    LWSiteCollectionService,
)
from app.domains.shared.schemas.common import SuccessResponse

router = APIRouter(prefix="/lab-web-sites", tags=["Lab Web Site Talent"])


@router.get("/sites", response_model=list[SiteBrief])
async def list_sites(
    only_active: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> list[SiteBrief]:
    """List registered lab sites."""
    service = LWSiteCollectionService(session)
    sites = await service.list_sites(only_active=only_active)
    return [SiteBrief.model_validate(s) for s in sites]


@router.post("/sites/{site_code}/collect", response_model=SiteCollectStartResponse)
async def collect_site(
    site_code: str,
    force_reparse: bool = Query(False),
    session: AsyncSession = Depends(get_async_session),
) -> SiteCollectStartResponse:
    """Start a background LLM collection for one site. Returns the task id."""
    service = LWSiteCollectionService(session)
    try:
        task_id = await service.start_collection(site_code, force_reparse=force_reparse)
    except LookupError:
        raise HTTPException(status_code=404, detail="Site not found") from None
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = await service.get_task_status(task_id)
    return SiteCollectStartResponse(task_id=task_id, status=str(task.status) if task else "pending")


@router.get("/tasks/{task_id}", response_model=SiteCollectTaskResponse)
async def get_site_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> SiteCollectTaskResponse:
    """Poll a site collection task's status."""
    service = LWSiteCollectionService(session)
    task = await service.get_task_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found") from None
    return SiteCollectTaskResponse.model_validate(task)


@router.post("/tasks/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_site_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> SuccessResponse:
    service = LWSiteCollectionService(session)
    await service.cancel_collection(task_id)
    return SuccessResponse(message="Task cancelled")


@router.get("/sites/{site_code}/review")
async def review_site(
    site_code: str,
    session: AsyncSession = Depends(get_async_session),
):
    """List needs_review parse results for manual inspection."""
    service = LWSiteCollectionService(session)
    items = await service.get_review_items(site_code)
    return [
        {
            "page_id": i.page_id,
            "parse_status": i.parse_status,
            "parse_error": i.parse_error,
            "fetched_at": i.fetched_at,
        }
        for i in items
    ]
```

> Note: there's a syntax error above (`: ` instead of `)`) on the `review_site` signature — fix to `session: AsyncSession = Depends(get_async_session),):` during implementation.

- [ ] **Step 5: 注册路由**

Modify `backend/app/api_router.py`，加 import + 注册（在 lab_web_collection 注册之后）：

```python
from app.domains.lab_web.api import collection as lab_web_collection
from app.domains.lab_web.api import site_collection as lab_web_site_collection
```

```python
# Lab Web Talent endpoints (v2.x)
api_router.include_router(lab_web_collection.router)

# Lab Web Site LLM endpoints (v2.x)
api_router.include_router(lab_web_site_collection.router)
```

- [ ] **Step 6: 运行确认通过 + 验证路由**

Run:
```bash
cd backend && uv run pytest tests/domains/lab_web/test_site_collection_service.py -v
cd backend && uv run python -c "
from app.api_router import api_router
print(sorted([r.path for r in api_router.routes if 'lab-web-sites' in r.path]))
"
```
Expected: test PASS (2 passed); routes list contains `/lab-web-sites/sites`, `/lab-web-sites/sites/{site_code}/collect`, `/lab-web-sites/tasks/{task_id}`, `/lab-web-sites/tasks/{task_id}/cancel`, `/lab-web-sites/sites/{site_code}/review`

- [ ] **Step 7: Commit**

```bash
cd backend
git add app/domains/lab_web/services/lw_site_collection_service.py app/domains/lab_web/api/site_collection.py app/api_router.py tests/domains/lab_web/test_site_collection_service.py
git commit -m "feat(lab_web_site): add LWSiteCollectionService orchestration + API endpoints"
```

---

## Task 10: 质量门禁收尾 + 完整回归

**Files:** 无新文件（收尾 + 修复）

- [ ] **Step 1: 跑全部 lab_web 测试（v1 + v2 回归）**

Run: `cd backend && uv run pytest tests/domains/lab_web/ -q`
Expected: all pass (v1 的 ~43 + v2 新增)

- [ ] **Step 2: lint + format**

Run:
```bash
cd backend
uv run ruff check app/domains/lab_web/ app/domains/shared/services/llm/llm_gateway.py --fix
uv run black app/domains/lab_web/ app/domains/shared/services/llm/llm_gateway.py
```
Expected: clean

- [ ] **Step 3: mypy gate**

Run: `cd backend && uv run python scripts/ops/mypy_gate.py`
Expected: PASS (no new errors vs baseline; lab_web_site 0 errors). 如有 lab_web_site 的类型错误，用 `cast()`/`# type: ignore[specific]` 修复（参照 v1 Task 13 的处理）。

- [ ] **Step 4: 架构检查**

Run: `cd backend && uv run python scripts/check_architecture.py`
Expected: 三项 PASSED（无新增 httpx/跨域/endpoint 违规）

- [ ] **Step 5: 修复发现的任何问题，再次全绿后提交**

```bash
cd backend
git add -A
git commit -m "chore(lab_web_site): pass full quality gate (ruff/black/mypy/architecture/tests)

All gates green: lab_web v1 + v2 tests pass, mypy gate PASS (0 new errors),
architecture check clean (no new httpx/cross-domain/endpoint violations)."
```

- [ ] **Step 6: 真实 LLM 手动验收（可选，需 LLM 配置 + 网络）**

> 需 `backend/.env` 配好 `LLM_*`（至少一个 provider 的 key）。标记 `slow`，不入 CI。

Run:
```bash
cd backend && uv run python -c "
import asyncio, app.model_registry  # noqa
from app.core.database import AsyncSessionLocal
from app.domains.lab_web.services.lw_site_collection_service import LWSiteCollectionService

async def main():
    async with AsyncSessionLocal() as s:
        svc = LWSiteCollectionService(s)
        task_id = await svc.start_collection('stanford_nlp_group')
        for _ in range(120):
            await asyncio.sleep(0.5)
            t = await svc.get_task_status(task_id)
            if str(t.status) in ('success','failed','partial','cancelled'):
                break
        print('status:', t.status, '| total:', t.total_records, '| err:', (t.error_message or '')[:200])

asyncio.run(main())
"
```
Expected: `status: success|partial, total: <N>`. 若 `partial`，查 `lw_site_raw_page.parse_status` 是否 needs_review，看 parse_error 调提示词。若 LLM 解析出人员，人工核对几条姓名/角色是否准确。

---

## 完工核对清单（对应 spec §9 验收标准）

- [ ] 1. `lw_site_config` + `lw_site_raw_page` 两表建出，预置 3 站点（Task 5）
- [ ] 2. `SourceType.LAB_WEB_SITE` 枚举 + 模型注册（Task 1 + Task 5）
- [ ] 3. `BaseLabSiteCollector` LLM 管线跑通（mock 测试，Task 8）
- [ ] 4. 缓存逻辑工作（Task 8 test_collect_uses_cache_on_html_hash_hit）
- [ ] 5. schema 校验拦截非法输出 + needs_review（Task 4 + Task 8）
- [ ] 6. 人员写入 core_talent（source_type=lab_web_site），role_type 映射（Task 7 + Task 8）
- [ ] 7. 跨源隔离（Task 7 test_sync_isolates_from_v1_and_openalex）
- [ ] 8. 手动验收真实 LLM 抓 NLP Group（Task 10 Step 6）
- [ ] 9. ruff + black + mypy gate + check_architecture 全绿（Task 10）
- [ ] 10. 不破坏 v1（Task 10 Step 1 全量回归）
