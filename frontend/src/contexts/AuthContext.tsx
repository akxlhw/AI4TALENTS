/**
 * AuthContext compatibility layer.
 *
 * Previously used React Context API + useState.
 * Now delegates to Zustand (stores/authStore) for fine-grained subscriptions
 * while keeping the same hook interface for consumers.
 */

import React from 'react'
import { useAuthStore } from '../stores/authStore'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  isSuperAdmin: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  hasRole: (roles: string[]) => boolean
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Provider is now a no-op because Zustand manages state outside React tree.
  // Kept here to avoid breaking existing tree structure.
  return <>{children}</>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const store = useAuthStore()

  return {
    user: store.user,
    loading: store.loading,
    isAuthenticated: !!store.user,
    isAdmin: store.user?.role === 'admin' || store.user?.role === 'super_admin',
    isSuperAdmin: store.user?.role === 'super_admin',
    login: store.login,
    logout: store.logout,
    refreshUser: store.refreshUser,
    hasRole: (roles: string[]) => (store.user ? roles.includes(store.user.role) : false),
  }
}

export default AuthProvider
