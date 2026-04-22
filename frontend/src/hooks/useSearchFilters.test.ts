/**
 * Tests for useSearchFilters hook
 */
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useSearchFilters, useSortState } from './useSearchFilters'

describe('useSearchFilters', () => {
  describe('initialization', () => {
    it('should initialize with default empty filters', () => {
      const { result } = renderHook(() => useSearchFilters())

      expect(result.current.filters).toEqual({})
      expect(result.current.hasActiveFilters).toBe(false)
      expect(result.current.activeFilterCount).toBe(0)
    })

    it('should initialize with provided initial filters', () => {
      const { result } = renderHook(() =>
        useSearchFilters({
          initialFilters: { role: 'professor', country: 'US' },
        })
      )

      expect(result.current.filters.role).toBe('professor')
      expect(result.current.filters.country).toBe('US')
      expect(result.current.hasActiveFilters).toBe(true)
      expect(result.current.activeFilterCount).toBe(2)
    })
  })

  describe('setFilter', () => {
    it('should set a single filter value', () => {
      const { result } = renderHook(() => useSearchFilters())

      act(() => {
        result.current.setFilter('role', 'phd')
      })

      expect(result.current.filters.role).toBe('phd')
      expect(result.current.hasActiveFilters).toBe(true)
    })

    it('should update existing filter', () => {
      const { result } = renderHook(() =>
        useSearchFilters({ initialFilters: { role: 'professor' } })
      )

      act(() => {
        result.current.setFilter('role', 'phd')
      })

      expect(result.current.filters.role).toBe('phd')
    })

    it('should clear filter when set to undefined', () => {
      const { result } = renderHook(() =>
        useSearchFilters({ initialFilters: { role: 'professor' } })
      )

      act(() => {
        result.current.setFilter('role', undefined)
      })

      expect(result.current.filters.role).toBeUndefined()
      expect(result.current.hasActiveFilters).toBe(false)
    })
  })

  describe('setFilters', () => {
    it('should set multiple filters at once', () => {
      const { result } = renderHook(() => useSearchFilters())

      act(() => {
        result.current.setFilters({
          role: 'professor',
          country: 'CN',
          minCitations: 100,
        })
      })

      expect(result.current.filters.role).toBe('professor')
      expect(result.current.filters.country).toBe('CN')
      expect(result.current.filters.minCitations).toBe(100)
      expect(result.current.activeFilterCount).toBe(3)
    })

    it('should merge with existing filters', () => {
      const { result } = renderHook(() =>
        useSearchFilters({ initialFilters: { role: 'professor' } })
      )

      act(() => {
        result.current.setFilters({ country: 'US' })
      })

      expect(result.current.filters.role).toBe('professor')
      expect(result.current.filters.country).toBe('US')
    })
  })

  describe('resetFilters', () => {
    it('should reset all filters to default', () => {
      const { result } = renderHook(() =>
        useSearchFilters({ initialFilters: { role: 'professor', country: 'US' } })
      )

      act(() => {
        result.current.resetFilters()
      })

      expect(result.current.filters).toEqual({})
      expect(result.current.hasActiveFilters).toBe(false)
    })
  })

  describe('hasActiveFilters', () => {
    it('should return false when no filters are set', () => {
      const { result } = renderHook(() => useSearchFilters())
      expect(result.current.hasActiveFilters).toBe(false)
    })

    it('should return true when any filter is set', () => {
      const { result } = renderHook(() => useSearchFilters())

      act(() => {
        result.current.setFilter('minWorks', 10)
      })

      expect(result.current.hasActiveFilters).toBe(true)
    })

    it('should return false when filter is empty string', () => {
      const { result } = renderHook(() => useSearchFilters())

      act(() => {
        result.current.setFilter('role', '')
      })

      expect(result.current.filters.role).toBe('')
      expect(result.current.hasActiveFilters).toBe(false)
    })
  })

  describe('activeFilterCount', () => {
    it('should count only non-empty filters', () => {
      const { result } = renderHook(() => useSearchFilters())

      act(() => {
        result.current.setFilters({
          role: 'professor',
          country: '',
          minWorks: 5,
          minCitations: undefined,
        })
      })

      expect(result.current.activeFilterCount).toBe(2)
    })
  })

  describe('toApiParams', () => {
    it('should convert filters to API parameters', () => {
      const { result } = renderHook(() =>
        useSearchFilters({
          initialFilters: {
            role: 'professor',
            school: 123,
            country: 'US',
            techDomain: 456,
            minWorks: 10,
            minCitations: 100,
            isGraduated: 'true',
            confirmStatus: 'confirmed',
          },
        })
      )

      const params = result.current.toApiParams()

      expect(params.role_type).toBe('professor')
      expect(params.school_id).toBe(123)
      expect(params.country_code).toBe('US')
      expect(params.tech_domain_id).toBe(456)
      expect(params.min_works).toBe(10)
      expect(params.min_citations).toBe(100)
      expect(params.is_graduated).toBe('true')
      expect(params.confirm_status).toBe('confirmed')
    })

    it('should exclude undefined and empty filters', () => {
      const { result } = renderHook(() =>
        useSearchFilters({
          initialFilters: {
            role: 'professor',
            country: '',
            minWorks: undefined,
          },
        })
      )

      const params = result.current.toApiParams()

      expect(params.role_type).toBe('professor')
      expect(params.country_code).toBeUndefined()
      expect(params.min_works).toBeUndefined()
    })

    it('should return empty object when no filters', () => {
      const { result } = renderHook(() => useSearchFilters())
      const params = result.current.toApiParams()
      expect(params).toEqual({})
    })
  })
})

describe('useSortState', () => {
  it('should initialize with default sort', () => {
    const { result } = renderHook(() => useSortState())

    expect(result.current.sortState.sortBy).toBe('cited_by_count')
    expect(result.current.sortState.sortOrder).toBe('desc')
  })

  it('should initialize with custom defaults', () => {
    const { result } = renderHook(() =>
      useSortState({
        defaultSortBy: 'works_count',
        defaultSortOrder: 'asc',
      })
    )

    expect(result.current.sortState.sortBy).toBe('works_count')
    expect(result.current.sortState.sortOrder).toBe('asc')
  })

  it('should toggle sort order when clicking same column', () => {
    const { result } = renderHook(() => useSortState())

    act(() => {
      result.current.setSortBy('cited_by_count')
    })

    expect(result.current.sortState.sortOrder).toBe('asc')
  })

  it('should set new column with desc order', () => {
    const { result } = renderHook(() => useSortState())

    act(() => {
      result.current.setSortBy('works_count')
    })

    expect(result.current.sortState.sortBy).toBe('works_count')
    expect(result.current.sortState.sortOrder).toBe('desc')
  })

  it('should toggle sort order', () => {
    const { result } = renderHook(() => useSortState())

    act(() => {
      result.current.toggleSortOrder()
    })

    expect(result.current.sortState.sortOrder).toBe('asc')

    act(() => {
      result.current.toggleSortOrder()
    })

    expect(result.current.sortState.sortOrder).toBe('desc')
  })
})
