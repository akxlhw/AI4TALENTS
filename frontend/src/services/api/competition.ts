import { apiClient } from './client'
import type { PaginatedResponse } from '../../types'

// ---- DTOs (mirror backend app/domains/competition/schemas/competition.py) ----

export interface CompTalentSummary {
  talent_id: number
  handle: string
  source_code: string
  real_name: string | null
  school: string | null
  country_code: string | null
  avatar_url: string | null
  current_rating: number | null
  max_rating: number | null
  rank_title: string | null
  contests_count: number
  medals_gold: number
  medals_silver: number
  medals_bronze: number
  last_contest_at: string | null
}

export interface CompResultItem {
  contest_id: number
  contest_name: string
  start_time: string | null
  rank: number | null
  score: number | null
  rating_before: number | null
  rating_after: number | null
  award: string | null
  team_name: string | null
  source_url: string | null
}

export interface CompTalentDetail extends CompTalentSummary {
  profile_url: string | null
  global_rank: number | null
  specialties: string[] | null
  results: CompResultItem[]
}

export interface CompContestSummary {
  contest_id: number
  series_code: string
  external_id: string
  name: string
  start_time: string | null
  season: string | null
  status: string
  source_url: string | null
  results_count: number
}

export interface CompLeaderboardEntry {
  rank: number | null
  talent_id: number | null
  handle: string | null
  school: string | null
  country_code: string | null
  avatar_url: string | null
  score: number | null
  rating_before: number | null
  rating_after: number | null
  award: string | null
  team_name: string | null
}

export interface CompTeamLeaderboardEntry {
  rank: number | null
  team_id: number | null
  team_name: string | null
  school: string | null
  country_code: string | null
  award: string | null
  score: number | null
  team_members: { handle?: string; real_name: string; role?: string }[] | null
}

export interface CompContestDetail extends CompContestSummary {
  duration_seconds: number | null
  raw_meta: Record<string, unknown> | null
  results: CompLeaderboardEntry[]
  team_results: CompTeamLeaderboardEntry[]
}

export interface CompSeriesOut {
  series_id: number
  code: string
  name: string
  name_en: string | null
  homepage: string | null
  description: string | null
  logo_url: string | null
  is_enabled: boolean
  talents_count: number
  contests_count: number
}

export interface CompOverviewOut {
  total_talents: number
  total_contests: number
  total_series: number
  total_medalists: number
  total_countries: number
  top_talents: CompTalentSummary[]
  recent_contests: CompContestSummary[]
}

export interface CompImportReport {
  source_code: string
  contest_external_id: string
  contest_name: string
  total_lines: number
  persons_parsed: number
  persons_upserted: number
  teams_parsed: number
  teams_upserted: number
  results_deleted: number
  results_inserted: number
  skipped: number
  skip_reasons: { line: number; reason: string }[]
  duration_ms: number
}

export interface CompTalentSearchParams {
  keyword?: string
  country_code?: string
  school?: string
  min_rating?: number
  rank_title?: string
  sort_by?: string
  page?: number
  page_size?: number
}

export interface CompContestSearchParams {
  series_code?: string
  season?: string
  keyword?: string
  year_gte?: number
  page?: number
  page_size?: number
}

export const compApi = {
  getOverview: () => apiClient.get<CompOverviewOut>('/comp/overview'),

  listSeries: () => apiClient.get<CompSeriesOut[]>('/comp/series'),

  listTalents: (params?: CompTalentSearchParams) =>
    apiClient.get<PaginatedResponse<CompTalentSummary>>('/comp/talents', { params }),

  getTalent: (id: number) => apiClient.get<CompTalentDetail>(`/comp/talents/${id}`),

  listContests: (params?: CompContestSearchParams) =>
    apiClient.get<PaginatedResponse<CompContestSummary>>('/comp/contests', { params }),

  getContest: (id: number) => apiClient.get<CompContestDetail>(`/comp/contests/${id}`),

  importUpload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<CompImportReport>('/comp/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
