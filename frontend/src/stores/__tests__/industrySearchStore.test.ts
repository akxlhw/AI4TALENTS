import { describe, it, expect, beforeEach } from 'vitest'
import { useIndustrySearchStore } from '../industrySearchStore'

const initialState = {
  keyword: '',
  positionId: null,
  minScore: null,
  status: '',
  sourcePlatform: '',
  techDirection: '',
  sortBy: 'match_score_desc',
  page: 1,
  pageSize: 20,
} as const

describe('industrySearchStore', () => {
  beforeEach(() => {
    useIndustrySearchStore.setState({ ...initialState })
  })

  it('should initialize with default values', () => {
    const state = useIndustrySearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.positionId).toBeNull()
    expect(state.minScore).toBeNull()
    expect(state.sortBy).toBe('match_score_desc')
    expect(state.page).toBe(1)
  })

  it('should set filter and reset page to 1', () => {
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().setFilter('keyword', '张')
    const state = useIndustrySearchStore.getState()
    expect(state.keyword).toBe('张')
    expect(state.page).toBe(1)
  })

  it('should reset page when changing position/score/status filters', () => {
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().setFilter('positionId', 5)
    expect(useIndustrySearchStore.getState().page).toBe(1)
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().setFilter('minScore', 80)
    expect(useIndustrySearchStore.getState().page).toBe(1)
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().setFilter('status', 'contacted')
    expect(useIndustrySearchStore.getState().page).toBe(1)
  })

  it('should not reset page when changing sort or pagination', () => {
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().setFilter('sortBy', 'match_score_asc')
    useIndustrySearchStore.getState().setFilter('pageSize', 50)
    const state = useIndustrySearchStore.getState()
    expect(state.page).toBe(3)
    expect(state.sortBy).toBe('match_score_asc')
    expect(state.pageSize).toBe(50)
  })

  it('should reset filters to defaults', () => {
    useIndustrySearchStore.getState().setFilter('keyword', '张')
    useIndustrySearchStore.getState().setFilter('positionId', 2)
    useIndustrySearchStore.getState().setFilter('page', 3)
    useIndustrySearchStore.getState().resetFilters()
    const state = useIndustrySearchStore.getState()
    expect(state.keyword).toBe('')
    expect(state.positionId).toBeNull()
    expect(state.page).toBe(1)
  })

  it('should sync from URL params', () => {
    const query = new URLSearchParams(
      'keyword=张&position_id=3&min_score=80&status=new&source_platform=maimai&tech_direction=llm&sort_by=created_desc&page=2'
    )
    useIndustrySearchStore.getState().syncFromUrl(query)
    const state = useIndustrySearchStore.getState()
    expect(state.keyword).toBe('张')
    expect(state.positionId).toBe(3)
    expect(state.minScore).toBe(80)
    expect(state.status).toBe('new')
    expect(state.sourcePlatform).toBe('maimai')
    expect(state.techDirection).toBe('llm')
    expect(state.sortBy).toBe('created_desc')
    expect(state.page).toBe(2)
  })

  it('should fall back to defaults for invalid URL params', () => {
    const query = new URLSearchParams(
      'page=abc&page_size=-5&sort_by=invalid&position_id=xyz&min_score=999'
    )
    useIndustrySearchStore.getState().syncFromUrl(query)
    const state = useIndustrySearchStore.getState()
    expect(state.page).toBe(1)
    expect(state.pageSize).toBe(20)
    expect(state.sortBy).toBe('match_score_desc')
    expect(state.positionId).toBeNull()
    expect(state.minScore).toBeNull()
  })

  it('should convert state to query object', () => {
    useIndustrySearchStore.setState({
      keyword: '张',
      positionId: 3,
      minScore: 80,
      status: 'new',
      sourcePlatform: 'linkedin',
      techDirection: 'llm',
      sortBy: 'match_score_asc',
      page: 2,
    })
    const query = useIndustrySearchStore.getState().toQuery()
    expect(query).toEqual({
      keyword: '张',
      position_id: '3',
      min_score: '80',
      status: 'new',
      source_platform: 'linkedin',
      tech_direction: 'llm',
      sort_by: 'match_score_asc',
      page: '2',
    })
  })

  it('should omit default values from query object', () => {
    const query = useIndustrySearchStore.getState().toQuery()
    expect(query).toEqual({})
  })
})
