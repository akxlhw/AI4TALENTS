"""Map raw lab-page titles to the unified RoleType enumeration.

Lab People pages carry fine-grained titles (e.g. "Assistant Professor",
"PhD Candidate"). AI4TALENT's RoleType is a coarse four-value enum. We keep
the original title verbatim (title_raw / current_title) AND map it to a
RoleType plus a confidence score via substring matching.
"""
from __future__ import annotations

from app.domains.shared.models.enums import RoleType

# Rules ordered by specificity; first match wins.
# Student/postdoc rules MUST come before the bare "researcher" rule, because
# titles like "Postdoctoral Researcher" and "Undergraduate Researcher" contain
# "researcher" but are not independent research staff.
# (keywords lowercased, role, confidence)
ROLE_RULES: list[tuple[list[str], RoleType, float]] = [
    (["professor", "lecturer", "faculty"], RoleType.PROFESSOR, 0.95),
    # Students and postdocs (compound titles that contain "researcher").
    (["postdoc", "postdoctoral", "post-doc"], RoleType.GRADUATE, 0.9),
    (
        [
            "phd",
            "ph.d",
            "doctoral",
            "candidate",
            "master",
            "ms student",
            "m.s.",
            "meng",
            "undergraduate",
            "ugrad",
            "bachelor",
        ],
        RoleType.STUDENT,
        0.95,
    ),
    # Independent research staff (specific compounds only; bare "researcher"
    # is intentionally excluded to avoid matching the student/postdoc cases above).
    (
        [
            "research scientist",
            "research engineer",
            "staff scientist",
            "principal investigator",
            "pi",
        ],
        RoleType.PROFESSOR,
        0.85,
    ),
    (["visiting"], RoleType.UNKNOWN, 0.6),
]


def map_role_type(title_raw: str | None) -> tuple[RoleType, float]:
    """Map a raw lab-page title to (RoleType, confidence).

    Returns (RoleType.UNKNOWN, 0.0) when title is missing/empty or no rule
    matches. Matching is case-insensitive substring matching.
    """
    if not title_raw:
        return RoleType.UNKNOWN, 0.0
    text = title_raw.lower()
    for keywords, role, confidence in ROLE_RULES:
        if any(keyword in text for keyword in keywords):
            return role, confidence
    return RoleType.UNKNOWN, 0.0
