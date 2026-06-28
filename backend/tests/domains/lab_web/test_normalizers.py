"""Tests for lab_web normalizers."""
from app.domains.lab_web.constants.normalizers import (
    compute_content_hash,
    normalize_email,
    normalize_name,
)


class TestNormalizeEmail:
    def test_at_dot_obfuscation(self):
        assert normalize_email("john [at] cs [dot] stanford [dot] edu") == "john@cs.stanford.edu"

    def test_uppercase_obfuscation(self):
        assert normalize_email("john [AT] CS [DOT] STANFORD [DOT] EDU") == "john@cs.stanford.edu"

    def test_special_at_variant(self):
        assert normalize_email("john(ät)cs.stanford.edu") == "john@cs.stanford.edu"

    def test_standard_email_unchanged(self):
        assert normalize_email("john@cs.stanford.edu") == "john@cs.stanford.edu"

    def test_none_returns_none(self):
        assert normalize_email(None) is None

    def test_js_rendered_returns_none(self):
        # JS-obfuscated emails are not parsed in v1; raw string preserved by caller.
        assert normalize_email("<script>document.write('john'+'@'+'cs')</script>") is None

    def test_empty_returns_none(self):
        assert normalize_email("") is None
        assert normalize_email("   ") is None


class TestNormalizeName:
    def test_collapses_whitespace(self):
        assert normalize_name("John   Smith") == "John Smith"

    def test_strips_edges(self):
        assert normalize_name("  John Smith  ") == "John Smith"

    def test_preserves_case(self):
        assert normalize_name("McDonald O'Brien") == "McDonald O'Brien"

    def test_preserves_mixed_script(self):
        assert normalize_name("张伟 Wei Zhang") == "张伟 Wei Zhang"

    def test_none_returns_none(self):
        assert normalize_name(None) is None


class TestComputeContentHash:
    def test_stable_across_calls(self):
        h1 = compute_content_hash(
            lab_code="stanford_sail", name="John Smith", title="PhD",
            email="john@cs.stanford.edu", homepage="https://john.cs.stanford.edu",
        )
        h2 = compute_content_hash(
            lab_code="stanford_sail", name="John Smith", title="PhD",
            email="john@cs.stanford.edu", homepage="https://john.cs.stanford.edu",
        )
        assert h1 == h2
        assert len(h1) == 64  # sha256 hex

    def test_different_person_different_hash(self):
        h1 = compute_content_hash("stanford_sail", "John Smith", None, None, None)
        h2 = compute_content_hash("stanford_sail", "Jane Doe", None, None, None)
        assert h1 != h2

    def test_different_lab_different_hash(self):
        h1 = compute_content_hash("stanford_sail", "John Smith", None, None, None)
        h2 = compute_content_hash("mit_csail", "John Smith", None, None, None)
        assert h1 != h2

    def test_none_fields_do_not_break(self):
        h = compute_content_hash("stanford_sail", "John", None, None, None)
        assert len(h) == 64
