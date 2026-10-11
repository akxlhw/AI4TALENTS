import { useState, useCallback, useEffect } from 'react'
import { logger } from '../utils/logger'

export interface ColumnConfig {
  key: string
  /** Display label — an i18n KEY (`common:columns.*`) translated at render time. */
  label: string
  visible: boolean
  required?: boolean // 固定显示的列
}

const STORAGE_KEY = 'talent_search_columns'

// 默认列配置（label 为 i18n key，渲染时经 t() 翻译）
const DEFAULT_COLUMNS: ColumnConfig[] = [
  { key: 'favorite', label: 'common:columns.favorite', visible: true, required: true },
  { key: 'name', label: 'common:columns.name', visible: true, required: true },
  { key: 'role_type', label: 'common:columns.role_type', visible: true },
  { key: 'school_name', label: 'common:columns.school_name', visible: true },
  { key: 'works_count', label: 'common:columns.works_count', visible: true },
  { key: 'cited_by_count', label: 'common:columns.cited_by_count', visible: true },
  { key: 'h_index', label: 'common:columns.h_index', visible: true },
  { key: 'topic_tags', label: 'common:columns.topic_tags', visible: true },
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
      logger.error('Failed to load column config:', error)
    }
  }, [])

  // Save to localStorage
  const saveToStorage = useCallback((newColumns: ColumnConfig[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns))
      setColumns(newColumns)
    } catch (error) {
      logger.error('Failed to save column config:', error)
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
