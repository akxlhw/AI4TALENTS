"""Tests for crawl.py helper functions (JSONL writing, labs.yaml reading, report gen)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from crawl import (
    generate_report,
    load_existing_persons,
    load_labs,
    slugify,
    write_jsonl,
)

pytestmark = pytest.mark.unit


class TestSlugify:
    def test_basic(self):
        assert slugify("Stanford AI Lab") == "stanford_ai_lab"

    def test_chinese(self):
        assert slugify("北京智源") == "北京智源"  # non-ascii preserved

    def test_special_chars(self):
        assert slugify("MIT  CSAIL!!") == "mit_csail"


class TestLoadLabs:
    def test_loads_labs_list(self, tmp_path):
        yaml_content = """
labs:
  - name: "Test Lab"
    domain: "https://test.example"
  - name: "Lab Two"
    domain: "https://two.example"
"""
        labs_file = tmp_path / "labs.yaml"
        labs_file.write_text(yaml_content, encoding="utf-8")
        labs = load_labs(str(labs_file))
        assert len(labs) == 2
        assert labs[0]["name"] == "Test Lab"
        assert labs[1]["domain"] == "https://two.example"

    def test_match_by_name(self, tmp_path):
        yaml_content = """
labs:
  - name: "Stanford AI Lab"
    domain: "https://ai.stanford.edu"
  - name: "MIT CSAIL"
    domain: "https://www.csail.mit.edu"
"""
        labs_file = tmp_path / "labs.yaml"
        labs_file.write_text(yaml_content, encoding="utf-8")
        match = load_labs(str(labs_file), match="Stanford")
        assert len(match) == 1
        assert match[0]["name"] == "Stanford AI Lab"


class TestWriteJsonl:
    def test_writes_valid_jsonl(self, tmp_path):
        persons = [
            {"name": "Alice", "role_section": "Faculty"},
            {"name": "Bob", "role_section": "PhD Students"},
        ]
        path = write_jsonl(persons, str(tmp_path), "test_lab", "2026-06-29")
        content = Path(path).read_text(encoding="utf-8")
        lines = [json.loads(l) for l in content.strip().split("\n")]
        assert len(lines) == 2
        assert lines[0]["name"] == "Alice"
        assert lines[1]["role_section"] == "PhD Students"

    def test_skips_entries_without_name(self, tmp_path):
        persons = [
            {"name": "Alice", "role_section": "Faculty"},
            {"role_section": "Unknown"},  # no name -> skipped
        ]
        path = write_jsonl(persons, str(tmp_path), "test_lab", "2026-06-29")
        content = Path(path).read_text(encoding="utf-8")
        lines = [json.loads(l) for l in content.strip().split("\n")]
        assert len(lines) == 1  # the nameless one dropped


class TestGenerateReport:
    def test_report_contains_counts_and_roles(self, tmp_path):
        persons = [
            {"name": "A", "role_section": "Faculty"},
            {"name": "B", "role_section": "PhD Students"},
            {"name": "C", "role_section": "PhD Students"},
        ]
        report = generate_report(
            persons,
            str(tmp_path),
            "test_lab",
            "https://test.example",
            "2026-06-29",
        )
        assert "3" in report  # total
        assert "Faculty" in report
        assert "PhD Students" in report


class TestLoadExistingPersons:
    def test_reads_most_recent_jsonl(self, tmp_path):
        """#2 resume: load_existing_persons reads the newest prior JSONL."""
        lab_dir = tmp_path / "test_lab"
        lab_dir.mkdir()
        # write two files, older + newer
        (lab_dir / "_2026-06-28.jsonl").write_text(
            '{"name":"Old","role_section":"Faculty"}\n', encoding="utf-8"
        )
        (lab_dir / "_2026-06-29.jsonl").write_text(
            '{"name":"Alice","role_section":"PhD Students"}\n'
            '{"name":"Bob","role_section":"Postdocs"}\n',
            encoding="utf-8",
        )
        persons = load_existing_persons(str(tmp_path), "test_lab")
        assert len(persons) == 2  # the newer file
        assert persons[0]["name"] == "Alice"

    def test_returns_empty_when_no_prior(self, tmp_path):
        """No prior JSONL → empty list (first run)."""
        persons = load_existing_persons(str(tmp_path), "new_lab")
        assert persons == []

    def test_skips_malformed_lines(self, tmp_path):
        """Malformed JSON lines are skipped, not fatal."""
        lab_dir = tmp_path / "test_lab"
        lab_dir.mkdir()
        (lab_dir / "_2026-06-29.jsonl").write_text(
            '{"name":"Alice"}\n'
            'not valid json\n'
            '{"name":"Bob"}\n',
            encoding="utf-8",
        )
        persons = load_existing_persons(str(tmp_path), "test_lab")
        assert len(persons) == 2  # Alice + Bob, malformed line skipped

