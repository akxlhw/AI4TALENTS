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
    list: (params?: { school_id?: number; role_type?: string; page?: number }) =>
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
}
