/**
 * Authentication state management using Zustand.
 *
 * Replaces the previous Context API implementation to avoid
 * unnecessary re-renders of all consumers on any state change.
 */

import { create } from 'zustand'
import { message } from 'antd'
import { api } from '../services/api'
import { applyDomainCssVars } from '../theme'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  loading: true,

  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),

  login: async (username: string, password: string) => {
    const response = await api.auth.login(username, password)
    const { access_token, refresh_token, user } = response.data

    localStorage.setItem('token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
    localStorage.setItem('user', JSON.stringify(user))

    set({ user })
    message.success(`欢迎回来，${user.display_name || user.username}！`)
  },

  logout: async () => {
    try {
      await api.auth.logout()
    } catch {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      set({ user: null })
      applyDomainCssVars('academic')
      message.info('已退出登录')
    }
  },

  refreshUser: async () => {
    try {
      const response = await api.auth.me()
      set({ user: response.data })
    } catch (err) {
      console.error('Failed to refresh user:', err)
    }
  },
}))

// Initialize auth state on module load (check existing token)
const token = localStorage.getItem('token')
if (token) {
  api.auth
    .me()
    .then((response) => {
      useAuthStore.getState().setUser(response.data)
    })
    .catch(() => {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    })
    .finally(() => {
      useAuthStore.getState().setLoading(false)
    })
} else {
  useAuthStore.getState().setLoading(false)
}
