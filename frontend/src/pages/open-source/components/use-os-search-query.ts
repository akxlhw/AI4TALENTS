import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { OSSearchQuery } from '../../../types'

/**
 * Owns the search query state of the open-source search page and keeps it
 * in two-way sync with the URL search params.
 */
export function useOsSearchQuery() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [query, setQuery] = useState<OSSearchQuery>({
    q: searchParams.get('q') || '',
    tech_elements: searchParams.get('tech_elements')?.split(',').filter(Boolean) || [],
    languages: searchParams.get('languages')?.split(',').filter(Boolean) || [],
    location: searchParams.get('location') || '',
    company: searchParams.get('company') || '',
    repo_full_names: searchParams.get('repo_full_names')?.split(',').filter(Boolean) || [],
    is_committer: searchParams.get('is_committer') === 'true',
    is_student: searchParams.get('is_student') === 'true',
    sort_by: searchParams.get('sort_by') || 'stars_desc',
    mode: (searchParams.get('mode') as OSSearchQuery['mode']) || 'keyword',
    page: parseInt(searchParams.get('page') || '1'),
    page_size: 20,
  })

  const updateSearchParams = (newQuery: OSSearchQuery) => {
    const params = new URLSearchParams()
    if (newQuery.q) params.set('q', newQuery.q)
    if (newQuery.tech_elements?.length)
      params.set('tech_elements', newQuery.tech_elements.join(','))
    if (newQuery.languages?.length) params.set('languages', newQuery.languages.join(','))
    if (newQuery.location) params.set('location', newQuery.location)
    if (newQuery.company) params.set('company', newQuery.company)
    if (newQuery.repo_full_names?.length)
      params.set('repo_full_names', newQuery.repo_full_names.join(','))

    if (newQuery.is_committer) params.set('is_committer', 'true')
    if (newQuery.is_student) params.set('is_student', 'true')
    if (newQuery.sort_by && newQuery.sort_by !== 'stars_desc')
      params.set('sort_by', newQuery.sort_by)
    if (newQuery.mode && newQuery.mode !== 'keyword') params.set('mode', newQuery.mode)
    if (newQuery.page && newQuery.page > 1) params.set('page', String(newQuery.page))
    setSearchParams(params)
  }

  const setQueryAndSyncUrl = (newQuery: OSSearchQuery) => {
    setQuery(newQuery)
    updateSearchParams(newQuery)
  }

  const handleClearFilters = () => {
    setQueryAndSyncUrl({
      ...query,
      q: '',
      tech_elements: [],
      languages: [],
      location: '',
      company: '',
      repo_full_names: [],
      is_committer: false,
      is_student: false,
      page: 1,
    })
  }

  const handleSearch = () => {
    setQueryAndSyncUrl({ ...query, page: 1 })
  }

  const handlePageChange = (page: number) => {
    setQueryAndSyncUrl({ ...query, page })
  }

  return {
    query,
    setQuery,
    setQueryAndSyncUrl,
    handleClearFilters,
    handleSearch,
    handlePageChange,
  }
}
