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
        assert "Alice Smith" in result

    def test_truncates_when_too_long(self):
        html = "<body>" + ("Alice " * 20000) + "</body>"
        result = preprocess_html(html, max_chars=5000)
        assert len(result) <= 5100
        assert result.endswith("...[truncated]")

    def test_preserves_name_like_text(self):
        html = "<body><div class='team-member'><b>Carol Jones</b> Faculty</div></body>"
        result = preprocess_html(html)
        assert "Carol Jones" in result
        assert "Faculty" in result
