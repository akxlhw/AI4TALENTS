"""Tests for lab_web role mapping."""
from app.domains.lab_web.constants.role_mapping import map_role_type
from app.domains.shared.models.enums import RoleType


class TestMapRoleType:
    def test_professor_series(self):
        assert map_role_type("Assistant Professor") == (RoleType.PROFESSOR, 0.95)
        assert map_role_type("Associate Professor of CS") == (RoleType.PROFESSOR, 0.95)
        assert map_role_type("Full Professor") == (RoleType.PROFESSOR, 0.95)
        assert map_role_type("Lecturer") == (RoleType.PROFESSOR, 0.95)
        assert map_role_type("Faculty") == (RoleType.PROFESSOR, 0.95)

    def test_research_scientist(self):
        assert map_role_type("Research Scientist") == (RoleType.PROFESSOR, 0.85)
        assert map_role_type("Principal Investigator") == (RoleType.PROFESSOR, 0.85)
        assert map_role_type("Research Engineer") == (RoleType.PROFESSOR, 0.85)

    def test_postdoc_is_graduate(self):
        assert map_role_type("Postdoctoral Researcher") == (RoleType.GRADUATE, 0.9)
        assert map_role_type("Postdoc") == (RoleType.GRADUATE, 0.9)

    def test_student_series(self):
        assert map_role_type("PhD Candidate") == (RoleType.STUDENT, 0.95)
        assert map_role_type("Ph.D. Student") == (RoleType.STUDENT, 0.95)
        assert map_role_type("MS Student") == (RoleType.STUDENT, 0.95)
        assert map_role_type("Undergraduate Researcher") == (RoleType.STUDENT, 0.95)

    def test_visiting_is_unknown(self):
        assert map_role_type("Visiting Scholar") == (RoleType.UNKNOWN, 0.6)

    def test_none_returns_unknown_zero(self):
        assert map_role_type(None) == (RoleType.UNKNOWN, 0.0)

    def test_empty_string_returns_unknown_zero(self):
        assert map_role_type("") == (RoleType.UNKNOWN, 0.0)

    def test_no_match_returns_unknown_zero(self):
        assert map_role_type("Engineer") == (RoleType.UNKNOWN, 0.0)

    def test_case_insensitive(self):
        assert map_role_type("ASSISTANT PROFESSOR") == (RoleType.PROFESSOR, 0.95)
