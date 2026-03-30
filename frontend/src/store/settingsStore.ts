/**
 * Settings Store
 *
 * Zustand store for user settings state management.
 * Manages column configs, search templates, and other user preferences.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ColumnConfig {
  key: string
  label: string
  visible: boolean
  width?: number
  fixed?: 'left' | 'right'
}

interface SearchTemplate {
  id: string
  name: string
  filters: Record<string, any>
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  createdAt: string
}

interface SettingsState {
  // Column configurations by page
  columnConfigs: Record<string, ColumnConfig[]>

  // Search templates
  searchTemplates: SearchTemplate[]

  // Default view settings
  defaultView: {
    perspective: 'tech-element' | 'country-school'
    techElementId?: number
    countryId?: number
  }

  // Theme
  theme: 'light' | 'dark'

  // Actions
  setColumnConfig: (page: string, config: ColumnConfig[]) => void
  getColumnConfig: (page: string) => ColumnConfig[] | undefined
  addSearchTemplate: (template: Omit<SearchTemplate, 'id' | 'createdAt'>) => void
  removeSearchTemplate: (id: string) => void
  setDefaultView: (view: Partial<SettingsState['defaultView']>) => void
  setTheme: (theme: 'light' | 'dark') => void
  reset: () => void
}

const defaultColumnConfig: Record<string, ColumnConfig[]> = {
  search: [
    { key: 'name', label: '姓名', visible: true, width: 180, fixed: 'left' },
    { key: 'role_type', label: '角色', visible: true, width: 100 },
    { key: 'school_name', label: '学校', visible: true, width: 150 },
    { key: 'h_index', label: 'H指数', visible: true, width: 80 },
    { key: 'works_count', label: '论文数', visible: true, width: 80 },
    { key: 'cited_by_count', label: '引用数', visible: true, width: 100 },
  ],
  favorites: [
    { key: 'name', label: '姓名', visible: true, width: 180, fixed: 'left' },
    { key: 'role_type', label: '角色', visible: true, width: 100 },
    { key: 'school_name', label: '学校', visible: true, width: 150 },
    { key: 'h_index', label: 'H指数', visible: true, width: 80 },
    { key: 'followup_status', label: '跟进状态', visible: true, width: 120 },
    { key: 'notes', label: '备注', visible: true, width: 150 },
  ],
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      columnConfigs: {},
      searchTemplates: [],
      defaultView: {
        perspective: 'tech-element',
      },
      theme: 'light',

      setColumnConfig: (page: string, config: ColumnConfig[]) => {
        set((state) => ({
          columnConfigs: {
            ...state.columnConfigs,
            [page]: config,
          },
        }))
      },

      getColumnConfig: (page: string) => {
        const state = get()
        return state.columnConfigs[page] || defaultColumnConfig[page]
      },

      addSearchTemplate: (template) => {
        const newTemplate: SearchTemplate = {
          ...template,
          id: Date.now().toString(),
          createdAt: new Date().toISOString(),
        }
        set((state) => ({
          searchTemplates: [...state.searchTemplates, newTemplate],
        }))
      },

      removeSearchTemplate: (id: string) => {
        set((state) => ({
          searchTemplates: state.searchTemplates.filter((t) => t.id !== id),
        }))
      },

      setDefaultView: (view) => {
        set((state) => ({
          defaultView: {
            ...state.defaultView,
            ...view,
          },
        }))
      },

      setTheme: (theme) => {
        set({ theme })
      },

      reset: () => {
        set({
          columnConfigs: {},
          searchTemplates: [],
          defaultView: { perspective: 'tech-element' },
          theme: 'light',
        })
      },
    }),
    {
      name: 'settings-storage',
    }
  )
)

export default useSettingsStore
