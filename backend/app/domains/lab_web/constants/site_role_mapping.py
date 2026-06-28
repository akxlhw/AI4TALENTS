"""Map lab-site role-section labels to the unified RoleType enumeration.

Lab-site People pages segment members into named sections (Faculty / PhD
Students / Postdocs / Staff / Alumni). These labels are authoritative (the
site explicitly declares the role), so confidence is high (1.0 for clear
matches). The original section label is preserved in extra_data.role_section_raw.
"""

from __future__ import annotations

from app.domains.shared.models.enums import RoleType

# Rules ordered by specificity; first match wins. Substring match on lowercased
# role_section. NOTE: postdoc rules MUST come before research-scientist/staff.
# (keywords lowercased, role, confidence)
SITE_ROLE_RULES: list[tuple[list[str], RoleType, float]] = [
    (["faculty", "professor", "principal investigator"], RoleType.PROFESSOR, 1.0),
    (["postdoc", "postdoctoral", "post-doc"], RoleType.GRADUATE, 1.0),
    (["phd", "ph.d", "doctoral", "graduate student", "student"], RoleType.STUDENT, 1.0),
    (
        ["research scientist", "research engineer", "staff scientist", "staff"],
        RoleType.PROFESSOR,
        0.9,
    ),
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
