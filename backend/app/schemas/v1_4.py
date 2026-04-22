"""
API schemas for v1.4 features.
JD Match, Recommend, and enhanced Search schemas.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


# ============ Enhanced Search Schemas ============

class SearchMode:
    """Search mode constants."""
    KEYWORD = "keyword"
    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class EnhancedSearchRequest(BaseModel):
    """Enhanced search request."""
    q: str = Field(..., min_length=1, description="Search query")
    mode: str = Field(default="keyword", description="Search mode: keyword, fulltext, semantic, hybrid")
    fields: List[str] = Field(
        default=["name", "title", "topics", "works"],
        description="Fields to search in"
    )
    fuzzy: bool = Field(default=False, description="Enable fuzzy matching")
    role_type: Optional[str] = Field(default=None, description="Filter by role type")
    school_id: Optional[int] = Field(default=None, description="Filter by school ID")
    min_citations: Optional[int] = Field(default=None, description="Minimum citations")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")


class SemanticSearchResult(BaseModel):
    """Semantic search result with similarity score."""
    talent_id: int
    name: str
    name_en: Optional[str] = None
    role_type: str
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    topic_tags: List[str] = Field(default_factory=list)
    openalex_topics: List[str] = Field(default_factory=list, description="OpenAlex research topics")
    similarity_score: Optional[float] = Field(default=None, description="Similarity score for semantic search")
    match_sources: List[str] = Field(default_factory=list, description="How this result was matched: fulltext, semantic_research, semantic_papers")
    highlight: Optional[str] = None


class EnhancedSearchResponse(BaseModel):
    """Enhanced search response."""
    items: List[SemanticSearchResult]
    total: int
    query: str
    mode: str
    page: int
    page_size: int
    took_ms: float = Field(description="Query execution time in milliseconds")
    precise_count: int = Field(default=0, description="Number of precise matches (similarity >= 0.95)")
    similar_count: int = Field(default=0, description="Number of similar matches (0.7 <= similarity < 0.95)")
    fulltext_count: int = Field(default=0, description="Number of fulltext matches")
    semantic_count: int = Field(default=0, description="Number of semantic matches")


# ============ JD Match Schemas ============

class JDFeaturesResponse(BaseModel):
    """JD parsing result.

    v1.4.1: Simplified to only return research_areas.
    """
    research_areas: List[str] = Field(default_factory=list, description="Research areas (English keywords)")


class MatchConfigRequest(BaseModel):
    """Match configuration request."""
    weights: dict = Field(
        default_factory=lambda: {
            "research": 1.0
        },
        description="Score weights"
    )
    filters: dict = Field(default_factory=dict, description="Filters")
    limit: int = Field(default=50, ge=1, le=100, description="Max results")


class MatchResultItemResponse(BaseModel):
    """Match result item.

    v1.4.1: Simplified to only return research_score and overall_score.
    """
    talent_id: int
    name: str
    title: str
    school_name: str
    overall_score: float = Field(description="Overall match score (0-100)")
    research_score: float = Field(description="Research match score")
    match_reasons: List[str] = Field(default_factory=list, description="Match reasons")


class MatchResponse(BaseModel):
    """JD match response."""
    session_id: int
    total: int
    items: List[MatchResultItemResponse]
    took_ms: float = Field(description="Match execution time in milliseconds")


class JDMatchRequest(BaseModel):
    """JD match request."""
    jd_text: str = Field(..., min_length=10, description="JD text content")
    config: Optional[MatchConfigRequest] = Field(default=None, description="Match configuration")


class JDParseRequest(BaseModel):
    """JD parse request."""
    jd_text: str = Field(..., min_length=10, description="JD text content")


# ============ Recommend Schemas ============

class RecommendRequest(BaseModel):
    """Recommendation request."""
    reference_talent_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Reference talent IDs"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max results")
    filters: dict = Field(default_factory=dict, description="Filters")


class RecommendResultItem(BaseModel):
    """Recommendation result item."""
    talent_id: int
    name: str
    title: str
    school_name: str
    similarity_score: float = Field(description="Similarity score (0-1)")
    reasons: List[str] = Field(default_factory=list, description="Recommendation reasons")


class RecommendResponse(BaseModel):
    """Recommendation response."""
    reference_talents: List[int]
    total: int
    items: List[RecommendResultItem]
    mode: str
    took_ms: float = Field(description="Query execution time in milliseconds")
