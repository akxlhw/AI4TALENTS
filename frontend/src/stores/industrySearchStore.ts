import { create } from 'zustand'

/**
 * Industry talent search state management using Zustand.
 *
 * Holds filter values, sorting and pagination for the `/industry` page.
 * Provides bidirectional synchronization with URL query parameters so
 * searches are shareable and refresh-safe (mirrors labSearchStore).
 */

export type IndustrySortBy = 'match_score_desc' | 'match_score_asc' | 'created_desc' | 'name_asc'

export interface IndustrySearchState {
  keyword: string
  positionId: number | null
  minScore: number | null
  status: string
  sourcePlatform: string
  techDirection: string
  sortBy: IndustrySortBy
  page: number
  pageSize: number

  setFilter: <
    K extends keyof Omit<IndustrySearchState, 'setFilter' | 'resetFilters' | 'syncFromUrl' | 'toQuery'>,
  >(
    key: K,
    value: IndustrySearchState[K]
  ) => void
  resetFilters: () => void
  syncFromUrl: (query: URLSearchParams) => void
  toQuery: () => Record<string, string>
}

type FilterKey =
  | 'keyword'
  | 'positionId'
  | 'minScore'
  | 'status'
  | 'sourcePlatform'
  | 'techDirection'

const FILTER_KEYS: FilterKey[] = [
  'keyword',
  'positionId',
  'minScore',
  'status',
  'sourcePlatform',
  'techDirection',
]

const SORT_OPTIONS: IndustrySortBy[] = [
  'match_score_desc',
  'match_score_asc',
  'created_desc',
  'name_asc',
]
const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

const initialState: Omit<
  IndustrySearchState,
  'setFilter' | 'resetFilters' | 'syncFromUrl' | 'toQuery'
> = {
  keyword: '',
  positionId: null,
  minScore: null,
  status: '',
  sourcePlatform: '',
  techDirection: '',
  sortBy: 'match_score_desc',
  page: DEFAULT_PAGE,
  pageSize: DEFAULT_PAGE_SIZE,
}

function parseIntWithDefault(value: string | null, defaultValue: number): number {
  if (!value) return defaultValue
  const parsed = parseInt(value, 10)
  return Number.isNaN(parsed) || parsed < 1 ? defaultValue : parsed
}

function parseNullableNumber(value: string | null, min: number, max: number): number | null {
  if (!value) return null
  const parsed = Number(value)
  return Number.isNaN(parsed) || parsed < min || parsed > max ? null : parsed
}

function parseSortBy(value: string | null): IndustrySortBy {
  return SORT_OPTIONS.includes(value as IndustrySortBy) ? (value as IndustrySortBy) : 'match_score_desc'
}

export const useIndustrySearchStore = create<IndustrySearchState>((set, get) => ({
  ...initialState,

  setFilter: (key, value) => {
    const update: Partial<IndustrySearchState> = { [key]: value }
    if (FILTER_KEYS.includes(key as FilterKey)) {
      update.page = DEFAULT_PAGE
    }
    set(update)
  },

  resetFilters: () => {
    set({ ...initialState })
  },

  syncFromUrl: query => {
    set({
      keyword: query.get('keyword') || '',
      positionId: parseNullableNumber(query.get('position_id'), 1, Number.MAX_SAFE_INTEGER),
      minScore: parseNullableNumber(query.get('min_score'), 0, 100),
      status: query.get('status') || '',
      sourcePlatform: query.get('source_platform') || '',
      techDirection: query.get('tech_direction') || '',
      sortBy: parseSortBy(query.get('sort_by')),
      page: parseIntWithDefault(query.get('page'), DEFAULT_PAGE),
      pageSize: parseIntWithDefault(query.get('page_size'), DEFAULT_PAGE_SIZE),
    })
  },

  toQuery: () => {
    const state = get()
    const query: Record<string, string> = {}
    if (state.keyword) query.keyword = state.keyword
    if (state.positionId !== null) query.position_id = String(state.positionId)
    if (state.minScore !== null) query.min_score = String(state.minScore)
    if (state.status) query.status = state.status
    if (state.sourcePlatform) query.source_platform = state.sourcePlatform
    if (state.techDirection) query.tech_direction = state.techDirection
    if (state.sortBy !== 'match_score_desc') query.sort_by = state.sortBy
    if (state.page > DEFAULT_PAGE) query.page = String(state.page)
    if (state.pageSize !== DEFAULT_PAGE_SIZE) query.page_size = String(state.pageSize)
    return query
  },
}))
