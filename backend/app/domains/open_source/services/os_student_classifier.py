"""开源开发者在校生识别分类器（纯函数）。

判定逻辑（已与产品确认）::

    is_student = bio_student OR (company_is_school AND NOT bio_staff)

- ``bio_student``：bio 命中学生关键词（student / undergraduate / phd candidate /
  研究生 / 在读 等，词边界、大小写不敏感）。
- ``bio_staff``（负向）：bio 命中教职工关键词（professor / faculty / postdoc /
  researcher / 教授 / 研究员 等）。
- ``company_is_school``：company 规范化后（去 ``@``、小写、标点转空格、压空白）满足任一：
  a) 词边界命中通用词 ``university`` 或 ``college``
     （刻意不使用 ``institute``，避免误伤 Alan Turing Institute 等研究所）；
  b) 命中学校词典（学术域导出的 ``constants/school_dict.json``）或手工缩写别名表
     （``constants/school_aliases.py``）。

词典缺失时自动降级为「通用词 + 手工别名」，不抛异常。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.domains.open_source.constants.school_aliases import MANUAL_SCHOOL_ALIASES

logger = logging.getLogger(__name__)

_SCHOOL_DICT_PATH = Path(__file__).resolve().parent.parent / "constants" / "school_dict.json"

# 学生关键词：拉丁词用词边界，中文词直接子串匹配
_STUDENT_RE = re.compile(
    r"\bstudents?\b|\bundergraduates?\b|\bundergrads?\b"
    r"|\bgraduate\s+students?\b|\bphd\s+students?\b|\bph\.?d\.?\s+candidates?\b"
    r"|\bmaster'?s?\s+students?\b|\bbachelors?\b"
    r"|研究生|本科生|在读|博士生|硕士生",
    re.IGNORECASE,
)

# 教职工（负向）关键词
_STAFF_RE = re.compile(
    r"\bprofessors?\b|\bfaculty\b|\bpostdocs?\b|\bpost-doctoral\b"
    r"|\bresearch\s+scientists?\b|\bresearchers?\b|\blecturers?\b|\bstaff\b"
    r"|教授|研究员|讲师",
    re.IGNORECASE,
)

# 通用学校词（注意：不含 institute）
_GENERIC_SCHOOL_RE = re.compile(r"\buniversity\b|\bcollege\b", re.IGNORECASE)

_NON_ALNUM_RE = re.compile(r"[^\w\s\u4e00-\u9fff]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_CJK_RE = re.compile(r"[一-鿿]")


@dataclass(frozen=True)
class ClassifyResult:
    """在校生判定结果。"""

    is_student: bool
    reason: str  # "bio_student" | "company_school" | "none"
    matched: str  # 命中的关键词/学校名（便于调试与统计）


def normalize_company(company: str | None) -> str:
    """规范化 company：去 @、小写、标点转空格、压空白。"""
    if not company:
        return ""
    text = company.lstrip("@").lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _contains_term(normalized_text: str, normalized_term: str) -> bool:
    """词典匹配：拉丁词用词边界（避免 "MIT" 命中 "submit"），中文词用子串。"""
    if not normalized_term:
        return False
    if _CJK_RE.search(normalized_term):
        return normalized_term in normalized_text
    pattern = r"\b" + re.escape(normalized_term) + r"\b"
    return re.search(pattern, normalized_text) is not None


@lru_cache(maxsize=1)
def _school_terms() -> tuple[str, ...]:
    """加载学校词典（names + aliases 键）并与手工别名合并，规范化后缓存。

    词典文件缺失或损坏时降级为仅手工别名，不抛异常。
    """
    terms: set[str] = set()
    if _SCHOOL_DICT_PATH.exists():
        try:
            data = json.loads(_SCHOOL_DICT_PATH.read_text(encoding="utf-8"))
            for name in data.get("names", []):
                terms.add(normalize_company(str(name)))
            for alias in data.get("aliases", {}):
                terms.add(normalize_company(str(alias)))
        except (json.JSONDecodeError, OSError) as exc:  # pragma: no cover - 防御性
            logger.warning("Failed to load school dict %s: %s", _SCHOOL_DICT_PATH, exc)
    else:
        logger.info(
            "School dict %s not found, falling back to generic words + manual aliases",
            _SCHOOL_DICT_PATH,
        )
    for alias in MANUAL_SCHOOL_ALIASES:
        terms.add(normalize_company(alias))
    terms.discard("")
    # 长词优先，避免短缩写抢占日志可读性（功能上无影响）
    return tuple(sorted(terms, key=len, reverse=True))


def _match_school(normalized_company: str) -> str:
    """返回命中的学校词（通用词或词典词），未命中返回空串。"""
    match = _GENERIC_SCHOOL_RE.search(normalized_company)
    if match:
        return match.group(0)
    for term in _school_terms():
        if _contains_term(normalized_company, term):
            return term
    return ""


def classify(
    company: str | None = None,
    bio: str | None = None,
    email: str | None = None,
) -> ClassifyResult:
    """判定开发者是否为在校生。

    Args:
        company: GitHub company 字段（可含 @ 前缀）。
        bio: GitHub bio 字段。
        email: GitHub email 字段（预留，当前判定逻辑不使用）。

    Returns:
        ClassifyResult(is_student, reason, matched)
    """
    bio_text = bio or ""

    staff_match = _STAFF_RE.search(bio_text)
    student_match = _STUDENT_RE.search(bio_text)
    if student_match:
        return ClassifyResult(True, "bio_student", student_match.group(0))

    normalized = normalize_company(company)
    if normalized:
        school_hit = _match_school(normalized)
        if school_hit and not staff_match:
            return ClassifyResult(True, "company_school", school_hit)

    return ClassifyResult(False, "none", "")


def has_staff_keyword(bio: str | None) -> bool:
    """bio 是否命中教职工（负向）关键词。"""
    if not bio:
        return False
    return _STAFF_RE.search(bio) is not None


def compute_is_student(
    company: str | None = None,
    bio: str | None = None,
    email: str | None = None,
) -> bool:
    """便捷入口：仅返回布尔结果（供 sync/backfill 使用）。"""
    return classify(company=company, bio=bio, email=email).is_student
