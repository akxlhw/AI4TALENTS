/**
 * Favorites state management using Zustand.
 *
 * Replaces the previous Context API implementation to avoid
 * unnecessary re-renders of all consumers on any state change.
 */

import { create } from 'zustand'
import { message } from 'antd'
import { api } from '../services/api'
import type { FavoriteTalent } from '../types'
import { logger } from '../utils/logger'

interface FavoritesState {
  favoriteIds: Set<number>
  favorites: FavoriteTalent[]
  loading: boolean
  isFavorited: (talentId: number) => boolean
  addFavorite: (talentId: number, notes?: string) => Promise<void>
  removeFavorite: (talentId: number) => Promise<void>
  updateNotes: (talentId: number, notes: string) => Promise<void>
  refreshFavorites: () => Promise<void>
  reset: () => void
}

export const useFavoritesStore = create<FavoritesState>()((set, get) => ({
  favoriteIds: new Set(),
  favorites: [],
  loading: true,

  isFavorited: (talentId: number) => get().favoriteIds.has(talentId),

  refreshFavorites: async () => {
    try {
      const [idsResponse, listResponse] = await Promise.all([
        api.favorites.getIds(),
        api.favorites.list({ page: 1, page_size: 100 }),
      ])
      set({
        favoriteIds: new Set(idsResponse.data),
        favorites: listResponse.data.items || [],
      })
    } catch (err) {
      logger.error('Failed to load favorites:', err)
      message.error('收藏状态加载失败，收藏标记可能不准确')
    } finally {
      set({ loading: false })
    }
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
        const newSet = new Set(state.favoriteIds)
        newSet.delete(talentId)
        return {
          favoriteIds: newSet,
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

  reset: () => set({ favoriteIds: new Set(), favorites: [], loading: false }),
}))
