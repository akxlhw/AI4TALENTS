/**
 * Auth Store
 *
 * Zustand store for authentication state management.
 * Replaces AuthContext with a simpler, more performant solution.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { message } from 'antd'
import { api } from '../services/api'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  token: string | null

  // Computed
  isAuthenticated: boolean
  isAdmin: boolean
  isSuperAdmin: boolean

  // Actions
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  hasRole: (roles: string[]) => boolean
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      loading: true,
      token: localStorage.getItem('token'),

      // Computed values
      get isAuthenticated() {
        return !!get().user
      },
      get isAdmin() {
        const user = get().user
        return user?.role === 'admin' || user?.role === 'super_admin'
      },
      get isSuperAdmin() {
        return get().user?.role === 'super_admin'
      },

      // Actions
      login: async (username: string, password: string) => {
        const response = await api.auth.login(username, password)
        const { access_token, refresh_token, user } = response.data

        localStorage.setItem('token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        set({ user, token: access_token, loading: false })
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
          set({ user: null, token: null })
          message.info('已退出登录')
        }
      },

      refreshUser: async () => {
        try {
          const response = await api.auth.me()
          set({ user: response.data })
        } catch (error) {
          console.error('Failed to refresh user:', error)
        }
      },

      hasRole: (roles: string[]) => {
        const user = get().user
        return user ? roles.includes(user.role) : false
      },

      setUser: (user: User | null) => set({ user }),
      setToken: (token: string | null) => set({ token }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token }),
    }
  )
)

// Initialize auth on app load
export const initializeAuth = async () => {
  const token = localStorage.getItem('token')
  if (token) {
    try {
      const response = await api.auth.me()
      useAuthStore.getState().setUser(response.data)
    } catch {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      useAuthStore.getState().setUser(null)
    }
  }
  useAuthStore.setState({ loading: false })
}

export default useAuthStore
