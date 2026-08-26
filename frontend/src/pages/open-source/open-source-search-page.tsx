import { useEffect, useState, useCallback } from 'react'
import { Typography, message } from 'antd'
import { logger } from '../../utils/logger'
import { useAuth } from '../../contexts/AuthContext'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import ExportConfirmModal from '../../components/ExportConfirmModal'
import { useExportDownload } from '../../hooks/useExportDownload'
import type { OSDeveloper } from '../../types'
import { useOsSearchQuery } from './components/use-os-search-query'
import OsSearchFilterCard from './components/os-search-filter-card'
import OsResultsToolbar from './components/os-results-toolbar'
import OsSearchResults from './components/os-search-results'

const { Title } = Typography

const OpenSourceSearchPage: React.FC = () => {
  const { isAdmin } = useAuth()
  const {
    query,
    setQuery,
    setQueryAndSyncUrl,
    handleClearFilters,
    handleSearch,
    handlePageChange,
  } = useOsSearchQuery()

  const [developers, setDevelopers] = useState<OSDeveloper[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set())
  const [filterExpanded, setFilterExpanded] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [searchError, setSearchError] = useState<string | null>(null)

  const [repoOptions, setRepoOptions] = useState<{ value: string; label: string }[]>([])
  const [repoLoading, setRepoLoading] = useState(false)

  const fetchDevelopers = useCallback(async () => {
    try {
      setLoading(true)
      setSearchError(null)
      let res
      if (query.mode === 'keyword') {
        res = await api.openSource.listDevelopers({
          q: query.q,
          tech_elements: query.tech_elements,
          languages: query.languages,
          location: query.location,
          company: query.company,
          repo_full_names: query.repo_full_names,
          is_committer: query.is_committer,
          is_student: query.is_student,
          has_contact: query.has_contact || undefined,
          sort_by: query.sort_by,
          page: query.page,
          page_size: query.page_size,
        })
      } else {
        res = await api.openSource.search({
          q: query.q,
          mode: query.mode,
          filters: {
            tech_elements: query.tech_elements,
            languages: query.languages,
            location: query.location,
            company: query.company,
            repo_full_names: query.repo_full_names,
            is_student: query.is_student,
            has_contact: query.has_contact || undefined,
          },
          sort_by: query.sort_by,
          page: query.page,
          page_size: query.page_size,
        })
      }
      setDevelopers(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (err) {
      const errorMessage = getErrorMessage(err, '搜索失败，请稍后重试')
      logger.error('Search failed', err)
      setSearchError(errorMessage)
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [query])

  const loadRepos = useCallback(async (techElements: string[]) => {
    if (!techElements?.length) {
      setRepoOptions([])
      return
    }
    try {
      setRepoLoading(true)
      const res = await api.openSource.listRepositories({
        tech_elements: techElements,
        page_size: 100,
      })
      const items = res.data.items || []
      setRepoOptions(
        items.map((item: { repo_full_name: string }) => ({
          value: item.repo_full_name,
          label: item.repo_full_name,
        }))
      )
    } catch (err) {
      logger.error('Failed to load repos', err)
      setRepoOptions([])
      message.warning('仓库列表加载失败')
    } finally {
      setRepoLoading(false)
    }
  }, [])

  const fetchFavoriteIds = useCallback(async () => {
    try {
      const res = await api.openSource.getFavoriteIds()
      setFavoriteIds(new Set(res.data.developer_ids || []))
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchDevelopers()
    fetchFavoriteIds()
  }, [fetchDevelopers, fetchFavoriteIds])

  useEffect(() => {
    if (query.tech_elements?.length) {
      loadRepos(query.tech_elements)
    } else {
      setRepoOptions([])
    }
  }, [query.tech_elements, loadRepos])

  const handleToggleFavorite = async (developerId: number) => {
    try {
      if (favoriteIds.has(developerId)) {
        await api.openSource.removeFavorite(developerId)
        setFavoriteIds(prev => {
          const next = new Set(prev)
          next.delete(developerId)
          return next
        })
      } else {
        await api.openSource.addFavorite(developerId)
        setFavoriteIds(prev => new Set(prev).add(developerId))
      }
    } catch (e) {
      logger.error('Favorite toggle failed', e)
      message.error(getErrorMessage(e, '收藏操作失败'))
    }
  }

  const toggleSelection = (developerId: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(developerId)) {
        next.delete(developerId)
      } else {
        next.add(developerId)
      }
      return next
    })
  }

  const isPageAllSelected =
    developers.length > 0 && developers.every(d => selectedIds.has(d.developer_id))

  const handleSelectPage = () => {
    if (isPageAllSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev)
        developers.forEach(d => next.delete(d.developer_id))
        return next
      })
    } else {
      setSelectedIds(prev => {
        const next = new Set(prev)
        developers.forEach(d => next.add(d.developer_id))
        return next
      })
    }
  }

  const handleSelectAll = async () => {
    try {
      const params: Record<string, unknown> = {
        q: query.q,
        tech_elements: query.tech_elements,
        languages: query.languages,
        location: query.location,
        company: query.company,
        repo_full_names: query.repo_full_names,
        is_committer: query.is_committer,
        is_student: query.is_student,
        has_contact: query.has_contact || undefined,
        sort_by: query.sort_by,
      }
      const res = await api.openSource.getAllDeveloperIds(params)
      setSelectedIds(new Set(res.data || []))
      message.success(`已全选 ${res.data.length} 位开发者`)
    } catch (e) {
      message.error(getErrorMessage(e, '全选失败'))
    }
  }

  const { exporting, exportMenu, exportConfirmVisible, confirmExport, cancelExport } =
    useExportDownload({
      getIds: () => Array.from(selectedIds),
      emptyWarning: '请先选择要导出的开发者',
      exportApi: (ids, format) => api.openSource.exportDevelopers(ids, format),
      fileName: 'os_developers_export',
      successMessage: count => `已导出 ${count} 位开发者`,
      formatError: e => getErrorMessage(e, '导出失败'),
    })

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3} style={{ marginBottom: 16 }}>
        开源人才搜索
      </Title>

      {/* Search & Filter */}
      <OsSearchFilterCard
        query={query}
        filterExpanded={filterExpanded}
        repoOptions={repoOptions}
        repoLoading={repoLoading}
        onQueryChange={setQuery}
        onQueryChangeAndSyncUrl={setQueryAndSyncUrl}
        onSearch={handleSearch}
        onToggleFilterExpanded={() => setFilterExpanded(!filterExpanded)}
      />

      {/* Results */}
      <OsResultsToolbar
        total={total}
        showControls={developers.length > 0 && !loading}
        isPageAllSelected={isPageAllSelected}
        selectedCount={selectedIds.size}
        isAdmin={isAdmin}
        exporting={exporting}
        exportMenu={exportMenu}
        onSelectPage={handleSelectPage}
        onSelectAll={handleSelectAll}
        onClearSelection={() => setSelectedIds(new Set())}
      />

      <OsSearchResults
        loading={loading}
        searchError={searchError}
        developers={developers}
        total={total}
        page={query.page || 1}
        pageSize={query.page_size || 20}
        favoriteIds={favoriteIds}
        selectedIds={selectedIds}
        onRetry={fetchDevelopers}
        onClearFilters={handleClearFilters}
        onPageChange={handlePageChange}
        onToggleFavorite={handleToggleFavorite}
        onToggleSelect={toggleSelection}
      />

      <ExportConfirmModal
        open={exportConfirmVisible}
        onConfirm={confirmExport}
        onCancel={cancelExport}
      />
    </div>
  )
}

export default OpenSourceSearchPage
