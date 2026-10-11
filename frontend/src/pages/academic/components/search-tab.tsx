import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../../contexts/AuthContext'
import {
  Card,
  Input,
  InputRef,
  Table,
  type TablePaginationConfig,
  Typography,
  Tag,
  Space,
  Select,
  Empty,
  Spin,
  Row,
  Col,
  Button,
  Dropdown,
  message,
  Modal,
  Tooltip,
  Alert,
} from 'antd'
import {
  SortAscendingOutlined,
  SortDescendingOutlined,
  DownOutlined,
  DownloadOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import { semanticColors } from '../../../theme'
import FavoriteButton from '../../../components/FavoriteButton'
import TalentCompareModal from '../../../components/TalentCompareModal'
import TopicTags from '../../../components/TopicTags'
import ColumnSettings from '../../../components/ColumnSettings'
import ExportConfirmModal from '../../../components/ExportConfirmModal'
import { useKeyboardShortcuts } from '../../../hooks/useKeyboardShortcuts'
import { useSearchTemplates } from '../../../hooks/useSearchTemplates'
import { useColumnConfig } from '../../../hooks/useColumnConfig'
import { getRoleTypeConfig, LEGACY_ROLE_TYPE_MAP } from '../../../constants/roleType'
import '../../../i18n/namespaces/academic'
import { formatNumber } from '../../../utils/format'
import type { SearchTalent, TechDomain, EnhancedSearchResult } from '../../../types'

const { Text } = Typography
const { Search } = Input

interface School { school_id: number; school_name: string }

interface Country { country_code: string; country_name_cn: string }

interface SearchTabProps {
  schools: School[]
  countries: Country[]
  techDomains: TechDomain[]
  countryOptions: { value: string; label: string }[]
  schoolOptions: { value: number; label: string }[]
  techDomainOptions: { value: number; label: string }[]
  onAddToReference: (talentId: number, talentName: string) => void
}

interface SearchUrlState {
  q: string
  page: number
  role?: string
  school?: number
  minCit?: number
  country?: string
  techDomain?: number
  sortField: string
  order: 'desc' | 'asc'
}

const SearchTab: React.FC<SearchTabProps> = ({
  countryOptions,
  schoolOptions,
  techDomainOptions,
  onAddToReference,
}) => {
  const { isAdmin } = useAuth()
  const navigate = useNavigate()
  const { t } = useTranslation(['academic', 'common'])
  const [urlSearchParams] = useSearchParams()
  const searchInputRef = useRef<InputRef>(null)

  const [query, setQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [results, setResults] = useState<SearchTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20
  const [tookMs, setTookMs] = useState<number | null>(null)
  const [searchModeUsed, setSearchModeUsed] = useState<string | null>(null)
  const [fulltextMatchCount, setFulltextMatchCount] = useState(0)
  const [semanticMatchCount, setSemanticMatchCount] = useState(0)
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [schoolFilter, setSchoolFilter] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()
  const [sortBy, setSortBy] = useState<string>('cited_by_count')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)
  const [exportConfirmVisible, setExportConfirmVisible] = useState(false)
  const [pendingExportFormat, setPendingExportFormat] = useState<'csv' | 'xlsx' | null>(null)
  const [compareModalVisible, setCompareModalVisible] = useState(false)
  const [countryFilter, setCountryFilter] = useState<string | undefined>()
  const [techDomainFilter, setTechDomainFilter] = useState<number | undefined>()
  const { addTemplate } = useSearchTemplates()
  const [saveTemplateModalVisible, setSaveTemplateModalVisible] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const { columns: columnConfig, toggleColumn, resetColumns } = useColumnConfig()
  const [columnSettingsVisible, setColumnSettingsVisible] = useState(false)

  useKeyboardShortcuts([
    { key: '/', action: () => searchInputRef.current?.focus() },
    { key: 'f', ctrlKey: true, action: () => searchInputRef.current?.focus() },
    { key: 'Escape', action: () => { if (compareModalVisible) setCompareModalVisible(false) } },
  ])

  // URL is the single source of truth for search state. Every user action
  // (search/filter/sort/page) updates the URL via updateUrl; this effect
  // re-syncs the UI and re-runs the search — covering mount, shared links,
  // and browser back/forward navigation.
  useEffect(() => {
    const tab = urlSearchParams.get('tab')
    if (tab && tab !== 'search') return
    const s: SearchUrlState = {
      q: urlSearchParams.get('q') || '',
      page: parseInt(urlSearchParams.get('page') || '1', 10),
      role: urlSearchParams.get('role_type') || undefined,
      school: urlSearchParams.get('school_id') ? Number(urlSearchParams.get('school_id')) : undefined,
      minCit: urlSearchParams.get('min_citations') ? Number(urlSearchParams.get('min_citations')) : undefined,
      country: urlSearchParams.get('country') || undefined,
      techDomain: urlSearchParams.get('tech_domain') ? Number(urlSearchParams.get('tech_domain')) : undefined,
      sortField: urlSearchParams.get('sort_by') || 'cited_by_count',
      order: (urlSearchParams.get('sort_order') as 'desc' | 'asc') || 'desc',
    }
    setQuery(s.q)
    setRoleFilter(s.role)
    setSchoolFilter(s.school)
    setMinCitations(s.minCit)
    setCountryFilter(s.country)
    setTechDomainFilter(s.techDomain)
    setSortBy(s.sortField)
    setSortOrder(s.order)
    performSearch(s.q, s.page, s)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSearchParams])

  const loadAllTalents = async (pageNum: number = 1, filters: SearchUrlState) => {
    setSearchLoading(true)
    try {
      const response = await api.talents.list({
        page: pageNum,
        page_size: pageSize,
        role_type: filters.role,
        school_id: filters.school,
        country_code: filters.country,
      })
      const items: SearchTalent[] = (response.data.items || []).map((item: SearchTalent) => ({
        talent_id: item.talent_id,
        name: item.name,
        name_en: item.name_en,
        role_type: item.role_type,
        school_id: item.school_id,
        school_name: item.school_name,
        education_school_id: item.education_school_id,
        education_school_name: item.education_school_name,
        company_school_id: item.company_school_id,
        company_school_name: item.company_school_name,
        current_title: item.current_title,
        works_count: item.works_count,
        cited_by_count: item.cited_by_count,
        h_index: item.h_index,
        topic_tags: item.topic_tags || [],
        openalex_topics: item.openalex_topics || [],
      }))
      setResults(items)
      setTotal(response.data.total || items.length)
      setTookMs(null)
      setPage(pageNum)
    } catch {
      message.error(t('searchTab.loadListError'))
    } finally {
      setSearchLoading(false)
    }
  }

  const performSearch = async (searchQuery: string, pageNum: number, filters: SearchUrlState) => {
    if (!searchQuery.trim()) return loadAllTalents(pageNum, filters)
    setSearchLoading(true)
    setTookMs(null)
    setSearchModeUsed(null)
    try {
      const response = await api.enhancedSearch.search({
        q: searchQuery.trim(),
        mode: 'hybrid',
        role_type: filters.role,
        school_id: filters.school,
        min_citations: filters.minCit,
        country_code: filters.country,
        tech_domain_id: filters.techDomain,
        page: pageNum,
        page_size: pageSize,
      })
      const items: SearchTalent[] = (response.data.items || []).map((item: EnhancedSearchResult) => ({
        talent_id: item.talent_id,
        name: item.name,
        name_en: item.name_en,
        role_type: item.role_type,
        school_id: item.school_id,
        school_name: item.school_name,
        education_school_id: item.education_school_id,
        education_school_name: item.education_school_name,
        company_school_id: item.company_school_id,
        company_school_name: item.company_school_name,
        current_title: item.current_title,
        works_count: item.works_count,
        cited_by_count: item.cited_by_count,
        h_index: item.h_index,
        topic_tags: item.topic_tags || [],
        openalex_topics: item.openalex_topics || [],
        similarity_score: item.similarity_score,
        match_sources: item.match_sources || [],
      }))
      setResults(items)
      setTotal(response.data.total || items.length)
      setTookMs(response.data.took_ms || null)
      setSearchModeUsed(response.data.mode || 'hybrid')
      setFulltextMatchCount(response.data.fulltext_count || 0)
      setSemanticMatchCount(response.data.semantic_count || 0)
      setPage(pageNum)
    } catch {
      message.error(t('searchTab.searchError'))
    } finally {
      setSearchLoading(false)
    }
  }

  // Push a URL change; the effect above turns it into a new search
  const updateUrl = (changes: Record<string, string | undefined>) => {
    const params = new URLSearchParams(urlSearchParams)
    Object.entries(changes).forEach(([key, value]) => {
      if (value === undefined || value === '') params.delete(key)
      else params.set(key, value)
    })
    params.set('tab', 'search')
    navigate(`/search-recommend?${params.toString()}`)
  }

  const handleSearch = (value: string) => {
    updateUrl({ q: value.trim() || undefined, page: undefined })
  }

  const handleTableChange = (pagination: TablePaginationConfig) => {
    const next = pagination.current || 1
    updateUrl({ page: next > 1 ? String(next) : undefined })
  }

  const handleResetFilters = () => {
    updateUrl({
      role_type: undefined,
      school_id: undefined,
      min_citations: undefined,
      country: undefined,
      tech_domain: undefined,
      sort_by: undefined,
      sort_order: undefined,
      page: undefined,
    })
  }

  const handleExportRequest = (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('searchTab.exportSelectFirst'))
      return
    }
    setPendingExportFormat(format)
    setExportConfirmVisible(true)
  }

  const handleExportConfirm = async () => {
    if (!pendingExportFormat) return
    setExporting(true)
    try {
      const response = await api.talents.export(selectedRowKeys as number[], pendingExportFormat)
      const blob = new Blob([response.data], { type: pendingExportFormat === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `talents_export.${pendingExportFormat}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success(t('searchTab.exportSuccess', { n: selectedRowKeys.length }))
    } catch {
      message.error(t('searchTab.exportError'))
    } finally {
      setExporting(false)
      setExportConfirmVisible(false)
      setPendingExportFormat(null)
    }
  }

  const exportMenu = {
    items: [
      { key: 'csv', label: t('searchTab.exportCsv') },
      { key: 'xlsx', label: t('searchTab.exportExcel') },
    ],
    onClick: (e: { key: string }) => handleExportRequest(e.key as 'csv' | 'xlsx'),
  }

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning(t('searchTab.compareSelectRange'))
      return
    }
    setCompareModalVisible(true)
  }

  const sortMenu = {
    onClick: (e: { key: string }) => {
      const [field, order] = e.key.split('-')
      updateUrl({
        sort_by: field === 'cited_by_count' ? undefined : field,
        sort_order: order === 'desc' ? undefined : order,
        page: undefined,
      })
    },
    items: [
      { key: 'cited_by_count-desc', label: t('searchTab.sortBy.citationsDesc') },
      { key: 'cited_by_count-asc', label: t('searchTab.sortBy.citationsAsc') },
      { key: 'works_count-desc', label: t('searchTab.sortBy.worksDesc') },
      { key: 'works_count-asc', label: t('searchTab.sortBy.worksAsc') },
    ],
  }

  const hasActiveFilters = roleFilter || schoolFilter || minCitations || countryFilter || techDomainFilter

  const searchColumns = [
    {
      title: t('columns.favorite'),
      key: 'favorite',
      width: 60,
      align: 'center' as const,
      render: (_: unknown, record: SearchTalent) => <FavoriteButton talentId={record.talent_id} size="small" />,
    },
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: SearchTalent) => {
        const similarity = record.similarity_score
        const isSimilarRecommend = similarity !== undefined && similarity >= 0.7 && similarity < 0.9
        const nameStyle = isSimilarRecommend ? { fontWeight: 500, color: semanticColors.orange } : { fontWeight: 500 }

        const nameContent = (
          <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={nameStyle}>
            <Space direction="vertical" size={0}>
              <span>{name}</span>
              {record.name_en && <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>}
            </Space>
          </a>
        )

        if (isSimilarRecommend) {
          const percent = Math.round((similarity || 0) * 100)
          return (
            <Tooltip title={t('searchTab.similarTooltip', { percent })}>
              {nameContent}
            </Tooltip>
          )
        }
        return nameContent
      },
    },
    {
      title: t('columns.role'),
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = getRoleTypeConfig(role)
        const roleKey = LEGACY_ROLE_TYPE_MAP[role] || role
        return <Tag color={config.color}>{t(`roles.${roleKey}`, { defaultValue: config.text })}</Tag>
      },
    },
    {
      title: t('columns.school'),
      key: 'school',
      width: 150,
      ellipsis: true,
      render: (_: unknown, record: SearchTalent) => {
        if (record.education_school_name) {
          return <span>{record.education_school_name}</span>
        }
        if (record.company_school_name) {
          return <span>{record.company_school_name}</span>
        }
        return record.school_name ? (
          <a onClick={() => navigate(`/schools/${record.school_id}`)}>{record.school_name}</a>
        ) : (
          <Text type="secondary">-</Text>
        )
      },
    },
    { title: t('columns.works'), dataIndex: 'works_count', key: 'works_count', width: 80, align: 'center' as const },
    { title: t('columns.citations'), dataIndex: 'cited_by_count', key: 'cited_by_count', width: 100, align: 'right' as const, render: (count: number) => formatNumber(count) },
    { title: t('columns.hIndex'), dataIndex: 'h_index', key: 'h_index', width: 80, align: 'center' as const },
    {
      title: t('columns.researchDirections'),
      dataIndex: 'openalex_topics',
      key: 'openalex_topics',
      width: 200,
      render: (topics: string[], record: SearchTalent) => <TopicTags tags={topics && topics.length > 0 ? topics : record.topic_tags} maxVisible={2} />,
    },
    {
      title: t('columns.actions'),
      key: 'actions',
      width: 100,
      render: (_: unknown, record: SearchTalent) => (
        <Tooltip title={t('searchTab.addToReferenceTip')}>
          <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => onAddToReference(record.talent_id, record.name)}>
            {t('searchTab.addToReference')}
          </Button>
        </Tooltip>
      ),
    },
  ]

  return (
    <>
      {/* Search Box */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Search
              ref={searchInputRef}
              placeholder={t('searchTab.placeholder')}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton={t('common:actions.search')}
              size="large"
              allowClear
            />
          </Col>
          <Col>
            <Dropdown menu={sortMenu} trigger={['click']}>
              <Button size="large" icon={sortOrder === 'desc' ? <SortDescendingOutlined /> : <SortAscendingOutlined />}>
                {t('searchTab.sort')} <DownOutlined />
              </Button>
            </Dropdown>
          </Col>
        </Row>
      </Card>

      {/* Search Technology Info */}
      {query.trim() && tookMs && (
        <Alert
          message={
            <Space split={<span style={{ color: semanticColors.borderGray }}>|</span>}>
              <Space>
                <ThunderboltOutlined style={{ color: 'var(--domain-primary)' }} />
                <span>
                  {t('searchTab.smartSearchEnabled')}
                  {searchModeUsed === 'hybrid' && t('searchTab.modeHybrid')}
                  {searchModeUsed === 'semantic' && t('searchTab.modeSemantic')}
                  {searchModeUsed === 'keyword' && t('searchTab.modeKeyword')}
                  {searchModeUsed === 'fulltext' && t('searchTab.modeFulltext')}
                </span>
              </Space>
              <span>{t('searchTab.totalPeople', { n: total })}</span>
              {(fulltextMatchCount > 0 || semanticMatchCount > 0) && (
                <>
                  {fulltextMatchCount > 0 && (
                    <span style={{ color: semanticColors.orange }}>
                      {t('searchTab.keywordMatches', { n: fulltextMatchCount })}
                    </span>
                  )}
                  {semanticMatchCount > 0 && (
                    <span style={{ color: 'var(--domain-secondary)' }}>
                      {t('searchTab.semanticMatches', { n: semanticMatchCount })}
                    </span>
                  )}
                </>
              )}
              <span style={{ color: '#999' }}>{t('searchTab.tookMs', { ms: tookMs.toFixed(0) })}</span>
            </Space>
          }
          type="info"
          style={{ marginBottom: 16 }}
          showIcon={false}
        />
      )}

      {/* Filters */}
      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '12px 24px' } }}>
        <Row gutter={[16, 8]}>
          <Col span={24}>
            <Space size={8} wrap>
              <Text type="secondary">{t('filters.label')}</Text>
              <Select placeholder={t('filters.techDomain')} value={techDomainFilter} onChange={(val) => updateUrl({ tech_domain: val ? String(val) : undefined, page: undefined })} allowClear showSearch optionFilterProp="label" style={{ width: 140 }} options={techDomainOptions} />
              <Select placeholder={t('filters.country')} value={countryFilter} onChange={(val) => updateUrl({ country: val || undefined, page: undefined })} allowClear showSearch optionFilterProp="label" style={{ width: 120 }} options={countryOptions} />
              <Select placeholder={t('filters.school')} value={schoolFilter} onChange={(val) => updateUrl({ school_id: val ? String(val) : undefined, page: undefined })} allowClear showSearch optionFilterProp="label" style={{ width: 180 }} options={schoolOptions} />
              <Select placeholder={t('filters.role')} value={roleFilter} onChange={(val) => updateUrl({ role_type: val || undefined, page: undefined })} allowClear style={{ width: 140 }} options={[{ value: 'professor', label: t('roles.professor') }, { value: 'student', label: t('roles.student') }, { value: 'graduated', label: t('roles.graduate') }]} />
              <Select placeholder={t('filters.minCitations')} value={minCitations} onChange={(val) => updateUrl({ min_citations: val ? String(val) : undefined, page: undefined })} allowClear style={{ width: 120 }} options={[{ value: 100, label: t('searchTab.minCitations.c100') }, { value: 500, label: t('searchTab.minCitations.c500') }, { value: 1000, label: t('searchTab.minCitations.c1000') }]} />
              {hasActiveFilters && <Button type="link" icon={<ReloadOutlined />} onClick={handleResetFilters}>{t('searchTab.resetFilters')}</Button>}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      <Card styles={{ body: { padding: 0 } }}>
        {selectedRowKeys.length > 0 && (
          <div style={{ padding: '12px 16px', background: semanticColors.bgGrayLight, borderBottom: `1px solid ${semanticColors.borderGrayLight}` }}>
            <Space>
              <Text>{t('searchTab.selectedPrefix')} <strong>{selectedRowKeys.length}</strong> {t('searchTab.selectedSuffix')}</Text>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>{t('searchTab.clearSelection')}</Button>
              <Button size="small" onClick={handleCompare} disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}>{t('searchTab.compare', { n: selectedRowKeys.length })}</Button>
              {isAdmin && (
                <Dropdown menu={exportMenu} trigger={['click']}>
                  <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>{t('common:actions.export')} <DownOutlined /></Button>
                </Dropdown>
              )}
            </Space>
          </div>
        )}
        <Spin spinning={searchLoading}>
          <Table
            dataSource={results}
            columns={searchColumns}
            rowKey="talent_id"
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            pagination={{ current: page, pageSize, total, showSizeChanger: false, showTotal: (count) => t('searchTab.totalResults', { n: count }) }}
            onChange={handleTableChange}
            locale={{
              emptyText: query ? (
                <Empty description={t('searchTab.noResultsFor', { query })}>
                  <Button size="small" onClick={handleResetFilters}>{t('searchTab.clearSearch')}</Button>
                </Empty>
              ) : (
                <Empty description={t('searchTab.noData')} />
              ),
            }}
          />
        </Spin>
      </Card>

      {/* Export Confirm Modal */}
      <ExportConfirmModal
        open={exportConfirmVisible}
        onConfirm={handleExportConfirm}
        onCancel={() => { setExportConfirmVisible(false); setPendingExportFormat(null) }}
      />

      {/* Compare Modal */}
      <TalentCompareModal visible={compareModalVisible} talentIds={selectedRowKeys as number[]} onClose={() => setCompareModalVisible(false)} />

      {/* Column Settings Modal */}
      <ColumnSettings visible={columnSettingsVisible} columns={columnConfig} onToggle={toggleColumn} onReset={resetColumns} onClose={() => setColumnSettingsVisible(false)} />

      {/* Save Template Modal */}
      <Modal
        title={t('searchTab.template.title')}
        open={saveTemplateModalVisible}
        onOk={() => {
          if (!newTemplateName.trim()) { message.warning(t('searchTab.template.nameRequired')); return }
          addTemplate(newTemplateName.trim(), { role_type: roleFilter, min_citations: minCitations, sort_by: sortBy, sort_order: sortOrder })
          setNewTemplateName('')
          setSaveTemplateModalVisible(false)
          message.success(t('searchTab.template.saved'))
        }}
        onCancel={() => { setSaveTemplateModalVisible(false); setNewTemplateName('') }}
        okText={t('searchTab.template.save')}
        cancelText={t('common:actions.cancel')}
      >
        <Input placeholder={t('searchTab.template.namePlaceholder')} value={newTemplateName} onChange={(e) => setNewTemplateName(e.target.value)} onPressEnter={() => setSaveTemplateModalVisible(false)} />
      </Modal>
    </>
  )
}

export default SearchTab
