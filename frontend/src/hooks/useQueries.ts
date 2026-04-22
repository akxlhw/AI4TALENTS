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
 * Get homepage highlights (hot tech domains, top countries, top schools).
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
// Tech Domain Queries
// ============================================

/**
 * Get all tech domains list.
 * Cached for 30 minutes (static config data).
 */
export function useTechDomains() {
  return useQuery({
    queryKey: queryKeys.techDomains.list,
    queryFn: async () => {
      const response = await api.techDomains.list()
      return response.data
    },
    staleTime: staleTimes.static,
  })
}

/**
 * Get tech domain detail.
 * Cached for 30 minutes.
 */
export function useTechDomain(id: number) {
  return useQuery({
    queryKey: queryKeys.techDomains.detail(id),
    queryFn: async () => {
      const response = await api.techDomains.get(id)
      return response.data
    },
    staleTime: staleTimes.static,
    enabled: !!id,
  })
}

/**
 * Get tech domain stats.
 * Cached for 5 minutes.
 */
export function useTechDomainStats(domainId?: number) {
  return useQuery({
    queryKey: queryKeys.techDomains.stats(domainId),
    queryFn: async () => {
      if (domainId) {
        const response = await api.techDomains.getStats(domainId)
        return response.data
      } else {
        const response = await api.techDomains.getOverallStats()
        return response.data
      }
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get overall tech domain stats.
 * Cached for 5 minutes.
 */
export function useOverallTechDomainStats() {
  return useQuery({
    queryKey: queryKeys.techDomains.overallStats,
    queryFn: async () => {
      const response = await api.techDomains.getOverallStats()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get country distribution for tech domain.
 * Cached for 10 minutes.
 */
export function useTechDomainCountries(domainId?: number, directionId?: number) {
  return useQuery({
    queryKey: queryKeys.techDomains.countries(domainId, directionId),
    queryFn: async () => {
      if (domainId) {
        const response = await api.techDomains.getCountries(domainId, directionId)
        return response.data
      } else {
        const response = await api.techDomains.getOverallCountries()
        return response.data
      }
    },
    staleTime: staleTimes.detail,
  })
}

/**
 * Get school distribution for tech domain.
 * Cached for 5 minutes.
 */
export function useTechDomainSchools(
  domainId: number,
  params?: { direction_id?: number; country_code?: string; page?: number; page_size?: number }
) {
  return useQuery({
    queryKey: queryKeys.techDomains.schools(domainId, params),
    queryFn: async () => {
      const response = await api.techDomains.getSchools(domainId, params)
      return response.data
    },
    staleTime: staleTimes.list,
    enabled: !!domainId,
  })
}

/**
 * Get talent list for tech domain.
 * Cached for 3 minutes.
 */
export function useTechDomainTalents(
  domainId: number,
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
    queryKey: queryKeys.techDomains.talents(domainId, params),
    queryFn: async () => {
      const response = await api.techDomains.getTalents(domainId, params)
      return response.data
    },
    staleTime: staleTimes.list,
    enabled: !!domainId,
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
    queryKey: queryKeys.techDomains.overallTalents(params),
    queryFn: async () => {
      const response = await api.techDomains.getOverallTalents(params)
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
 * Get collect tech domains with config.
 * Cached for 30 minutes.
 */
export function useCollectTechDomains() {
  return useQuery({
    queryKey: queryKeys.collect.techDomains,
    queryFn: async () => {
      const response = await api.collect.listTechDomains()
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
  tech_domain_id?: number
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
