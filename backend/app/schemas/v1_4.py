"""
API schemas for v1.4 features.
JD Match, Recommend, and enhanced Search schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

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
    mode: str = Field(
        default="keyword", description="Search mode: keyword, fulltext, semantic, hybrid"
    )
    fields: list[str] = Field(
        default=["name", "title", "topics", "works"], description="Fields to search in"
    )
    fuzzy: bool = Field(default=False, description="Enable fuzzy matching")
    role_type: str | None = Field(default=None, description="Filter by role type")
    school_id: int | None = Field(default=None, description="Filter by school ID")
    min_citations: int | None = Field(default=None, description="Minimum citations")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")


class SemanticSearchResult(BaseModel):
    """Semantic search result with similarity score."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    name_en: str | None = Field(default=None, description="English name")
    role_type: str = Field(description="Role type")
    school_name: str | None = Field(default=None, description="School name")
    current_title: str | None = Field(default=None, description="Current title/position")
    works_count: int = Field(default=0, description="Number of works")
    cited_by_count: int = Field(default=0, description="Citation count")
    h_index: int = Field(default=0, description="H-index")
    topic_tags: list[str] = Field(default_factory=list, description="Topic tags")
    openalex_topics: list[str] = Field(default_factory=list, description="OpenAlex research topics")
    similarity_score: float | None = Field(
        default=None, description="Similarity score for semantic search"
    )
    match_sources: list[str] = Field(
        default_factory=list,
        description="How this result was matched: fulltext, semantic_research, semantic_papers",
    )
    highlight: str | None = Field(default=None, description="Highlighted search snippet")


class EnhancedSearchResponse(BaseModel):
    """Enhanced search response."""

    items: list[SemanticSearchResult] = Field(description="Search results")
    total: int = Field(description="Total count")
    query: str = Field(description="Search query")
    mode: str = Field(description="Search mode used")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    took_ms: float = Field(description="Query execution time in milliseconds")
    precise_count: int = Field(
        default=0, description="Number of precise matches (similarity >= 0.95)"
    )
    similar_count: int = Field(
        default=0, description="Number of similar matches (0.7 <= similarity < 0.95)"
    )
    fulltext_count: int = Field(default=0, description="Number of fulltext matches")
    semantic_count: int = Field(default=0, description="Number of semantic matches")


# ============ JD Match Schemas ============


class JDFeaturesResponse(BaseModel):
    """JD parsing result.

    v1.4.1: Simplified to only return research_areas.
    """

    research_areas: list[str] = Field(
        default_factory=list, description="Research areas (English keywords)"
    )


class MatchConfigRequest(BaseModel):
    """Match configuration request."""

    weights: dict = Field(default_factory=lambda: {"research": 1.0}, description="Score weights")
    filters: dict = Field(default_factory=dict, description="Filters")
    limit: int = Field(default=50, ge=1, le=100, description="Max results")


class MatchResultItemResponse(BaseModel):
    """Match result item.

    v1.4.1: Simplified to only return research_score and overall_score.
    """

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    title: str = Field(description="Current title/position")
    school_name: str = Field(description="School name")
    overall_score: float = Field(description="Overall match score (0-100)")
    research_score: float = Field(description="Research match score")
    match_reasons: list[str] = Field(default_factory=list, description="Match reasons")


class MatchResponse(BaseModel):
    """JD match response."""

    session_id: int = Field(description="Match session ID")
    total: int = Field(description="Total matched results")
    items: list[MatchResultItemResponse] = Field(description="Match results")
    took_ms: float = Field(description="Match execution time in milliseconds")


class JDMatchRequest(BaseModel):
    """JD match request."""

    jd_text: str = Field(..., min_length=10, description="JD text content")
    config: MatchConfigRequest | None = Field(default=None, description="Match configuration")


class JDParseRequest(BaseModel):
    """JD parse request."""

    jd_text: str = Field(..., min_length=10, description="JD text content")


# ============ Recommend Schemas ============


class RecommendRequest(BaseModel):
    """Recommendation request."""

    reference_talent_ids: list[int] = Field(
        ..., min_length=1, max_length=10, description="Reference talent IDs"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max results")
    filters: dict = Field(default_factory=dict, description="Filters")


class RecommendResultItem(BaseModel):
    """Recommendation result item."""

    talent_id: int = Field(description="Talent ID")
    name: str = Field(description="Name")
    title: str = Field(description="Current title/position")
    school_name: str = Field(description="School name")
    similarity_score: float = Field(description="Similarity score (0-1)")
    reasons: list[str] = Field(default_factory=list, description="Recommendation reasons")


class RecommendResponse(BaseModel):
    """Recommendation response."""

    reference_talents: list[int] = Field(description="Reference talent IDs")
    total: int = Field(description="Total recommended results")
    items: list[RecommendResultItem] = Field(description="Recommendation results")
    mode: str = Field(description="Recommendation mode: vector/tag")
    took_ms: float = Field(description="Query execution time in milliseconds")
