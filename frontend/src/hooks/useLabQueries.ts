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
