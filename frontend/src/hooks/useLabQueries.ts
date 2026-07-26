import { useQuery } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { api } from '../services/api'
import type { LabTalentSearchParams } from '../services/api/lab'
import { queryKeys, staleTimes } from './queryClient'

/**
 * Get lab overview statistics.
 * Cached for 5 minutes.
 */
export function useLabStats() {
  return useQuery({
    queryKey: queryKeys.lab.stats,
    queryFn: async () => {
      const response = await api.lab.getStats()
      return response.data
    },
    staleTime: staleTimes.stats,
  })
}

/**
 * Get parent labs with a preview of their talents.
 * Cached for 3 minutes.
 */
export function useLabList() {
  return useQuery({
    queryKey: queryKeys.lab.labs,
    queryFn: async () => {
      const response = await api.lab.listLabs()
      return response.data
    },
    staleTime: staleTimes.list,
  })
}

/**
 * Get lab talent list with filtering and pagination.
 * Cached for 3 minutes; keeps previous data while fetching new page.
 */
export function useLabTalents(params?: LabTalentSearchParams) {
  return useQuery({
    queryKey: queryKeys.lab.talents(params),
    queryFn: async () => {
      const response = await api.lab.listTalents(params)
      return response.data
    },
    staleTime: staleTimes.list,
    placeholderData: previousData => previousData,
  })
}

/**
 * Get lab talent detail.
 * Cached for 10 minutes; skips retry on 404.
 */
export function useLabTalent(id?: number) {
  const effectiveId = id ?? -1
  return useQuery({
    queryKey: queryKeys.lab.talent(effectiveId),
    queryFn: async () => {
      const response = await api.lab.getTalent(id!)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!id,
    retry: (failureCount, error: AxiosError) => {
      if (error.response?.status === 404) return false
      return failureCount < 1
    },
  })
}

/**
 * Get lab profile (metadata + aggregated stats).
 * Cached for 5 minutes; skips retry on 404.
 */
export function useLabProfile(parentLab?: string) {
  return useQuery({
    queryKey: ['lab', 'profile', parentLab],
    queryFn: async () => {
      const response = await api.lab.getLabProfile(parentLab!)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!parentLab,
    retry: (failureCount, error: AxiosError) => {
      if (error.response?.status === 404) return false
      return failureCount < 1
    },
  })
}

/**
 * Get mentorship data (advisors + supervised students).
 * Cached for 10 minutes.
 */
export function useMentorship(talentId?: number) {
  return useQuery({
    queryKey: ['lab', 'mentorship', talentId],
    queryFn: async () => {
      const response = await api.lab.getMentorship(talentId!)
      return response.data
    },
    staleTime: staleTimes.detail,
    enabled: !!talentId,
  })
}

/**
 * Get cleaned homepage HTML for inline preview.
 * Not cached (always fresh fetch).
 */
export function useHomepagePreview(talentId?: number, enabled = false) {
  return useQuery({
    queryKey: ['lab', 'homepage-preview', talentId],
    queryFn: async () => {
      const response = await api.lab.getHomepagePreview(talentId!)
      return response.data
    },
    enabled: !!talentId && enabled,
    staleTime: 0,
    retry: 0,
  })
}
