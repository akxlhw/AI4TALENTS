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
        default=["name", "title", "research_interests", "topics"],
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
    research_interests: Optional[str] = None
    similarity_score: Optional[float] = Field(default=None, description="Similarity score for semantic search")
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


# ============ JD Match Schemas ============

class JDFeaturesResponse(BaseModel):
    """JD parsing result."""
    skills: List[str] = Field(default_factory=list, description="Required skills")
    experience: str = Field(default="", description="Experience requirement")
    research_areas: List[str] = Field(default_factory=list, description="Research areas")
    role_type: str = Field(default="", description="Role type")
    education_level: Optional[str] = Field(default=None, description="Education level requirement")


class MatchConfigRequest(BaseModel):
    """Match configuration request."""
    weights: dict = Field(
        default_factory=lambda: {
            "skill": 0.4,
            "research": 0.3,
            "experience": 0.2,
            "education": 0.1
        },
        description="Score weights"
    )
    filters: dict = Field(default_factory=dict, description="Filters")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")


class MatchResultItemResponse(BaseModel):
    """Match result item."""
    talent_id: int
    name: str
    title: str
    school_name: str
    overall_score: float = Field(description="Overall match score (0-100)")
    skill_score: float = Field(description="Skill match score")
    research_score: float = Field(description="Research match score")
    experience_score: float = Field(description="Experience match score")
    match_reasons: List[str] = Field(default_factory=list, description="Match reasons")
    highlight_skills: List[str] = Field(default_factory=list, description="Matched skills to highlight")


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
