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
