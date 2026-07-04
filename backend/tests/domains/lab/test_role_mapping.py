"""Tests for role_section → (role_type, academic_level) mapping."""

from __future__ import annotations

import pytest

from app.domains.lab.constants.role_mapping import map_role


class TestMapRole:
    """Verify role_section labels map to correct (role_type, academic_level)."""

    @pytest.mark.parametrize(
        "section,expected",
        [
            # Faculty / professor variants
            ("Faculty", ("professor", None)),
            ("Professors", ("professor", None)),
            ("Principal Investigators", ("professor", None)),
            ("教授", ("professor", None)),
            ("Director", ("professor", None)),  # lab director is professor-level
            # Postdocs → graduate
            ("Postdocs", ("graduate", None)),
            ("Postdoctoral Researchers", ("graduate", None)),
            ("博后", ("graduate", None)),
            # Staff / researchers → graduate
            ("Staff", ("graduate", None)),
            ("Research Scientists", ("graduate", None)),
            ("Researchers", ("graduate", None)),
            ("研究员", ("graduate", None)),
        ],
    )
    def test_non_student_roles(self, section, expected):
        assert map_role(section) == expected

    @pytest.mark.parametrize(
        "section,expected_level",
        [
            ("PhD Students", "phd"),
            ("Doctoral Students", "phd"),
            ("PhD Candidates", "phd"),
            ("博士生", "phd"),
            ("Master Students", "master"),
            ("Master's Students", "master"),
            ("Masters", "master"),
            ("硕士生", "master"),
            ("Undergrads", "bachelor"),
            ("Undergraduate Students", "bachelor"),
            ("Bachelor", "bachelor"),
            ("本科生", "bachelor"),
        ],
    )
    def test_student_degree_levels(self, section, expected_level):
        role_type, level = map_role(section)
        assert role_type == "student"
        assert level == expected_level

    def test_generic_student_without_degree(self):
        """A bare 'Students' label with no degree keyword → student, None level."""
        assert map_role("Students") == ("student", None)
        assert map_role("学生") == ("student", None)

    def test_graduate_student_is_not_phd(self):
        """'Graduate Student' does NOT specify degree level — must NOT be phd.

        Graduate student could be master or phd; the label alone is ambiguous,
        so academic_level must be None (not phd).
        """
        assert map_role("Graduate Student") == ("student", None)

    def test_alumni_maps_to_unknown(self):
        assert map_role("Alumni") == ("unknown", None)
        assert map_role("Former Members") == ("unknown", None)

    def test_unknown_section_falls_back(self):
        assert map_role("Visitors") == ("unknown", None)
        assert map_role("Random Label") == ("unknown", None)

    def test_empty_or_none(self):
        assert map_role("") == ("unknown", None)

    def test_case_insensitive(self):
        assert map_role("PHD STUDENTS") == ("student", "phd")
        assert map_role("FACULTY") == ("professor", None)

    def test_priority_phd_over_generic_student(self):
        """'PhD Students' must match phd before the generic 'student' keyword."""
        assert map_role("PhD Students") == ("student", "phd")
