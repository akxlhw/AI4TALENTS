import { apiClient } from './client'

export const labApi = {
  getStats: () => apiClient.get('/lab/stats'),

  listTalents: (params?: Record<string, unknown>) => apiClient.get('/lab/talents', { params }),

  getTalent: (id: number) => apiClient.get(`/lab/talents/${id}`),

  importUpload: (file: File, parentLab: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('parent_lab', parentLab)
    return apiClient.post('/lab/import/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
