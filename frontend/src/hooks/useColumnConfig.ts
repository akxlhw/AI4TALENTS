import { useState, useCallback, useEffect } from 'react'

export interface ColumnConfig {
  key: string
  label: string
  visible: boolean
  required?: boolean // 固定显示的列
}

const STORAGE_KEY = 'talent_search_columns'

// 默认列配置
const DEFAULT_COLUMNS: ColumnConfig[] = [
  { key: 'favorite', label: '收藏', visible: true, required: true },
  { key: 'name', label: '姓名', visible: true, required: true },
  { key: 'role_type', label: '角色', visible: true },
  { key: 'school_name', label: '学校', visible: true },
  { key: 'works_count', label: '论文数', visible: true },
  { key: 'cited_by_count', label: '引用数', visible: true },
  { key: 'h_index', label: 'H指数', visible: true },
  { key: 'topic_tags', label: '研究方向', visible: true },
]

/**
 * Hook to manage table column visibility
 */
export function useColumnConfig() {
  const [columns, setColumns] = useState<ColumnConfig[]>(DEFAULT_COLUMNS)

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const savedColumns = JSON.parse(stored)
        // Merge with defaults to handle new columns
        const merged = DEFAULT_COLUMNS.map(defaultCol => {
          const saved = savedColumns.find((c: ColumnConfig) => c.key === defaultCol.key)
          if (saved && !defaultCol.required) {
            return { ...defaultCol, visible: saved.visible }
          }
          return defaultCol
        })
        setColumns(merged)
      }
    } catch (error) {
      console.error('Failed to load column config:', error)
    }
  }, [])

  // Save to localStorage
  const saveToStorage = useCallback((newColumns: ColumnConfig[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns))
      setColumns(newColumns)
    } catch (error) {
      console.error('Failed to save column config:', error)
    }
  }, [])

  // Toggle column visibility
  const toggleColumn = useCallback(
    (key: string) => {
      const newColumns = columns.map(col =>
        col.key === key && !col.required ? { ...col, visible: !col.visible } : col
      )
      saveToStorage(newColumns)
    },
    [columns, saveToStorage]
  )

  // Set column visibility
  const setColumnVisible = useCallback(
    (key: string, visible: boolean) => {
      const newColumns = columns.map(col =>
        col.key === key && !col.required ? { ...col, visible } : col
      )
      saveToStorage(newColumns)
    },
    [columns, saveToStorage]
  )

  // Reset to defaults
  const resetColumns = useCallback(() => {
    saveToStorage(DEFAULT_COLUMNS)
  }, [saveToStorage])

  // Get visible column keys
  const getVisibleColumnKeys = useCallback(() => {
    return columns.filter(col => col.visible).map(col => col.key)
  }, [columns])

  // Check if column is visible
  const isColumnVisible = useCallback(
    (key: string) => {
      return columns.find(col => col.key === key)?.visible ?? true
    },
    [columns]
  )

  return {
    columns,
    toggleColumn,
    setColumnVisible,
    resetColumns,
    getVisibleColumnKeys,
    isColumnVisible,
  }
}

export default useColumnConfig
