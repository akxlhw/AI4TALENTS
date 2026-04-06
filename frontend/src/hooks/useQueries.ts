/**
 * React Query hooks for API calls.
 *
 * These hooks provide:
 * - Automatic caching with configurable stale times
 * - Request deduplication
 * - Background refetching
 * - Error handling
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { queryKeys, staleTimes } from './queryClient'

// ============================================
// Homepage Queries
// ============================================

/**
 * Get homepage highlights (hot tech elements, top countries, top schools).
 * Cached for 5 minutes.
 */
export function useHomepageHighlights() {
  return useQuery({
    queryKey: queryKeys.homepage.highlights,
    queryFn: async () => {
      const response = await api.homepage.getHighlights()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get overview statistics.
 * Cached for 5 minutes.
 */
export function useOverviewStats() {
  return useQuery({
    queryKey: queryKeys.homepage.overview,
    queryFn: async () => {
      const response = await api.overview.get()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

// ============================================
// Tech Element Queries
// ============================================

/**
 * Get all tech elements list.
 * Cached for 30 minutes (static config data).
 */
export function useTechElements() {
  return useQuery({
    queryKey: queryKeys.techElements.list,
    queryFn: async () => {
      const response = await api.techElements.list()
      return response.data
    },
    staleTime: staleTimes.static,
  })
}

/**
 * Get tech element detail.
 * Cached for 30 minutes.
 */
export function useTechElement(id: number) {
  return useQuery({
    queryKey: queryKeys.techElements.detail(id),
    queryFn: async () => {
      const response = await api.techElements.get(id)
      return response.data
    },
    staleTime: staleTimes.static,
    enabled: !!id,
  })
}

/**
 * Get tech element stats.
 * Cached for 5 minutes.
 */
export function useTechElementStats(elementId?: number) {
  return useQuery({
    queryKey: queryKeys.techElements.stats(elementId),
    queryFn: async () => {
      if (elementId) {
        const response = await api.techElements.getStats(elementId)
        return response.data
      } else {
        const response = await api.techElements.getOverallStats()
        return response.data
      }
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get overall tech element stats.
 * Cached for 5 minutes.
 */
export function useOverallTechElementStats() {
  return useQuery({
    queryKey: queryKeys.techElements.overallStats,
    queryFn: async () => {
      const response = await api.techElements.getOverallStats()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get country distribution for tech element.
 * Cached for 10 minutes.
 */
export function useTechElementCountries(elementId?: number, directionId?: number) {
  return useQuery({
    queryKey: queryKeys.techElements.countries(elementId, directionId),
    queryFn: async () => {
      if (elementId) {
        const response = await api.techElements.getCountries(elementId, directionId)
        return response.data
      } else {
        const response = await api.techElements.getOverallCountries()
        return response.data
      }
    },
    staleTime: staleTimes.detail,
  })
}

/**
 * Get school distribution for tech element.
 * Cached for 5 minutes.
 */
export function useTechElementSchools(
  elementId: number,
  params?: { direction_id?: number; country_code?: string; page?: number; page_size?: number }
) {
  return useQuery({
    queryKey: queryKeys.techElements.schools(elementId, params),
    queryFn: async () => {
      const response = await api.techElements.getSchools(elementId, params)
      return response.data
    },
    staleTime: staleTimes.list,
    enabled: !!elementId,
  })
}

/**
 * Get talent list for tech element.
 * Cached for 3 minutes.
 */
export function useTechElementTalents(
  elementId: number,
  params?: {
    direction_id?: number
    country_code?: string
    school_id?: number
    role_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }
) {
  return useQuery({
    queryKey: queryKeys.techElements.talents(elementId, params),
    queryFn: async () => {
      const response = await api.techElements.getTalents(elementId, params)
      return response.data
    },
    staleTime: staleTimes.list,
    enabled: !!elementId,
  })
}

/**
 * Get overall talents list.
 * Cached for 3 minutes.
 */
export function useOverallTalents(params?: {
  country_code?: string
  school_id?: number
  role_type?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: queryKeys.techElements.overallTalents(params),
    queryFn: async () => {
      const response = await api.techElements.getOverallTalents(params)
      return response.data
    },
    staleTime: staleTimes.list,
  })
}

// ============================================
// Talent Queries
// ============================================

/**
 * Get talent detail.
 * Cached for 10 minutes.
 */
export function useTalent(id: number) {
  return useQuery({
    queryKey: queryKeys.talents.detail(id),
    queryFn: async () => {
      const response = await api.talents.get(id)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!id,
  })
}

/**
 * Get talent works.
 * Cached for 10 minutes.
 */
export function useTalentWorks(id: number, limit?: number) {
  return useQuery({
    queryKey: queryKeys.talents.works(id),
    queryFn: async () => {
      const response = await api.talents.getWorks(id, limit)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!id,
  })
}

/**
 * Get talent collaborations.
 * Cached for 10 minutes.
 */
export function useTalentCollaborations(id: number, limit?: number) {
  return useQuery({
    queryKey: queryKeys.talents.collaborations(id),
    queryFn: async () => {
      const response = await api.talents.getCollaborations(id, limit)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!id,
  })
}

/**
 * Get talent list.
 * Cached for 3 minutes.
 */
export function useTalents(params?: {
  school_id?: number
  country_code?: string
  role_type?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: queryKeys.talents.list(params),
    queryFn: async () => {
      const response = await api.talents.list(params)
      return response.data
    },
    staleTime: staleTimes.list,
  })
}

// ============================================
// School Queries
// ============================================

/**
 * Get school detail.
 * Cached for 30 minutes.
 */
export function useSchool(id: number) {
  return useQuery({
    queryKey: queryKeys.schools.detail(id),
    queryFn: async () => {
      const response = await api.schools.get(id)
      return response.data
    },
    staleTime: staleTimes.static,
    enabled: !!id,
  })
}

/**
 * Get school talents.
 * Cached for 3 minutes.
 */
export function useSchoolTalents(
  id: number,
  params?: { role_type?: string; page?: number }
) {
  return useQuery({
    queryKey: queryKeys.schools.talents(id, params),
    queryFn: async () => {
      const response = await api.schools.getTalents(id, params)
      return response.data
    },
    staleTime: staleTimes.list,
    enabled: !!id,
  })
}

/**
 * Get schools list.
 * Cached for 30 minutes.
 */
export function useSchools(params?: {
  country_code?: string
  keyword?: string
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: queryKeys.schools.list(params),
    queryFn: async () => {
      const response = await api.schools.list(params)
      return response.data
    },
    staleTime: staleTimes.static,
  })
}

// ============================================
// Favorites Queries
// ============================================

/**
 * Get favorites list.
 * Cached for 3 minutes.
 */
export function useFavorites(params?: {
  page?: number
  page_size?: number
  role_type?: string
  keyword?: string
}) {
  return useQuery({
    queryKey: queryKeys.favorites.list(params),
    queryFn: async () => {
      const response = await api.favorites.list(params)
      return response.data
    },
    staleTime: staleTimes.list,
  })
}

/**
 * Get favorite IDs for quick check.
 * Cached for 5 minutes.
 */
export function useFavoriteIds() {
  return useQuery({
    queryKey: queryKeys.favorites.ids,
    queryFn: async () => {
      const response = await api.favorites.getIds()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Check if talent is favorited.
 */
export function useFavoriteCheck(talentId: number) {
  return useQuery({
    queryKey: queryKeys.favorites.check(talentId),
    queryFn: async () => {
      const response = await api.favorites.check(talentId)
      return response.data
    },
    staleTime: staleTimes.stats,
    enabled: !!talentId,
  })
}

// ============================================
// Favorites Mutations
// ============================================

/**
 * Add to favorites mutation.
 */
export function useAddFavorite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ talentId, notes }: { talentId: number; notes?: string }) =>
      api.favorites.add(talentId, notes),
    onSuccess: () => {
      // Invalidate favorites queries to refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.favorites.all })
    },
  })
}

/**
 * Remove from favorites mutation.
 */
export function useRemoveFavorite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (talentId: number) => api.favorites.remove(talentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.favorites.all })
    },
  })
}

// ============================================
// Collect Queries
// ============================================

/**
 * Get collect tech elements with config.
 * Cached for 30 minutes.
 */
export function useCollectTechElements() {
  return useQuery({
    queryKey: queryKeys.collect.techElements,
    queryFn: async () => {
      const response = await api.collect.listTechElements()
      return response.data
    },
    staleTime: staleTimes.static,
  })
}

/**
 * Get collect tasks.
 * Cached for 30 seconds (near real-time).
 */
export function useCollectTasks(params?: {
  status?: string
  tech_element_id?: number
  page?: number
  page_size?: number
}) {
  return useQuery({
    queryKey: queryKeys.collect.tasks(params),
    queryFn: async () => {
      const response = await api.collect.listTasks(params)
      return response.data
    },
    staleTime: staleTimes.realtime,
  })
}

/**
 * Get active collect tasks.
 * Cached for 30 seconds.
 */
export function useActiveCollectTasks() {
  return useQuery({
    queryKey: queryKeys.collect.activeTasks,
    queryFn: async () => {
      const response = await api.collect.getActiveTasks()
      return response.data
    },
    staleTime: staleTimes.realtime,
    // Refetch every 5 seconds for active tasks
    refetchInterval: 5 * 1000,
  })
}
