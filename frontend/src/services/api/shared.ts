import { apiClient } from './client'

export const sharedApi = {
  health: {
    check: () => apiClient.get('/health'),
    ready: () => apiClient.get('/health/ready'),
    live: () => apiClient.get('/health/live'),
  },

  auth: {
    login: (username: string, password: string) =>
      apiClient.post('/auth/login', { username, password }),
    logout: () => apiClient.post('/auth/logout'),
    register: (data: { username: string; email: string; password: string; employee_id: string; display_name?: string; privacy_policy_accepted: boolean; terms_of_use_accepted: boolean; storage_consent_level?: string }) =>
      apiClient.post('/auth/register', data),
    refresh: (refreshToken: string) =>
      apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
    me: () => apiClient.get('/auth/me'),
    changePassword: (currentPassword: string, newPassword: string) =>
      apiClient.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      }),
  },

  overview: {
    get: () => apiClient.get('/overview'),
  },

  countries: {
    list: () => apiClient.get('/countries'),
  },

  privacy: {
    getPolicy: () => apiClient.get('/privacy/policy'),
    getTerms: () => apiClient.get('/privacy/terms'),
    getConsentStatus: () => apiClient.get('/privacy/consent-status'),
    updateConsent: (data: {
      policy_version: string
      terms_version: string
      storage_consent_level: string
      accepted: boolean
    }) => apiClient.post('/privacy/consent', data),
  },

  admin: {
    listUsers: (params?: { role?: string; is_active?: boolean; page?: number; page_size?: number }) =>
      apiClient.get('/users', { params }),
    createUser: (data: { username: string; email: string; password: string; role?: string; display_name?: string; employee_id?: string }) =>
      apiClient.post('/users', data),
    getUser: (userId: number) =>
      apiClient.get(`/users/${userId}`),
    updateUser: (userId: number, data: { display_name?: string; department?: string; role?: string; is_active?: boolean }) =>
      apiClient.put(`/users/${userId}`, data),
    deactivateUser: (userId: number) =>
      apiClient.delete(`/users/${userId}`),
    approveUser: (userId: number) =>
      apiClient.post(`/users/${userId}/approve`),
    rejectUser: (userId: number) =>
      apiClient.post(`/users/${userId}/reject`),
    getUserScopes: (userId: number) =>
      apiClient.get(`/users/${userId}/scopes`),
    addUserScope: (userId: number, data: { scope_type: string; scope_value: string; expires_at?: string; notes?: string }) =>
      apiClient.post(`/users/${userId}/scopes`, { user_id: userId, ...data }),
    removeUserScope: (userId: number, scopeId: number) =>
      apiClient.delete(`/users/${userId}/scopes/${scopeId}`),
    listAuditLogs: (params?: { start_time?: string; end_time?: string; user_id?: number; event_type?: string; resource_type?: string; page?: number; page_size?: number }) =>
      apiClient.get('/audit/logs', { params }),
    getMyAccessibleSchools: () =>
      apiClient.get('/users/me/scopes/schools'),
    checkSchoolAccess: (schoolId: number) =>
      apiClient.get(`/users/me/scopes/check/${schoolId}`),
    getAccessibleTechDomains: () =>
      apiClient.get('/users/me/scopes/tech-domains'),
    getAccessibleCountries: () =>
      apiClient.get('/users/me/scopes/countries'),
    getDefaultView: () =>
      apiClient.get('/users/me/default-view'),
    updateDefaultView: (defaultView: 'tech_domain' | 'country_school') =>
      apiClient.put('/users/me/default-view', { default_view: defaultView }),
  },

  systemConfig: {
    list: () =>
      apiClient.get('/system-config'),
    getLLMConfig: () =>
      apiClient.get('/system-config/llm'),
    updateLLMConfig: (data: {
      enabled?: boolean
      provider?: string
      api_key?: string
      api_base?: string
      model?: string
      embedding_model?: string
      embedding_api_base?: string
      embedding_api_key?: string
      timeout?: number
    }) => apiClient.put('/system-config/llm', data),
    getProxyConfig: () =>
      apiClient.get('/system-config/proxy'),
    updateProxyConfig: (data: {
      enabled?: boolean
      url?: string
      username?: string
      password?: string
      no_proxy?: string
      ssl_verify?: boolean
    }) => apiClient.put('/system-config/proxy', data),
    testProxy: (data?: { url?: string; username?: string; password?: string }) =>
      apiClient.post('/system-config/test-proxy', data || {}),
    getGitHubConfig: () =>
      apiClient.get('/system-config/github'),
    updateGitHubConfig: (data: {
      tokens?: string
      base_url?: string
      rate_limit?: number
    }) => apiClient.put('/system-config/github', data),
    testGitHub: () =>
      apiClient.post('/system-config/github/test'),
    updateConfig: (key: string, value: string | number | boolean) =>
      apiClient.put(`/system-config/${key}`, { value }),
    testLLM: (data?: { api_format?: string; api_key?: string; api_base?: string; model?: string }) =>
      apiClient.post('/system-config/test-llm', data || {}),
    testEmbedding: (data?: { api_format?: string; api_key?: string; api_base?: string; embedding_model?: string }) =>
      apiClient.post('/system-config/test-embedding', data || {}),
  },
}
