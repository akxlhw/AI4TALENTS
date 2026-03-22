import { useState, useCallback, useEffect } from 'react'

export interface SearchTemplate {
  id: string
  name: string
  filters: {
    role_type?: string
    min_works?: number
    min_citations?: number
    sort_by?: string
    sort_order?: 'desc' | 'asc'
  }
  created_at: string
}

const STORAGE_KEY = 'talent_search_templates'

/**
 * Hook to manage search templates
 */
export function useSearchTemplates() {
  const [templates, setTemplates] = useState<SearchTemplate[]>([])

  // Load templates from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        setTemplates(JSON.parse(stored))
      }
    } catch (error) {
      console.error('Failed to load search templates:', error)
    }
  }, [])

  // Save templates to localStorage
  const saveToStorage = useCallback((newTemplates: SearchTemplate[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newTemplates))
      setTemplates(newTemplates)
    } catch (error) {
      console.error('Failed to save search templates:', error)
    }
  }, [])

  // Add a new template
  const addTemplate = useCallback(
    (name: string, filters: SearchTemplate['filters']) => {
      const newTemplate: SearchTemplate = {
        id: `template_${Date.now()}`,
        name,
        filters,
        created_at: new Date().toISOString(),
      }
      saveToStorage([...templates, newTemplate])
      return newTemplate
    },
    [templates, saveToStorage]
  )

  // Remove a template
  const removeTemplate = useCallback(
    (id: string) => {
      saveToStorage(templates.filter((t) => t.id !== id))
    },
    [templates, saveToStorage]
  )

  // Rename a template
  const renameTemplate = useCallback(
    (id: string, newName: string) => {
      saveToStorage(
        templates.map((t) => (t.id === id ? { ...t, name: newName } : t))
      )
    },
    [templates, saveToStorage]
  )

  // Get a template by id
  const getTemplate = useCallback(
    (id: string) => templates.find((t) => t.id === id),
    [templates]
  )

  return {
    templates,
    addTemplate,
    removeTemplate,
    renameTemplate,
    getTemplate,
  }
}

export default useSearchTemplates
