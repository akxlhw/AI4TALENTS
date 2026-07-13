import { apiClient } from './client'
import type {
  LabProfile,
  LabStats,
  LabTalent,
  LabTalentDetail,
  LabWithTalents,
  PaginatedResponse,
} from '../../types'

export interface LabTalentSearchParams {
  keyword?: string
  parent_lab?: string
  lab_name?: string
  role_type?: string
  academic_level?: string
  research_area?: string
  sort_by?: string
  page?: number
  page_size?: number
}

export interface LabImportReport {
  parent_lab: string
  total_lines: number
  total_parsed: number
  inserted: number
  skipped: number
  skip_reasons: { line: number; reason: string }[]
}

export const labApi = {
  getStats: () => apiClient.get<LabStats>('/lab/stats'),

  listLabs: () => apiClient.get<LabWithTalents[]>('/lab/labs'),

  getLabProfile: (parentLab: string) =>
    apiClient.get<LabProfile>(`/lab/labs/${encodeURIComponent(parentLab)}/profile`),

  listTalents: (params?: LabTalentSearchParams) =>
    apiClient.get<PaginatedResponse<LabTalent>>('/lab/talents', { params }),

  getTalent: (id: number) => apiClient.get<LabTalentDetail>(`/lab/talents/${id}`),

  getHomepagePreview: (id: number) =>
    apiClient.get<{ html: string; base_url: string; title: string; status: string }>(
      `/lab/talents/${id}/homepage-preview`
    ),

  triggerPrefetch: (parentLab: string) =>
    apiClient.post('/lab/prefetch-homepages', null, { params: { parent_lab: parentLab } }),

  getPrefetchStatus: () =>
    apiClient.get<{ status: string; processed: number; total: number; current: string; errors: number }>(
      '/lab/prefetch-homepages/status'
    ),

  importUpload: (file: File, parentLab?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (parentLab) {
      formData.append('parent_lab', parentLab)
    }
    return apiClient.post<LabImportReport>('/lab/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
