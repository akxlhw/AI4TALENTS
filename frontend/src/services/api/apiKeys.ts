import { apiClient } from './client'

export interface ApiKeyListItem {
  api_key_id: number
  key_name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  rate_limit_per_minute?: number | null
  expires_at?: string | null
  last_used_at?: string | null
  created_at?: string | null
}

export interface ApiKeyCreated {
  api_key_id: number
  key_name: string
  key_prefix: string
  scopes: string[]
  plaintext_key: string
}

export const apiKeysApi = {
  list: () => apiClient.get<ApiKeyListItem[]>('/api-keys'),
  create: (data: { key_name: string; scopes: string[]; rate_limit_per_minute?: number }) =>
    apiClient.post<ApiKeyCreated>('/api-keys', data),
  setActive: (id: number, is_active: boolean) =>
    apiClient.patch<ApiKeyListItem>(`/api-keys/${id}`, { is_active }),
}
