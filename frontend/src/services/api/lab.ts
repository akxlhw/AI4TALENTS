import { apiClient } from './client'
import type { LabStats, LabTalent, LabTalentDetail, PaginatedResponse } from '../../types'

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

  listTalents: (params?: LabTalentSearchParams) =>
    apiClient.get<PaginatedResponse<LabTalent>>('/lab/talents', { params }),

  getTalent: (id: number) => apiClient.get<LabTalentDetail>(`/lab/talents/${id}`),

  importUpload: (file: File, parentLab: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('parent_lab', parentLab)
    return apiClient.post<LabImportReport>('/lab/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
