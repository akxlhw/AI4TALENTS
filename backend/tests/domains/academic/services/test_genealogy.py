"""Tests for genealogy and influence services."""

from __future__ import annotations

import math

import pytest

from app.domains.academic.services.genealogy_service import GenealogyService
from app.domains.academic.services.influence_service import InfluenceService


class TestBuildEdgesFromStats:
    """Tests for GenealogyService._build_edges_from_stats confidence logic."""

    def test_minimal_pair_at_threshold_kept(self):
        """A pair with only positional pattern equals MIN_CONFIDENCE and is kept."""
        service = GenealogyService(session=None)  # noqa: session not used by this pure method
        pair_stats = {
            (1, 2): {
                "paper_count": 1,
                "shared_institution_count": 0,
                "years": [2020],
                "work_ids": ["w1"],
            }
        }
        edges = service._build_edges_from_stats(pair_stats)
        assert len(edges) == 1
        assert edges[0]["confidence_score"] == 0.30
        assert edges[0]["relationship_type"] == "senior_junior"

    def test_position_plus_institution_reaches_threshold(self):
        """Position pattern + shared institution yields senior_junior edge."""
        service = GenealogyService(session=None)
        pair_stats = {
            (1, 2): {
                "paper_count": 1,
                "shared_institution_count": 1,
                "years": [2020],
                "work_ids": ["w1"],
            }
        }
        edges = service._build_edges_from_stats(pair_stats)
        assert len(edges) == 1
        edge = edges[0]
        assert edge["from_talent_id"] == 1
        assert edge["to_talent_id"] == 2
        assert edge["relationship_type"] == "senior_junior"
        assert edge["confidence_score"] == pytest.approx(0.45, abs=0.01)
        assert edge["shared_institution"] is True

    def test_multiple_papers_and_time_span_bonus(self):
        """Multiple papers and long time span push confidence to advisor_student."""
        service = GenealogyService(session=None)
        pair_stats = {
            (1, 2): {
                "paper_count": 7,
                "shared_institution_count": 0,
                "years": [2018, 2019, 2020, 2021, 2022],
                "work_ids": [f"w{i}" for i in range(7)],
            }
        }
        edges = service._build_edges_from_stats(pair_stats)
        assert len(edges) == 1
        edge = edges[0]
        # 0.30 + 0.20 (max paper bonus) + 0.10 (time span) = 0.60
        assert edge["confidence_score"] == pytest.approx(0.60, abs=0.01)
        assert edge["relationship_type"] == "senior_junior"

    def test_mentor_mentee_with_high_confidence_and_institution(self):
        """High confidence + shared institution maps to mentor_mentee."""
        service = GenealogyService(session=None)
        pair_stats = {
            (1, 2): {
                "paper_count": 10,
                "shared_institution_count": 1,
                "years": [2015, 2016, 2017, 2018, 2019, 2020],
                "work_ids": [f"w{i}" for i in range(10)],
            }
        }
        edges = service._build_edges_from_stats(pair_stats)
        assert len(edges) == 1
        edge = edges[0]
        assert edge["relationship_type"] == "mentor_mentee"
        assert edge["confidence_score"] >= 0.65

    def test_evidence_work_ids_capped_at_50(self):
        """Evidence work_ids list is capped at 50 entries."""
        service = GenealogyService(session=None)
        pair_stats = {
            (1, 2): {
                "paper_count": 60,
                "shared_institution_count": 1,
                "years": [2020],
                "work_ids": [f"w{i}" for i in range(60)],
            }
        }
        edges = service._build_edges_from_stats(pair_stats)
        assert len(edges) == 1
        assert len(edges[0]["source_work_ids"]) == 50


class TestInfluenceNormalization:
    """Tests for InfluenceService normalization helpers."""

    def test_percentile_normalize_basic(self):
        values = {1: 10, 2: 20, 3: 30}
        result = InfluenceService._percentile_normalize(values)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(50.0)
        assert result[3] == pytest.approx(100.0)

    def test_percentile_normalize_single_value(self):
        result = InfluenceService._percentile_normalize({42: 100})
        assert result[42] == pytest.approx(50.0)

    def test_percentile_normalize_empty(self):
        assert InfluenceService._percentile_normalize({}) == {}

    def test_log_normalize_basic(self):
        values = {1: 0, 2: 9, 3: 99}
        result = InfluenceService._log_normalize(values)
        max_log = math.log(100)
        assert result[1] == pytest.approx(0.0, abs=0.01)
        assert result[2] == pytest.approx((math.log(10) / max_log) * 100, abs=0.01)
        assert result[3] == pytest.approx(100.0, abs=0.01)

    def test_log_normalize_empty(self):
        assert InfluenceService._log_normalize({}) == {}

    def test_log_normalize_all_zero(self):
        result = InfluenceService._log_normalize({1: 0, 2: 0})
        assert result[1] == 0.0
        assert result[2] == 0.0
