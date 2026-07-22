"""Pydantic DTOs for the competition domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkipReason(BaseModel):
    """Reason a JSONL line was skipped during import."""

    line: int
    reason: str


class CompImportReport(BaseModel):
    """Report returned by the import endpoint."""

    source_code: str
    contest_external_id: str
    contest_name: str = ""
    total_lines: int = 0
    persons_parsed: int = 0
    persons_upserted: int = 0
    teams_parsed: int = 0
    teams_upserted: int = 0
    results_deleted: int = 0
    results_inserted: int = 0
    skipped: int = 0
    skip_reasons: list[SkipReason] = Field(default_factory=list)
    duration_ms: int = 0


class CompTalentSummary(BaseModel):
    """Talent card in list views."""

    talent_id: int
    handle: str
    source_code: str
    real_name: str | None = None
    school: str | None = None
    country_code: str | None = None
    avatar_url: str | None = None
    current_rating: int | None = None
    max_rating: int | None = None
    rank_title: str | None = None
    contests_count: int = 0
    medals_gold: int = 0
    medals_silver: int = 0
    medals_bronze: int = 0
    last_contest_at: datetime | None = None


class CompResultItem(BaseModel):
    """One row of a talent's contest history."""

    contest_id: int
    contest_name: str
    start_time: datetime | None = None
    rank: int | None = None
    score: float | None = None
    rating_before: int | None = None
    rating_after: int | None = None
    award: str | None = None
    team_name: str | None = None
    source_url: str | None = None


class CompTalentDetail(CompTalentSummary):
    """Talent detail: profile + aggregates + contest history."""

    profile_url: str | None = None
    global_rank: int | None = None
    specialties: list[str] | None = None
    results: list[CompResultItem] = Field(default_factory=list)


class CompContestSummary(BaseModel):
    """Contest card in list views."""

    contest_id: int
    series_code: str
    external_id: str
    name: str
    start_time: datetime | None = None
    season: str | None = None
    status: str = "finished"
    source_url: str | None = None
    results_count: int = 0


class CompLeaderboardEntry(BaseModel):
    """Personal leaderboard row for a contest."""

    rank: int | None = None
    talent_id: int | None = None
    handle: str | None = None
    real_name: str | None = None
    school: str | None = None
    country_code: str | None = None
    avatar_url: str | None = None
    score: float | None = None
    rating_before: int | None = None
    rating_after: int | None = None
    award: str | None = None
    team_name: str | None = None


class CompTeamLeaderboardEntry(BaseModel):
    """Team leaderboard row for a contest."""

    rank: int | None = None
    team_id: int | None = None
    team_name: str | None = None
    school: str | None = None
    country_code: str | None = None
    award: str | None = None
    score: float | None = None
    team_members: list[dict[str, Any]] | None = None


class CompContestDetail(CompContestSummary):
    """Contest detail: info + personal leaderboard + team leaderboard."""

    duration_seconds: int | None = None
    raw_meta: dict[str, Any] | None = None
    results: list[CompLeaderboardEntry] = Field(default_factory=list)
    team_results: list[CompTeamLeaderboardEntry] = Field(default_factory=list)


class CompSeriesOut(BaseModel):
    """Series row with counts."""

    series_id: int
    code: str
    name: str
    name_en: str | None = None
    homepage: str | None = None
    description: str | None = None
    logo_url: str | None = None
    is_enabled: bool = True
    talents_count: int = 0
    contests_count: int = 0


class CompOverviewOut(BaseModel):
    """Overview stats payload."""

    total_talents: int = 0
    total_contests: int = 0
    total_series: int = 0
    total_medalists: int = 0
    total_countries: int = 0
    top_medalists: list[CompTalentSummary] = Field(default_factory=list)
    recent_contests: list[CompContestSummary] = Field(default_factory=list)
