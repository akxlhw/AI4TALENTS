"""Role mapping: crawler role_section → (role_type, academic_level).

role_type is the coarse identity (reuses shared RoleType enum values).
academic_level is the fine-grain degree level for students (phd/master/bachelor).
The two are orthogonal dimensions — see docs/lab-talent-v1.0-design.md §3.1.
"""

from __future__ import annotations

import re

# Keyword groups (lowercased substrings to match against role_section).
# NOTE: postdoc is checked BEFORE phd because "Postdoctoral" contains
# "doctoral" — substring matching would otherwise misclassify postdocs as phd.
_PHD_KEYWORDS = ("phd", "博士")
# "doctoral" needs word-boundary matching to avoid matching "postdoctoral".
_DOCTORAL_RE = re.compile(r"\bdoctoral\b", re.IGNORECASE)
_MASTER_KEYWORDS = ("master", "硕士")
_BACHELOR_KEYWORDS = ("undergrad", "bachelor", "本科")
_STUDENT_GENERIC_KEYWORDS = ("student", "学生")
_FACULTY_KEYWORDS = ("faculty", "professor", "教授", "principal investigator")
_POSTDOC_KEYWORDS = ("postdoc", "post doctoral", "post-doctoral", "postdoctoral", "博后")
_STAFF_KEYWORDS = ("staff", "researcher", "research scientist", "研究员")
_ALUMNI_KEYWORDS = ("alumni", "former", "校友")


def map_role(role_section: str) -> tuple[str, str | None]:
    """Map a crawler role_section label to (role_type, academic_level).

    Returns:
        (role_type, academic_level) where academic_level is None for non-students.
        role_type is one of: professor / student / graduate / unknown
        academic_level is one of: phd / master / bachelor / None
    """
    if not role_section:
        return ("unknown", None)

    s = role_section.lower().strip()

    # Non-student roles checked FIRST — "Postdoctoral Researchers" must not
    # fall through to the "doctoral" → phd branch below.
    if any(k in s for k in _POSTDOC_KEYWORDS):
        return ("graduate", None)
    if any(k in s for k in _FACULTY_KEYWORDS):
        return ("professor", None)
    if any(k in s for k in _STAFF_KEYWORDS):
        return ("graduate", None)
    if any(k in s for k in _ALUMNI_KEYWORDS):
        return ("unknown", None)

    # Student degree levels (fine grain first, then generic student)
    if any(k in s for k in _PHD_KEYWORDS) or _DOCTORAL_RE.search(s):
        return ("student", "phd")
    if any(k in s for k in _MASTER_KEYWORDS):
        return ("student", "master")
    if any(k in s for k in _BACHELOR_KEYWORDS):
        return ("student", "bachelor")
    if any(k in s for k in _STUDENT_GENERIC_KEYWORDS):
        return ("student", None)

    return ("unknown", None)
