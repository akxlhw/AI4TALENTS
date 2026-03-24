/**
 * API client for backend communication
 */
import axios, { AxiosInstance, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// API endpoints
export const api = {
  // Health
  health: {
    check: () => apiClient.get('/health'),
    ready: () => apiClient.get('/health/ready'),
    live: () => apiClient.get('/health/live'),
  },

  // Authentication
  auth: {
    login: (username: string, password: string) =>
      apiClient.post('/auth/login', { username, password }),
    logout: () => apiClient.post('/auth/logout'),
    refresh: (refreshToken: string) =>
      apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
    me: () => apiClient.get('/auth/me'),
    changePassword: (currentPassword: string, newPassword: string) =>
      apiClient.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      }),
  },

  // Overview
  overview: {
    get: () => apiClient.get('/overview'),
  },

  // Countries
  countries: {
    list: () => apiClient.get('/countries'),
  },

  // Schools
  schools: {
    list: (params?: { country_id?: number; keyword?: string; page?: number }) =>
      apiClient.get('/schools', { params }),
    get: (id: number) => apiClient.get(`/schools/${id}`),
    getTalents: (id: number, params?: { role_type?: string; page?: number }) =>
      apiClient.get(`/schools/${id}/talents`, { params }),
  },

  // Talents
  talents: {
    list: (params?: { school_id?: number; country_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/talents', { params }),
    get: (id: number) => apiClient.get(`/talents/${id}`),
    getWorks: (id: number, limit?: number) =>
      apiClient.get(`/talents/${id}/works`, { params: { limit } }),
    export: (talentIds: number[], format: 'csv' | 'xlsx' = 'csv') =>
      apiClient.post(`/talents/export?format=${format}`, null, {
        params: { talent_ids: talentIds },
        responseType: 'blob',
      }),
    compare: (talentIds: number[]) =>
      apiClient.post('/talents/compare', null, {
        params: { talent_ids: talentIds },
      }),
    getCollaborations: (id: number, limit?: number) =>
      apiClient.get(`/talents/${id}/collaborations`, { params: { limit } }),
  },

  // Search
  search: {
    talents: (params: { q: string; page?: number; page_size?: number }) =>
      apiClient.get('/search/talents', { params }),
  },

  // Admin
  admin: {
    listUsers: (params?: { role?: string; is_active?: boolean; page?: number; page_size?: number }) =>
      apiClient.get('/users', { params }),
    createUser: (data: { username: string; email: string; password: string; role?: string; display_name?: string }) =>
      apiClient.post('/users', data),
    getUser: (userId: number) =>
      apiClient.get(`/users/${userId}`),
    updateUser: (userId: number, data: { display_name?: string; department?: string; role?: string; is_active?: boolean }) =>
      apiClient.put(`/users/${userId}`, data),
    deactivateUser: (userId: number) =>
      apiClient.delete(`/users/${userId}`),
    getUserScopes: (userId: number) =>
      apiClient.get(`/users/${userId}/scopes`),
    addUserScope: (userId: number, data: { scope_type: string; scope_value: string; expires_at?: string; notes?: string }) =>
      apiClient.post(`/users/${userId}/scopes`, { user_id: userId, ...data }),
    removeUserScope: (userId: number, scopeId: number) =>
      apiClient.delete(`/users/${userId}/scopes/${scopeId}`),
    getMyAccessibleSchools: () =>
      apiClient.get('/users/me/scopes/schools'),
    checkSchoolAccess: (schoolId: number) =>
      apiClient.get(`/users/me/scopes/check/${schoolId}`),
    getAccessibleTechElements: () =>
      apiClient.get('/users/me/scopes/tech-elements'),
    getAccessibleCountries: () =>
      apiClient.get('/users/me/scopes/countries'),
    getDefaultView: () =>
      apiClient.get('/users/me/default-view'),
    updateDefaultView: (defaultView: 'tech_element' | 'country_school') =>
      apiClient.put('/users/me/default-view', { default_view: defaultView }),
  },

  // Favorites
  favorites: {
    add: (talentId: number, notes?: string) =>
      apiClient.post('/favorites', { talent_id: talentId, notes }),
    list: (params?: { page?: number; page_size?: number; role_type?: string; keyword?: string }) =>
      apiClient.get('/favorites', { params }),
    getIds: () =>
      apiClient.get('/favorites/ids'),
    check: (talentId: number) =>
      apiClient.get(`/favorites/${talentId}/check`),
    update: (talentId: number, notes?: string) =>
      apiClient.put(`/favorites/${talentId}`, { notes }),
    remove: (talentId: number) =>
      apiClient.delete(`/favorites/${talentId}`),
  },

  // Tech Elements
  techElements: {
    list: () =>
      apiClient.get('/tech-elements'),
    get: (id: number) =>
      apiClient.get(`/tech-elements/${id}`),
    getSummary: () =>
      apiClient.get('/tech-elements/summary'),
    getStats: (id: number) =>
      apiClient.get(`/tech-elements/${id}/stats`),
    getCountries: (id: number, directionId?: number) =>
      apiClient.get(`/tech-elements/${id}/countries`, { params: { direction_id: directionId } }),
    getSchools: (id: number, params?: { direction_id?: number; country_id?: number; page?: number; page_size?: number }) =>
      apiClient.get(`/tech-elements/${id}/schools`, { params }),
    getTalents: (id: number, params?: { direction_id?: number; country_id?: number; school_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get(`/tech-elements/${id}/talents`, { params }),
  },

  // Talent Pools
  talentPools: {
    list: () =>
      apiClient.get('/talent-pools'),
    get: (id: number) =>
      apiClient.get(`/talent-pools/${id}`),
    create: (data: { pool_name: string; pool_type?: string; scope_desc?: string }) =>
      apiClient.post('/talent-pools', data),
    update: (id: number, data: { pool_name?: string; scope_desc?: string; pool_status?: string }) =>
      apiClient.put(`/talent-pools/${id}`, data),
    delete: (id: number) =>
      apiClient.delete(`/talent-pools/${id}`),
    addMember: (poolId: number, talentId: number, notes?: string) =>
      apiClient.post(`/talent-pools/${poolId}/members`, { talent_id: talentId, notes }),
    removeMember: (poolId: number, talentId: number) =>
      apiClient.delete(`/talent-pools/${poolId}/members/${talentId}`),
    getMembers: (poolId: number, params?: { page?: number; page_size?: number }) =>
      apiClient.get(`/talent-pools/${poolId}/members`, { params }),
    updateFollowupStatus: (talentId: number, status: string) =>
      apiClient.put(`/talent-pools/favorites/${talentId}/followup`, { followup_status: status }),
    getFollowupStatuses: () =>
      apiClient.get('/talent-pools/followup-statuses'),
  },

  // Collect Configuration
  collect: {
    // Scopes
    listScopes: (params?: { scope_type?: string; is_enabled?: boolean }) =>
      apiClient.get('/collect/scopes', { params }),
    getScope: (scopeId: number) =>
      apiClient.get(`/collect/scopes/${scopeId}`),
    createScope: (data: { scope_code: string; scope_name: string; scope_type: string; scope_value: any[]; description?: string }) =>
      apiClient.post('/collect/scopes', data),
    updateScope: (scopeId: number, data: { scope_name?: string; scope_value?: any[]; is_enabled?: boolean; description?: string }) =>
      apiClient.put(`/collect/scopes/${scopeId}`, data),
    deleteScope: (scopeId: number) =>
      apiClient.delete(`/collect/scopes/${scopeId}`),
    // Strategies
    listStrategies: (params?: { strategy_type?: string; is_enabled?: boolean }) =>
      apiClient.get('/collect/strategies', { params }),
    getStrategy: (strategyId: number) =>
      apiClient.get(`/collect/strategies/${strategyId}`),
    createStrategy: (data: { strategy_code: string; strategy_name: string; strategy_type?: string; data_types: string[]; scope_ids?: number[]; schedule_cron?: string; fetch_config?: any; description?: string }) =>
      apiClient.post('/collect/strategies', data),
    updateStrategy: (strategyId: number, data: { strategy_name?: string; scope_ids?: number[]; data_types?: string[]; schedule_cron?: string; fetch_config?: any; is_enabled?: boolean; description?: string }) =>
      apiClient.put(`/collect/strategies/${strategyId}`, data),
    deleteStrategy: (strategyId: number) =>
      apiClient.delete(`/collect/strategies/${strategyId}`),
    // Tasks
    listTasks: (params?: { status?: string; strategy_id?: number; page?: number; page_size?: number }) =>
      apiClient.get('/collect/tasks', { params }),
    getTask: (taskId: number) =>
      apiClient.get(`/collect/tasks/${taskId}`),
    triggerTask: (data: { strategy_id?: number; task_type?: string }) =>
      apiClient.post('/collect/tasks', data),
    cancelTask: (taskId: number) =>
      apiClient.post(`/collect/tasks/${taskId}/cancel`),
    getActiveTasks: () =>
      apiClient.get('/collect/tasks/active'),
    // Options
    getScopeTypes: () =>
      apiClient.get('/collect/options/scope-types'),
    getStrategyTypes: () =>
      apiClient.get('/collect/options/strategy-types'),
    getTaskStatuses: () =>
      apiClient.get('/collect/options/task-statuses'),
    getDataTypes: () =>
      apiClient.get('/collect/options/data-types'),
  },

  // Data Version Management
  dataVersion: {
    // Versions
    listVersions: (params?: { is_published?: boolean; page?: number; page_size?: number }) =>
      apiClient.get('/data-version/versions', { params }),
    getActiveVersion: () =>
      apiClient.get('/data-version/versions/active'),
    getVersion: (versionId: number) =>
      apiClient.get(`/data-version/versions/${versionId}`),
    createVersion: (data: { version_code: string; version_name: string; version_type?: string; base_version_id?: number; source_task_id?: number; description?: string }) =>
      apiClient.post('/data-version/versions', data),
    publishVersion: (versionId: number, notes?: string) =>
      apiClient.post(`/data-version/versions/${versionId}/publish`, { notes }),
    // Publish Records
    listPublishRecords: (versionId?: number) =>
      apiClient.get('/data-version/publish-records', { params: { version_id: versionId } }),
    // Corrections
    listCorrections: (params?: { target_type?: string; status?: string; page?: number; page_size?: number }) =>
      apiClient.get('/data-version/corrections', { params }),
    createCorrection: (data: { target_type: string; target_id: number; field_name: string; original_value?: string; corrected_value?: string; correction_type?: string; reason?: string; source?: string }) =>
      apiClient.post('/data-version/corrections', data),
    revertCorrection: (correctionId: number) =>
      apiClient.post(`/data-version/corrections/${correctionId}/revert`),
    // Quality
    getQualitySummary: (versionId?: number) =>
      apiClient.get('/data-version/quality/summary', { params: { version_id: versionId } }),
    getQualityMetrics: () =>
      apiClient.get('/data-version/quality/metrics'),
  },
}
