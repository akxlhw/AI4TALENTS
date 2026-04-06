import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { message } from 'antd'
import { api } from '../services/api'
import type { FavoriteTalent } from '../types'

interface FavoritesContextType {
  favoriteIds: Set<number>
  favorites: FavoriteTalent[]
  loading: boolean
  isFavorited: (talentId: number) => boolean
  addFavorite: (talentId: number, notes?: string) => Promise<void>
  removeFavorite: (talentId: number) => Promise<void>
  updateNotes: (talentId: number, notes: string) => Promise<void>
  refreshFavorites: () => Promise<void>
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined)

export const FavoritesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set())
  const [favorites, setFavorites] = useState<FavoriteTalent[]>([])
  const [loading, setLoading] = useState(true)

  const refreshFavorites = useCallback(async () => {
    try {
      const [idsResponse, listResponse] = await Promise.all([
        api.favorites.getIds(),
        api.favorites.list({ page: 1, page_size: 100 }),
      ])
      setFavoriteIds(new Set(idsResponse.data))
      setFavorites(listResponse.data.items || [])
    } catch (err) {
      console.error('Failed to load favorites:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load favorites on mount
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      refreshFavorites()
    } else {
      setLoading(false)
    }
  }, [refreshFavorites])

  const isFavorited = useCallback((talentId: number) => {
    return favoriteIds.has(talentId)
  }, [favoriteIds])

  const addFavorite = useCallback(async (talentId: number, notes?: string) => {
    try {
      const response = await api.favorites.add(talentId, notes)
      setFavoriteIds(prev => new Set(prev).add(talentId))
      setFavorites(prev => [response.data, ...prev])
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
  }, [])

  const removeFavorite = useCallback(async (talentId: number) => {
    try {
      await api.favorites.remove(talentId)
      setFavoriteIds(prev => {
        const newSet = new Set(prev)
        newSet.delete(talentId)
        return newSet
      })
      setFavorites(prev => prev.filter(f => f.talent_id !== talentId))
      message.success('已取消收藏')
    } catch {
      message.error('取消收藏失败')
      throw new Error('取消收藏失败')
    }
  }, [])

  const updateNotes = useCallback(async (talentId: number, notes: string) => {
    try {
      await api.favorites.update(talentId, notes)
      setFavorites(prev => prev.map(f =>
        f.talent_id === talentId ? { ...f, notes } : f
      ))
      message.success('备注已更新')
    } catch {
      message.error('更新备注失败')
      throw new Error('更新备注失败')
    }
  }, [])

  const value: FavoritesContextType = {
    favoriteIds,
    favorites,
    loading,
    isFavorited,
    addFavorite,
    removeFavorite,
    updateNotes,
    refreshFavorites,
  }

  return (
    <FavoritesContext.Provider value={value}>
      {children}
    </FavoritesContext.Provider>
  )
}

export const useFavorites = (): FavoritesContextType => {
  const context = useContext(FavoritesContext)
  if (context === undefined) {
    throw new Error('useFavorites must be used within a FavoritesProvider')
  }
  return context
}

export default FavoritesContext
