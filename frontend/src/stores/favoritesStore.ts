/**
 * Favorites state management using Zustand.
 *
 * Replaces the previous Context API implementation to avoid
 * unnecessary re-renders of all consumers on any state change.
 */

import { create } from 'zustand'
import { message } from 'antd'
import { api } from '../services/api'
import { i18n } from '../i18n'
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
      message.error(i18n.t('favorites.loadFailed', { ns: 'common' }))
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
      message.success(i18n.t('favorites.added', { ns: 'common' }))
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message.warning(axiosError.response.data.detail)
      } else {
        message.error(i18n.t('favorites.addFailed', { ns: 'common' }))
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
      message.success(i18n.t('favorites.removed', { ns: 'common' }))
    } catch {
      const msg = i18n.t('favorites.removeFailed', { ns: 'common' })
      message.error(msg)
      throw new Error(msg)
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
      message.success(i18n.t('favorites.notesUpdated', { ns: 'common' }))
    } catch {
      const msg = i18n.t('favorites.updateFailed', { ns: 'common' })
      message.error(msg)
      throw new Error(msg)
    }
  },

  reset: () => set({ favoriteIds: new Set(), favorites: [], loading: false }),
}))
