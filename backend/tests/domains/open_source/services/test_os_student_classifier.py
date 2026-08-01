"""Unit tests for the open-source student classifier (pure functions)."""

from __future__ import annotations

import pytest

from app.domains.open_source.services import os_student_classifier as clf


@pytest.fixture(autouse=True)
def _clear_school_terms_cache():
    """Each test gets a fresh school-term cache (dict loading is lru_cached)."""
    clf._school_terms.cache_clear()
    yield
    clf._school_terms.cache_clear()


class TestBioStudent:
    @pytest.mark.parametrize(
        "bio",
        [
            "CS student at some place",
            "Undergraduate studying compilers",
            "undergrad @ nowhere",
            "Graduate student, ML",
            "PhD student in NLP",
            "Ph.D candidate",
            "phd candidate @ X",
            "Master student",
            "Bachelor of Engineering",
            "计算机在读研究生",
            "本科生一枚",
            "博士在读",
            "硕士生",
        ],
    )
    def test_student_bio_hits(self, bio: str) -> None:
        result = clf.classify(bio=bio)
        assert result.is_student is True
        assert result.reason == "bio_student"

    def test_student_bio_beats_staff_company(self) -> None:
        # bio 命中学生关键词时，即便 bio 也含 staff 词也判为学生（bio_student 优先）
        result = clf.classify(bio="PhD student, advised by a professor", company="MIT")
        assert result.is_student is True
        assert result.reason == "bio_student"

    def test_no_false_positive_without_word_boundary(self) -> None:
        # "students" 之外的变体不应命中：如 "studious"
        result = clf.classify(bio="studious hacker")
        assert result.is_student is False


class TestStaffExclusion:
    @pytest.mark.parametrize(
        "bio",
        [
            "Professor at MIT",
            "faculty member",
            "Postdoc in CS",
            "post-doctoral fellow",
            "Research Scientist",
            "AI researcher",
            "Lecturer",
            "staff engineer at a university lab",
            "清华大学教授",
            "研究员",
            "讲师",
        ],
    )
    def test_staff_bio_blocks_company_school(self, bio: str) -> None:
        result = clf.classify(company="Stanford University", bio=bio)
        assert result.is_student is False
        assert result.reason == "none"


class TestCompanySchool:
    @pytest.mark.parametrize(
        "company",
        [
            "@Stanford University",
            "MIT",
            "cmu",
            "UC Berkeley",
            "Georgia Tech",
            "Tsinghua University",
            "清华大学",
            "上海交大",
            "Some College",
        ],
    )
    def test_company_school_hits(self, company: str) -> None:
        result = clf.classify(company=company)
        assert result.is_student is True
        assert result.reason == "company_school"

    @pytest.mark.parametrize(
        "company",
        [
            "Acme Research Institute",  # institute 不算学校（虚构名，确保不在词典中）
            "Google",
            "@microsoft",
            "Submit Inc",  # MIT 词边界防护
            "Acme Solutions",
        ],
    )
    def test_company_non_school(self, company: str) -> None:
        result = clf.classify(company=company)
        assert result.is_student is False

    def test_institute_not_treated_as_school(self) -> None:
        assert clf.classify(company="Acme Research Institute").is_student is False


class TestSchoolDict:
    def test_dict_name_hit(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        import json

        dict_file = tmp_path / "school_dict.json"
        dict_file.write_text(
            json.dumps({"names": ["ETH Zurich"], "aliases": {"苏黎世联邦理工": "ETH Zurich"}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(clf, "_SCHOOL_DICT_PATH", dict_file)
        clf._school_terms.cache_clear()

        assert clf.classify(company="@ETH Zurich").is_student is True
        assert clf.classify(company="苏黎世联邦理工").is_student is True

    def test_dict_alias_word_boundary(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        import json

        dict_file = tmp_path / "school_dict.json"
        dict_file.write_text(
            json.dumps({"names": [], "aliases": {"CMU": "Carnegie Mellon University"}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(clf, "_SCHOOL_DICT_PATH", dict_file)
        clf._school_terms.cache_clear()

        assert clf.classify(company="CMU").is_student is True
        assert clf.classify(company="acmus corp").is_student is False

    def test_missing_dict_degrades_gracefully(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setattr(clf, "_SCHOOL_DICT_PATH", tmp_path / "nonexistent.json")
        clf._school_terms.cache_clear()

        # 通用词 + 手工别名仍可用，不抛异常
        assert clf.classify(company="Oxford University").is_student is True
        assert clf.classify(company="MIT").is_student is True
        assert clf.classify(company="Google").is_student is False
