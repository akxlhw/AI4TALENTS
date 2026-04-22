/**
 * useSearchFilters Hook
 *
 * Unified filter state management for search pages.
 * Reduces multiple useState calls to a single state object.
 */
import { useState, useCallback, useMemo } from 'react'

export interface SearchFilters {
  // Talent filters
  role?: string
  school?: number
  country?: string
  techDomain?: number
  minWorks?: number
  minCitations?: number
  isGraduated?: string
  confirmStatus?: string
}

export interface UseSearchFiltersOptions {
  initialFilters?: SearchFilters
}

export interface UseSearchFiltersReturn {
  filters: SearchFilters
  setFilter: <K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => void
  setFilters: (newFilters: Partial<SearchFilters>) => void
  resetFilters: () => void
  hasActiveFilters: boolean
  activeFilterCount: number
  toApiParams: () => Record<string, unknown>
}

const DEFAULT_FILTERS: SearchFilters = {}

export function useSearchFilters(options: UseSearchFiltersOptions = {}): UseSearchFiltersReturn {
  const { initialFilters = {} } = options

  const [filters, setFiltersState] = useState<SearchFilters>({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  })

  // Set a single filter value
  const setFilter = useCallback(<K extends keyof SearchFilters>(
    key: K,
    value: SearchFilters[K]
  ) => {
    setFiltersState(prev => ({
      ...prev,
      [key]: value,
    }))
  }, [])

  // Set multiple filter values at once
  const setFilters = useCallback((newFilters: Partial<SearchFilters>) => {
    setFiltersState(prev => ({
      ...prev,
      ...newFilters,
    }))
  }, [])

  // Reset all filters to default
  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS)
  }, [])

  // Check if any filter is active
  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some(value => value !== undefined && value !== '')
  }, [filters])

  // Count active filters
  const activeFilterCount = useMemo(() => {
    return Object.values(filters).filter(
      value => value !== undefined && value !== ''
    ).length
  }, [filters])

  // Convert to API parameters
  const toApiParams = useCallback((): Record<string, unknown> => {
    const params: Record<string, unknown> = {}

    if (filters.role) params.role_type = filters.role
    if (filters.school) params.school_id = filters.school
    if (filters.country) params.country_code = filters.country
    if (filters.techDomain) params.tech_domain_id = filters.techDomain
    if (filters.minWorks !== undefined) params.min_works = filters.minWorks
    if (filters.minCitations !== undefined) params.min_citations = filters.minCitations
    if (filters.isGraduated) params.is_graduated = filters.isGraduated
    if (filters.confirmStatus) params.confirm_status = filters.confirmStatus

    return params
  }, [filters])

  return {
    filters,
    setFilter,
    setFilters,
    resetFilters,
    hasActiveFilters,
    activeFilterCount,
    toApiParams,
  }
}

/**
 * useSortState Hook
 *
 * Manages sort column and order state.
 */
export interface SortState {
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

export interface UseSortStateOptions {
  defaultSortBy?: string
  defaultSortOrder?: 'asc' | 'desc'
}

export interface UseSortStateReturn {
  sortState: SortState
  setSortBy: (column: string) => void
  toggleSortOrder: () => void
  setSortState: (state: Partial<SortState>) => void
}

export function useSortState(options: UseSortStateOptions = {}): UseSortStateReturn {
  const {
    defaultSortBy = 'cited_by_count',
    defaultSortOrder = 'desc',
  } = options

  const [sortState, setSortState] = useState<SortState>({
    sortBy: defaultSortBy,
    sortOrder: defaultSortOrder,
  })

  const setSortBy = useCallback((column: string) => {
    setSortState(prev => ({
      sortBy: column,
      sortOrder: prev.sortBy === column && prev.sortOrder === 'desc' ? 'asc' : 'desc',
    }))
  }, [])

  const toggleSortOrder = useCallback(() => {
    setSortState(prev => ({
      ...prev,
      sortOrder: prev.sortOrder === 'desc' ? 'asc' : 'desc',
    }))
  }, [])

  return {
    sortState,
    setSortBy,
    toggleSortOrder,
    setSortState,
  }
}
