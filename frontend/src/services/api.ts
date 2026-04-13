/**
 * API client for backend communication
 */
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'

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
    // Don't redirect on cancelled requests
    if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
      return Promise.reject(error)
    }
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// ============================================
// AbortController Utilities for Request Cancellation
// ============================================

/**
 * Creates a cancellable request wrapper
 * Usage:
 *   const { request, cancel } = createCancellableRequest(
 *     (signal) => api.talents.list({ ...params }, { signal })
 *   )
 *   useEffect(() => {
 *     request().then(setData).catch(handleError)
 *     return () => cancel()
 *   }, [])
 */
export function createCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>
): {
  request: () => Promise<T>
  cancel: () => void
} {
  const controller = new AbortController()

  return {
    request: () => requestFn(controller.signal),
    cancel: () => controller.abort(),
  }
}

/**
 * Extended config with signal support
 */
export interface CancellableRequestConfig extends AxiosRequestConfig {
  signal?: AbortSignal
}

/**
 * Helper to check if an error is a cancellation error
 */
export function isCancellationError(error: unknown): boolean {
  if (error && typeof error === 'object') {
    const axiosError = error as { name?: string; code?: string }
    return axiosError.name === 'AbortError' || axiosError.code === 'ERR_CANCELED'
  }
  return false
}

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
    list: (params?: { country_code?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/schools', { params }),
    get: (id: number) => apiClient.get(`/schools/${id}`),
    getTalents: (id: number, params?: { role_type?: string; page?: number }) =>
      apiClient.get(`/schools/${id}/talents`, { params }),
  },

  // Talents
  talents: {
    list: (params?: { school_id?: number; country_code?: string; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
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
    // CR-03: Collaboration sync
    syncCollaborations: (talentId?: number) =>
      apiClient.post('/talents/collaborations/sync', null, { params: { talent_id: talentId } }),
    getCollaborationSyncStatus: () =>
      apiClient.get('/talents/collaborations/status'),
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
    getOverallStats: () =>
      apiClient.get('/tech-elements/overall-stats'),
    getOverallCountries: () =>
      apiClient.get('/tech-elements/overall-countries'),
    getOverallSchools: (params?: { page?: number; page_size?: number }) =>
      apiClient.get('/tech-elements/overall-schools', { params }),
    getOverallTalents: (params?: { country_code?: string; school_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/tech-elements/overall-talents', { params }),
    getStats: (id: number) =>
      apiClient.get(`/tech-elements/${id}/stats`),
    getCountries: (id: number, directionId?: number) =>
      apiClient.get(`/tech-elements/${id}/countries`, { params: { direction_id: directionId } }),
    getSchools: (id: number, params?: { direction_id?: number; country_code?: string; page?: number; page_size?: number }) =>
      apiClient.get(`/tech-elements/${id}/schools`, { params }),
    getTalents: (id: number, params?: { direction_id?: number; country_code?: string; school_id?: number; role_type?: string; keyword?: string; page?: number; page_size?: number }) =>
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

  // Collect Configuration - Simplified for MVP v1.1
  collect: {
    // Tech Elements with Collect Config
    listTechElements: () =>
      apiClient.get('/collect/tech-elements'),
    updateTechElementSources: (techElementId: number, data: { collect_sources: Array<{ id: string; name: string; type: string }> }) =>
      apiClient.put(`/collect/tech-elements/${techElementId}/sources`, data),
    // Tasks
    listTasks: (params?: { status?: string; tech_element_id?: number; page?: number; page_size?: number }) =>
      apiClient.get('/collect/tasks', { params }),
    getTask: (taskId: number) =>
      apiClient.get(`/collect/tasks/${taskId}`),
    triggerTask: (data: { tech_element_id: number; start_year?: number; end_year?: number | null }) =>
      apiClient.post('/collect/tasks', data),
    cancelTask: (taskId: number) =>
      apiClient.post(`/collect/tasks/${taskId}/cancel`),
    deleteTask: (taskId: number) =>
      apiClient.delete(`/collect/tasks/${taskId}`),
    getActiveTasks: () =>
      apiClient.get('/collect/tasks/active'),
    // Options
    getTaskStatuses: () =>
      apiClient.get('/collect/options/task-statuses'),
    getYearOptions: () =>
      apiClient.get('/collect/options/years'),
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

  // Venue Management - 顶会顶刊配置
  venues: {
    // 获取所有顶会顶刊列表
    list: (params?: { venue_type?: string; is_enabled?: boolean; keyword?: string; page?: number; page_size?: number }) =>
      apiClient.get('/venues', { params }),
    // 获取单个 Venue 详情
    get: (venueId: number) =>
      apiClient.get(`/venues/${venueId}`),
    // 获取技术要素的已绑定 Venue
    getTechElementBindings: (techElementId: number, isEnabled?: boolean) =>
      apiClient.get(`/venues/tech-elements/${techElementId}/bindings`, { params: { is_enabled: isEnabled } }),
    // 批量创建绑定
    batchCreateBindings: (techElementId: number, venueIds: number[]) =>
      apiClient.post('/venues/bindings/batch', { tech_element_id: techElementId, venue_ids: venueIds }),
    // 删除绑定
    deleteBinding: (bindingId: number) =>
      apiClient.delete(`/venues/bindings/${bindingId}`),
    // 批量更新绑定的启用状态
    updateBindings: (techElementId: number, venueIds: number[]) =>
      apiClient.post('/venues/bindings/batch', { tech_element_id: techElementId, venue_ids: venueIds }),
  },

  // Homepage - 首页聚合数据
  homepage: {
    // 获取首页热点数据
    getHighlights: () =>
      apiClient.get('/homepage/highlights'),
  },

  // v1.4 Enhanced Search - 增强搜索
  enhancedSearch: {
    // 增强搜索（支持多模式）
    search: (params: {
      q: string
      mode?: 'keyword' | 'fulltext' | 'semantic' | 'hybrid'
      fuzzy?: boolean
      role_type?: string
      school_id?: number
      min_citations?: number
      page?: number
      page_size?: number
    }) => apiClient.get('/search/v2/talents', { params }),
  },

  // v1.4 JD Match - 岗位匹配
  jdMatch: {
    // 解析JD文本
    parse: (jdText: string) =>
      apiClient.post('/jd-match/parse', { jd_text: jdText }),
    // 匹配人才
    match: (data: {
      jd_text: string
      config?: {
        weights?: { skill?: number; research?: number; experience?: number; education?: number }
        filters?: Record<string, unknown>
        limit?: number
      }
    }) => apiClient.post('/jd-match/match', data),
    // 获取匹配会话
    getSession: (sessionId: number) =>
      apiClient.get(`/jd-match/sessions/${sessionId}`),
  },

  // v1.4 Recommend - 智能推荐
  recommend: {
    // 获取相似人才推荐
    getRecommendations: (data: {
      reference_talent_ids: number[]
      limit?: number
      filters?: Record<string, unknown>
    }) => apiClient.post('/recommend/talents', data),
    // 获取相似人才（快捷接口）
    getSimilar: (talentId: number, limit?: number) =>
      apiClient.get(`/recommend/talents/${talentId}/similar`, { params: { limit } }),
  },

  // v1.4 System Config - 系统配置
  systemConfig: {
    // 获取所有配置
    list: () =>
      apiClient.get('/system-config'),
    // 获取 LLM 配置
    getLLMConfig: () =>
      apiClient.get('/system-config/llm'),
    // 更新 LLM 配置
    updateLLMConfig: (data: {
      enabled?: boolean
      provider?: string
      api_key?: string
      api_base?: string
      model?: string
      embedding_model?: string
      embedding_api_base?: string
      timeout?: number
    }) => apiClient.put('/system-config/llm', data),
    // 更新单个配置
    updateConfig: (key: string, value: string | number | boolean) =>
      apiClient.put(`/system-config/${key}`, { value }),
    // 测试 LLM 连接
    testLLM: (data?: { provider?: string; api_key?: string; api_base?: string }) =>
      apiClient.post('/system-config/test-llm', data || {}),
  },

  // v1.4 Embeddings - 向量嵌入
  embeddings: {
    // 获取嵌入状态
    getStatus: () =>
      apiClient.get('/embeddings/status'),
    // 获取生成进度
    getProgress: () =>
      apiClient.get('/embeddings/progress'),
    // 触发生成
    generate: (force?: boolean, batchSize?: number) =>
      apiClient.post('/embeddings/generate', null, { params: { force, batch_size: batchSize } }),
    // 取消生成
    cancel: () =>
      apiClient.post('/embeddings/cancel'),
  },
}
