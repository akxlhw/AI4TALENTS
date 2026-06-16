"""Pydantic schemas for genealogy API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenealogyNode(BaseModel):
    """Node in genealogy network response."""

    talent_id: int
    name: str
    institution: str | None = None
    composite_score: float = 0.0
    tier: str = "tier4"
    h_index: int = 0
    cited_by_count: int = 0
    is_root: bool = False


class GenealogyLink(BaseModel):
    """Link in genealogy network response."""

    source: int
    target: int
    type: str  # advisor_student / mentor_mentee / senior_junior
    confidence: float = Field(..., ge=0.0, le=1.0)
    shared_institution: bool = False
    evidence_count: int = 0
    first_year: int | None = None
    last_year: int | None = None


class GenealogyStats(BaseModel):
    """Statistics for genealogy network."""

    total_nodes: int = 0
    total_links: int = 0
    tier_distribution: dict[str, int] = Field(default_factory=dict)


class GenealogyNetworkResponse(BaseModel):
    """Full genealogy network for a given root talent."""

    root_talent: GenealogyNode
    nodes: list[GenealogyNode] = Field(default_factory=list)
    links: list[GenealogyLink] = Field(default_factory=list)
    stats: GenealogyStats = Field(default_factory=GenealogyStats)


class InfluenceRankingItem(BaseModel):
    """Single item in influence ranking."""

    talent_id: int
    name: str
    institution: str | None = None
    composite_score: float = 0.0
    tier: str = "tier4"
    h_index: int = 0
    cited_by_count: int = 0
    works_count: int = 0


class SyncStatusResponse(BaseModel):
    """Genealogy sync status."""

    status: str
    processed: int = 0
    total: int = 0
    edges: int = 0
    current_phase: str = ""
