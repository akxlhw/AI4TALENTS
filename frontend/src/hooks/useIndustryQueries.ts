import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { AxiosError } from 'axios'
import { api, apiClient } from '../services/api'
import type { CandidateStatusPatch, IndustryTalentSearchParams } from '../services/api/industry'
import { queryKeys, staleTimes } from './queryClient'

/**
 * Get industry positions with candidate aggregates.
 * Pass a status ('open'/'closed'/'archived') to filter; omit for all.
 */
export function useIndustryPositions(status?: string) {
  return useQuery({
    queryKey: queryKeys.industry.positions(status),
    queryFn: async () => {
      const response = await api.industry.listPositions(status)
      return response.data
    },
    staleTime: staleTimes.list,
  })
}

/**
 * Get industry talent list with filtering and pagination.
 * Keeps previous data while fetching a new page/filter combination.
 */
export function useIndustryTalents(params?: IndustryTalentSearchParams) {
  return useQuery({
    queryKey: queryKeys.industry.talents(params),
    queryFn: async () => {
      const response = await api.industry.listTalents(params)
      return response.data
    },
    staleTime: staleTimes.list,
    placeholderData: previousData => previousData,
  })
}

/**
 * Get industry talent detail (profile + per-position match comparison).
 * Skips retry on 404.
 */
export function useIndustryTalent(id?: number) {
  const effectiveId = id ?? -1
  return useQuery({
    queryKey: queryKeys.industry.talent(effectiveId),
    queryFn: async () => {
      const response = await api.industry.getTalent(id!)
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
 * Update recruiting state (status/touched/notes) of a candidate under a
 * position. Invalidates industry queries so list/detail stay consistent.
 */
export function useUpdateCandidateStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (vars: {
      talentId: number
      positionId: number
      patch: CandidateStatusPatch
    }) => {
      const response = await api.industry.patchCandidateStatus(
        vars.talentId,
        vars.positionId,
        vars.patch
      )
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
    },
  })
}

/**
 * Remove a talent from a position (delete the link). Invalidates industry
 * queries so list/detail stay consistent.
 */
export function useRemoveFromPosition() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (vars: { talentId: number; positionId: number }) => {
      const response = await api.industry.removeFromPosition(vars.talentId, vars.positionId)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.industry.all })
    },
  })
}

// ---- Tech directions (core_tech_direction via /tech-domains, academic) ----

export interface TechDirectionOption {
  code: string
  name: string
  nameEn: string | null
  domainName: string
}

interface TechDomainListResponse {
  items: {
    tech_domain_id: number
    domain_code: string
    domain_name: string
    directions: {
      tech_direction_id: number
      direction_code: string
      direction_name: string
      direction_name_en: string | null
    }[]
  }[]
}

/**
 * Flattened tech-direction options sourced from core_tech_direction
 * (used by position forms and the talent-list tech-direction filter).
 * Cached as static data.
 */
export function useTechDirectionOptions() {
  return useQuery({
    queryKey: queryKeys.industry.techDirections,
    queryFn: async (): Promise<TechDirectionOption[]> => {
      const response = await apiClient.get<TechDomainListResponse>('/tech-domains')
      return response.data.items.flatMap(d =>
        d.directions.map(dir => ({
          code: dir.direction_code,
          name: dir.direction_name,
          nameEn: dir.direction_name_en,
          domainName: d.domain_name,
        }))
      )
    },
    staleTime: staleTimes.static,
  })
}
