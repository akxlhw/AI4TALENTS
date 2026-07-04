/**
 * React Query configuration for frontend caching.
 */
import { QueryClient } from '@tanstack/react-query'

/**
 * Default query client with caching configuration.
 *
 * Cache strategy:
 * - staleTime: Data is fresh for 5 minutes
 * - gcTime: Unused data is garbage collected after 30 minutes
 * - retry: Retry failed requests once
 * - refetchOnWindowFocus: Don't refetch when window regains focus
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Keep unused data in cache for 30 minutes
      gcTime: 30 * 60 * 1000,
      // Retry failed requests once
      retry: 1,
      // Don't refetch when window regains focus
      refetchOnWindowFocus: false,
      // Don't refetch on mount if data is fresh
      refetchOnMount: true,
    },
  },
})

/**
 * Cache key factories for consistent key generation.
 */
export const queryKeys = {
  // Homepage
  homepage: {
    highlights: ['homepage', 'highlights'] as const,
    overview: ['homepage', 'overview'] as const,
  },

  // Tech Domains
  techDomains: {
    all: ['techDomains'] as const,
    list: ['techDomains', 'list'] as const,
    detail: (id: number) => ['techDomains', 'detail', id] as const,
    stats: (id?: number) => ['techDomains', 'stats', id] as const,
    overallStats: ['techDomains', 'overallStats'] as const,
    countries: (domainId?: number, directionId?: number) =>
      ['techDomains', 'countries', domainId, directionId] as const,
    schools: (domainId: number, params?: object) =>
      ['techDomains', 'schools', domainId, params] as const,
    talents: (domainId: number, params?: object) =>
      ['techDomains', 'talents', domainId, params] as const,
    overallTalents: (params?: object) =>
      ['techDomains', 'overallTalents', params] as const,
    overallSchools: (params?: object) =>
      ['techDomains', 'overallSchools', params] as const,
  },

  // Talents
  talents: {
    all: ['talents'] as const,
    list: (params?: object) => ['talents', 'list', params] as const,
    detail: (id: number) => ['talents', 'detail', id] as const,
    works: (id: number) => ['talents', 'works', id] as const,
    collaborations: (id: number) => ['talents', 'collaborations', id] as const,
  },

  // Schools
  schools: {
    all: ['schools'] as const,
    list: (params?: object) => ['schools', 'list', params] as const,
    detail: (id: number) => ['schools', 'detail', id] as const,
    talents: (id: number, params?: object) =>
      ['schools', 'talents', id, params] as const,
  },

  // Favorites
  favorites: {
    all: ['favorites'] as const,
    list: (params?: object) => ['favorites', 'list', params] as const,
    ids: ['favorites', 'ids'] as const,
    check: (talentId: number) => ['favorites', 'check', talentId] as const,
  },

  // Collect
  collect: {
    techDomains: ['collect', 'techDomains'] as const,
    tasks: (params?: object) => ['collect', 'tasks', params] as const,
    task: (id: number) => ['collect', 'task', id] as const,
    activeTasks: ['collect', 'activeTasks'] as const,
  },

  // Lab
  lab: {
    stats: ['lab', 'stats'] as const,
    talents: (params?: object) => ['lab', 'talents', params] as const,
    talent: (id: number) => ['lab', 'talent', id] as const,
  },
}

/**
 * Stale times for different data types.
 */
export const staleTimes = {
  // Static data: fresh for 30 minutes
  static: 30 * 60 * 1000,
  // Statistics: fresh for 5 minutes
  stats: 5 * 60 * 1000,
  // Lists: fresh for 3 minutes
  list: 3 * 60 * 1000,
  // Details: fresh for 10 minutes
  detail: 10 * 60 * 1000,
  // Real-time data: fresh for 30 seconds
  realtime: 30 * 1000,
}
