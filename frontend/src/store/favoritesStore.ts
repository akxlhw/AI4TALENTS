/**
 * Favorites Store
 *
 * Zustand store for favorites state management.
 * Replaces FavoritesContext with a simpler, more performant solution.
 */

import { create } from 'zustand'
import { message } from 'antd'
import { api } from '../services/api'
import type { FavoriteTalent } from '../types'

interface FavoritesState {
  favoriteIds: Set<number>
  favorites: FavoriteTalent[]
  loading: boolean

  // Actions
  isFavorited: (talentId: number) => boolean
  addFavorite: (talentId: number, notes?: string) => Promise<void>
  removeFavorite: (talentId: number) => Promise<void>
  updateNotes: (talentId: number, notes: string) => Promise<void>
  refreshFavorites: () => Promise<void>
}

export const useFavoritesStore = create<FavoritesState>((set, get) => ({
  favoriteIds: new Set(),
  favorites: [],
  loading: true,

  isFavorited: (talentId: number) => {
    return get().favoriteIds.has(talentId)
  },

  addFavorite: async (talentId: number, notes?: string) => {
    try {
      const response = await api.favorites.add(talentId, notes)
      set((state) => ({
        favoriteIds: new Set(state.favoriteIds).add(talentId),
        favorites: [response.data, ...state.favorites],
      }))
      message.success('已添加到收藏')
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message.warning(axiosError.response.data.detail)
      } else {
        message.error('添加收藏失败')
      }
      throw err
    }
  },

  removeFavorite: async (talentId: number) => {
    try {
      await api.favorites.remove(talentId)
      set((state) => {
        const newIds = new Set(state.favoriteIds)
        newIds.delete(talentId)
        return {
          favoriteIds: newIds,
          favorites: state.favorites.filter((f) => f.talent_id !== talentId),
        }
      })
      message.success('已取消收藏')
    } catch {
      message.error('取消收藏失败')
      throw new Error('取消收藏失败')
    }
  },

  updateNotes: async (talentId: number, notes: string) => {
    try {
      await api.favorites.update(talentId, notes)
      set((state) => ({
        favorites: state.favorites.map((f) =>
          f.talent_id === talentId ? { ...f, notes } : f
        ),
      }))
      message.success('备注已更新')
    } catch {
      message.error('更新备注失败')
      throw new Error('更新备注失败')
    }
  },

  refreshFavorites: async () => {
    try {
      const [idsResponse, listResponse] = await Promise.all([
        api.favorites.getIds(),
        api.favorites.list({ page: 1, page_size: 100 }),
      ])
      set({
        favoriteIds: new Set(idsResponse.data),
        favorites: listResponse.data.items || [],
        loading: false,
      })
    } catch (err) {
      console.error('Failed to load favorites:', err)
      set({ loading: false })
    }
  },
}))

// Initialize favorites on app load
export const initializeFavorites = async () => {
  const token = localStorage.getItem('token')
  if (token) {
    await useFavoritesStore.getState().refreshFavorites()
  } else {
    useFavoritesStore.setState({ loading: false })
  }
}

export default useFavoritesStore
