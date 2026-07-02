import { apiClient } from './client'

export const labApi = {
  getStats: () => apiClient.get('/lab/stats'),

  listTalents: (params?: Record<string, unknown>) => apiClient.get('/lab/talents', { params }),

  getTalent: (id: number) => apiClient.get(`/lab/talents/${id}`),
}
