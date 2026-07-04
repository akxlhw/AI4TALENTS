import { describe, it, expect, beforeEach } from 'vitest'
import { useLabSearchStore } from '../labSearchStore'

describe('labSearchStore', () => {
  beforeEach(() => {
    useLabSearchStore.setState({
      keyword: '',
      parentLab: '',
      labName: '',
      roleType: '',
      academicLevel: '',
      researchArea: '',
      sortBy: 'default',
      page: 1,
      pageSize: 20,
      advancedOpen: false,
    })
  })

  it('should initialize with default values', () => {
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.page).toBe(1)
    expect(state.sortBy).toBe('default')
  })

  it('should set filter and reset page to 1', () => {
    useLabSearchStore.getState().setFilter('page', 3)
    useLabSearchStore.getState().setFilter('keyword', '周')
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('周')
    expect(state.page).toBe(1)
  })

  it('should not reset page when changing sort or pagination', () => {
    useLabSearchStore.getState().setFilter('page', 3)
    useLabSearchStore.getState().setFilter('sortBy', 'name_asc')
    useLabSearchStore.getState().setFilter('pageSize', 50)
    const state = useLabSearchStore.getState()
    expect(state.page).toBe(3)
    expect(state.sortBy).toBe('name_asc')
    expect(state.pageSize).toBe(50)
  })

  it('should reset filters to defaults', () => {
    useLabSearchStore.getState().setFilter('keyword', '周')
    useLabSearchStore.getState().setFilter('page', 3)
    useLabSearchStore.getState().resetFilters()
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.page).toBe(1)
  })

  it('should sync from URL params', () => {
    const query = new URLSearchParams('keyword=周&role_type=professor&page=2&sort_by=name_asc')
    useLabSearchStore.getState().syncFromUrl(query)
    const state = useLabSearchStore.getState()
    expect(state.keyword).toBe('周')
    expect(state.roleType).toBe('professor')
    expect(state.page).toBe(2)
    expect(state.sortBy).toBe('name_asc')
  })

  it('should fall back to defaults for invalid URL params', () => {
    const query = new URLSearchParams('page=abc&page_size=-5&sort_by=invalid')
    useLabSearchStore.getState().syncFromUrl(query)
    const state = useLabSearchStore.getState()
    expect(state.page).toBe(1)
    expect(state.pageSize).toBe(20)
    expect(state.sortBy).toBe('default')
  })

  it('should toggle advanced filters', () => {
    useLabSearchStore.getState().toggleAdvanced()
    expect(useLabSearchStore.getState().advancedOpen).toBe(true)
    useLabSearchStore.getState().toggleAdvanced()
    expect(useLabSearchStore.getState().advancedOpen).toBe(false)
  })

  it('should convert state to query object', () => {
    useLabSearchStore.setState({
      keyword: '周',
      roleType: 'professor',
      page: 2,
      sortBy: 'name_asc',
    })
    const query = useLabSearchStore.getState().toQuery()
    expect(query).toEqual({
      keyword: '周',
      role_type: 'professor',
      page: '2',
      sort_by: 'name_asc',
    })
  })
})
