import { create } from 'zustand'

/**
 * Lab search state management using Zustand.
 *
 * Holds filter values, sorting, pagination, and advanced-panel visibility for
 * the `/lab/search` page. Provides bidirectional synchronization with URL query
 * parameters so searches are shareable and refresh-safe.
 */

export type LabSortBy = 'default' | 'name_asc' | 'cohort_desc' | 'created_desc'

export interface LabSearchState {
  keyword: string
  parentLab: string
  labName: string
  roleType: string
  academicLevel: string
  researchArea: string
  sortBy: LabSortBy
  page: number
  pageSize: number
  advancedOpen: boolean

  setFilter: <
    K extends keyof Omit<
      LabSearchState,
      'setFilter' | 'resetFilters' | 'toggleAdvanced' | 'syncFromUrl' | 'toQuery'
    >,
  >(
    key: K,
    value: LabSearchState[K]
  ) => void
  resetFilters: () => void
  toggleAdvanced: () => void
  syncFromUrl: (query: URLSearchParams) => void
  toQuery: () => Record<string, string>
}

type FilterKey = 'keyword' | 'parentLab' | 'labName' | 'roleType' | 'academicLevel' | 'researchArea'

const FILTER_KEYS: FilterKey[] = [
  'keyword',
  'parentLab',
  'labName',
  'roleType',
  'academicLevel',
  'researchArea',
]

const SORT_OPTIONS: LabSortBy[] = ['default', 'name_asc', 'cohort_desc', 'created_desc']
const DEFAULT_PAGE = 1
const DEFAULT_PAGE_SIZE = 20

const initialState: Omit<
  LabSearchState,
  'setFilter' | 'resetFilters' | 'toggleAdvanced' | 'syncFromUrl' | 'toQuery'
> = {
  keyword: '',
  parentLab: '',
  labName: '',
  roleType: '',
  academicLevel: '',
  researchArea: '',
  sortBy: 'default',
  page: DEFAULT_PAGE,
  pageSize: DEFAULT_PAGE_SIZE,
  advancedOpen: false,
}

function parseIntWithDefault(value: string | null, defaultValue: number): number {
  if (!value) return defaultValue
  const parsed = parseInt(value, 10)
  return Number.isNaN(parsed) || parsed < 1 ? defaultValue : parsed
}

function parseSortBy(value: string | null): LabSortBy {
  return SORT_OPTIONS.includes(value as LabSortBy) ? (value as LabSortBy) : 'default'
}

export const useLabSearchStore = create<LabSearchState>((set, get) => ({
  ...initialState,

  setFilter: (key, value) => {
    const update: Partial<LabSearchState> = { [key]: value }
    if (FILTER_KEYS.includes(key as FilterKey)) {
      update.page = DEFAULT_PAGE
    }
    set(update)
  },

  resetFilters: () => {
    set({ ...initialState })
  },

  toggleAdvanced: () => {
    set(state => ({ advancedOpen: !state.advancedOpen }))
  },

  syncFromUrl: query => {
    set({
      keyword: query.get('keyword') || '',
      parentLab: query.get('parent_lab') || '',
      labName: query.get('lab_name') || '',
      roleType: query.get('role_type') || '',
      academicLevel: query.get('academic_level') || '',
      researchArea: query.get('research_area') || '',
      sortBy: parseSortBy(query.get('sort_by')),
      page: parseIntWithDefault(query.get('page'), DEFAULT_PAGE),
      pageSize: parseIntWithDefault(query.get('page_size'), DEFAULT_PAGE_SIZE),
      advancedOpen: query.has('advanced') && query.get('advanced') === '1',
    })
  },

  toQuery: () => {
    const state = get()
    const query: Record<string, string> = {}
    if (state.keyword) query.keyword = state.keyword
    if (state.parentLab) query.parent_lab = state.parentLab
    if (state.labName) query.lab_name = state.labName
    if (state.roleType) query.role_type = state.roleType
    if (state.academicLevel) query.academic_level = state.academicLevel
    if (state.researchArea) query.research_area = state.researchArea
    if (state.sortBy !== 'default') query.sort_by = state.sortBy
    if (state.page > DEFAULT_PAGE) query.page = String(state.page)
    if (state.pageSize !== DEFAULT_PAGE_SIZE) query.page_size = String(state.pageSize)
    if (state.advancedOpen) query.advanced = '1'
    return query
  },
}))
