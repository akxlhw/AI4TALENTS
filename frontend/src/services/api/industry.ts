import { apiClient } from './client'
import type { PaginatedResponse } from '../../types'

// ---- DTOs (mirror backend app/domains/industry/schemas/industry.py) ----

export interface IndustryPosition {
  position_id: number
  title: string
  department: string | null
  tech_direction_codes: string[]
  level_min: number | null
  level_max: number | null
  jd_text: string | null
  jd_features: Record<string, unknown> | null
  status: string
  created_by: number | null
  created_at: string | null
  updated_at: string | null
  candidate_count: number
  avg_match_score: number | null
}

export interface IndustryPositionPayload {
  title: string
  department?: string | null
  tech_direction_codes?: string[]
  level_min?: number | null
  level_max?: number | null
  jd_text?: string | null
  status?: string
}

export interface IndustryPositionHit {
  position_id: number
  title: string
  match_score: number | null
  status: string
  touched: boolean
  match_tags: string[]
}

export interface IndustryTalentSummary {
  talent_id: number
  name: string
  current_org: string | null
  current_title: string | null
  degree: string | null
  years_of_exp: string | null
  years_of_exp_num: number | null
  location: string | null
  photo_url: string | null
  source: string | null
  best_match_score: number | null
  positions: IndustryPositionHit[]
}

export interface IndustryPositionMatchDetail extends IndustryPositionHit {
  score_school: number | null
  score_company: number | null
  score_direction: number | null
  match_tags: string[]
  match_reason: string | null
  notes: string | null
  batch: string | null
  source_platform: string | null
  updated_at: string | null
}

export interface IndustryExperience {
  range?: string
  year?: string
  org?: string
  title?: string
}

export interface IndustryTalentDetail extends Omit<IndustryTalentSummary, 'positions'> {
  experiences: IndustryExperience[]
  expect: string | null
  profile_url: string | null
  unified_person_id: string | null
  is_visible: boolean
  created_at: string | null
  updated_at: string | null
  positions: IndustryPositionMatchDetail[]
}

export interface IndustryTalentSearchParams {
  keyword?: string
  position_id?: number
  min_score?: number
  status?: string
  source_platform?: string
  tech_direction?: string
  sort_by?: string
  page?: number
  page_size?: number
}

export interface CandidateStatusPatch {
  status?: string
  touched?: boolean
  notes?: string
  // Score editing (0-100, optional)
  match_score?: number
  score_school?: number
  score_company?: number
  score_direction?: number
  match_reason?: string
}

export interface IndustryImportReport {
  total_lines: number
  total_parsed: number
  talents_inserted: number
  talents_updated: number
  links_inserted: number
  links_updated: number
  skipped: number
  skip_reasons: { line: number; reason: string }[]
  warnings: number
  aborted: boolean // true = 0 valid rows parsed, nothing was written
}

export const industryApi = {
  // ---- Positions (admin CRUD; no DELETE — archive via status) ----
  listPositions: (status?: string) =>
    apiClient.get<IndustryPosition[]>('/industry/positions', {
      params: status ? { status } : undefined,
    }),

  createPosition: (data: IndustryPositionPayload) =>
    apiClient.post<IndustryPosition>('/industry/positions', data),

  updatePosition: (positionId: number, data: Partial<IndustryPositionPayload>) =>
    apiClient.put<IndustryPosition>(`/industry/positions/${positionId}`, data),

  // ---- Talents ----
  listTalents: (params?: IndustryTalentSearchParams) =>
    apiClient.get<PaginatedResponse<IndustryTalentSummary>>('/industry/talents', { params }),

  getTalent: (id: number) => apiClient.get<IndustryTalentDetail>(`/industry/talents/${id}`),

  getTalentPositions: (id: number) =>
    apiClient.get<IndustryPositionMatchDetail[]>(`/industry/talents/${id}/positions`),

  patchCandidateStatus: (talentId: number, positionId: number, patch: CandidateStatusPatch) =>
    apiClient.patch<IndustryPositionMatchDetail>(
      `/industry/talents/${talentId}/positions/${positionId}`,
      patch
    ),

  removeFromPosition: (talentId: number, positionId: number) =>
    apiClient.delete<{ link_deleted: boolean; orphan_talent_deleted: boolean }>(
      `/industry/talents/${talentId}/positions/${positionId}`
    ),

  // ---- Batch management (super_admin) ----
  // batch=null represents the NULL-batch group (imports without a batch id);
  // it travels as the __none__ sentinel on the wire
  listBatches: (positionId: number) =>
    apiClient.get<{ batch: string | null; count: number; latest: string | null }[]>(
      `/industry/positions/${positionId}/batches`
    ),

  deleteBatch: (positionId: number, batch: string | null) =>
    apiClient.delete<{ links_deleted: number; talents_deleted: number }>(
      `/industry/positions/${positionId}/batches/${encodeURIComponent(batch ?? '__none__')}`
    ),

  // ---- Import (super_admin upload) ----
  importUpload: (file: File, positionId: number, batch?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('position_id', String(positionId))
    if (batch) {
      formData.append('batch', batch)
    }
    return apiClient.post<IndustryImportReport>('/industry/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // ---- Export (super_admin download, cross-server migration) ----
  // batch: string filters that batch; null exports the NULL-batch group;
  // undefined exports the whole position
  exportPosition: (positionId: number, batch?: string | null) =>
    apiClient.get(`/industry/positions/${positionId}/export`, {
      params: batch === null ? { batch: '__none__' } : batch ? { batch } : undefined,
      responseType: 'blob',
    }),
}
