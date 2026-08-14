import { apiClient } from './client'
import type { OSSearchQuery } from '../../types'

export interface OSSearchFilters {
  tech_elements?: string[]
  languages?: string[]
  location?: string
  company?: string
  min_stars?: number
  repo_full_names?: string[]
  is_committer?: boolean
  is_student?: boolean
}

export interface OSSearchParams {
  q?: string
  mode?: 'keyword' | 'semantic' | 'hybrid'
  filters?: OSSearchFilters
  sort_by?: string
  page?: number
  page_size?: number
}

export const openSourceApi = {
  getStats: () => apiClient.get('/open-source/stats'),
  getTrending: (params?: { period?: string; limit?: number }) =>
    apiClient.get('/open-source/trending', { params }),

  listDevelopers: (params?: OSSearchQuery & { min_stars?: number }) =>
    apiClient.get('/open-source/developers', { params }),
  getDeveloper: (id: number) =>
    apiClient.get(`/open-source/developers/${id}`),
  exportDevelopers: (developerIds: number[], format: 'csv' | 'xlsx' = 'csv') =>
    apiClient.post(`/open-source/developers/export`, { developer_ids: developerIds, format }, {
      responseType: 'blob',
    }),
  getAllDeveloperIds: (params?: Record<string, unknown>) =>
    apiClient.get('/open-source/developers/ids', { params }),
  getRepository: (owner: string, name: string) =>
    apiClient.get(`/open-source/repositories/${owner}/${name}`),
  getRepositoryContributors: (owner: string, name: string, params?: { page?: number; page_size?: number }) =>
    apiClient.get(`/open-source/repositories/${owner}/${name}/contributors`, { params }),
  getRepositories: (id: number, params?: { page?: number; page_size?: number; sort_by?: string }) =>
    apiClient.get(`/open-source/developers/${id}/repositories`, { params }),
  getContributions: (id: number) =>
    apiClient.get(`/open-source/developers/${id}/contributions`),
  getLanguages: (id: number) =>
    apiClient.get(`/open-source/developers/${id}/languages`),
  compare: (developerIds: number[]) =>
    apiClient.post('/open-source/developers/compare', { developer_ids: developerIds }),
  getRecommendations: (id: number, limit?: number) =>
    apiClient.get(`/open-source/developers/${id}/recommend`, { params: { limit } }),

  search: (params: OSSearchParams) =>
    apiClient.post('/open-source/search', params),

  addFavorite: (developerId: number, notes?: string) =>
    apiClient.post('/open-source/favourites', { developer_id: developerId, notes }),
  listFavorites: (params?: { page?: number; page_size?: number; keyword?: string }) =>
    apiClient.get('/open-source/favourites', { params }),
  updateFavorite: (developerId: number, data: { notes?: string; followup_status?: string }) =>
    apiClient.put(`/open-source/favourites/${developerId}`, data),
  removeFavorite: (developerId: number) =>
    apiClient.delete(`/open-source/favourites/${developerId}`),
  getFavoriteIds: () =>
    apiClient.get('/open-source/favourites/ids'),

  listTalentPools: () =>
    apiClient.get('/open-source/talent-pools'),
  createTalentPool: (data: { pool_name: string; pool_type?: string; scope_desc?: string }) =>
    apiClient.post('/open-source/talent-pools', data),
  addPoolMember: (poolId: number, developerId: number) =>
    apiClient.post(`/open-source/talent-pools/${poolId}/members/${developerId}`),
  removePoolMember: (poolId: number, developerId: number) =>
    apiClient.delete(`/open-source/talent-pools/${poolId}/members/${developerId}`),
  getPoolMembers: (poolId: number, params?: { page?: number; page_size?: number }) =>
    apiClient.get(`/open-source/talent-pools/${poolId}/members`, { params }),

  listRepoConfigs: (params?: Record<string, unknown>) =>
    apiClient.get('/open-source/repo-configs', { params }),
  listRepositories: (params?: Record<string, unknown>) =>
    apiClient.get('/open-source/repositories', { params }),
  createRepoConfig: (data: Record<string, unknown>) =>
    apiClient.post('/open-source/repo-configs', data),
  batchCreateRepoConfigs: (data: { repo_inputs: string[]; tech_element: string }) =>
    apiClient.post('/open-source/repo-configs/batch', data),
  updateRepoConfig: (id: number, data: Record<string, unknown>) =>
    apiClient.put(`/open-source/repo-configs/${id}`, data),
  deleteRepoConfig: (id: number) =>
    apiClient.delete(`/open-source/repo-configs/${id}`),
  purgeRepoConfigData: (id: number, params?: { dry_run?: boolean; delete_config?: boolean }) =>
    apiClient.post(`/open-source/repo-configs/${id}/purge`, null, { params }),
  collectRepo: (id: number, contributorsPerRepo?: number) =>
    apiClient.post(`/open-source/repo-configs/${id}/collect`, null, { params: { contributors_per_repo: contributorsPerRepo } }),
  collectBatchRepos: (repoConfigIds: number[], contributorsPerRepo?: number) =>
    apiClient.post('/open-source/repo-configs/collect-batch', {
      repo_config_ids: repoConfigIds,
      contributors_per_repo: contributorsPerRepo ?? 0,
    }),
  checkCollectionHistory: (repoConfigIds: number[]) =>
    apiClient.get('/open-source/repo-configs/collect-check', {
      params: { ids: repoConfigIds.join(',') },
    }),

  listCollectTasks: () =>
    apiClient.get('/open-source/collect/tasks'),
  getCollectTask: (id: number) =>
    apiClient.get(`/open-source/collect/tasks/${id}`),
  createCollectTask: (data: Record<string, unknown>) =>
    apiClient.post('/open-source/collect/tasks', data),
  cancelCollectTask: (id: number) =>
    apiClient.post(`/open-source/collect/tasks/${id}/cancel`),
  deleteCollectTask: (id: number) =>
    apiClient.delete(`/open-source/collect/tasks/${id}`),

  jdMatch: (data: { jd_text: string; filters?: Record<string, unknown>; top_k?: number }) =>
    apiClient.post('/open-source/jd-match', data),

  getEmbeddingStatus: () =>
    apiClient.get('/open-source/embeddings/status'),
  getEmbeddingProgress: () =>
    apiClient.get('/open-source/embeddings/progress'),
  generateEmbeddings: (batchSize?: number, force?: boolean) =>
    apiClient.post('/open-source/embeddings/generate', { batch_size: batchSize, force }),
  cancelEmbeddingGeneration: () =>
    apiClient.post('/open-source/embeddings/cancel'),
}
