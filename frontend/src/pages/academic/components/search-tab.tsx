import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
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
import { getRoleTypeConfig } from '../../../constants/roleType'
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

const SEARCH_STATE_KEY = 'search_state'

const SearchTab: React.FC<SearchTabProps> = ({
  countryOptions,
  schoolOptions,
  techDomainOptions,
  onAddToReference,
}) => {
  const navigate = useNavigate()
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

  // 从 sessionStorage 恢复搜索状态
  const getSavedSearchState = () => {
    try {
      const saved = sessionStorage.getItem(SEARCH_STATE_KEY)
      if (saved) {
        return JSON.parse(saved)
      }
    } catch { /* ignore */ }
    return null
  }

  // Initialize from URL or restore from sessionStorage
  useEffect(() => {
    const savedState = getSavedSearchState()
    const q = urlSearchParams.get('q')

    if (q) {
      if (savedState && savedState.query === q && savedState.results?.length > 0) {
        setQuery(savedState.query)
        setResults(savedState.results)
        setTotal(savedState.total)
        setTookMs(savedState.tookMs)
        setSearchModeUsed(savedState.searchModeUsed)
        setFulltextMatchCount(savedState.fulltextMatchCount || 0)
        setSemanticMatchCount(savedState.semanticMatchCount || 0)
        setPage(savedState.page || 1)
      } else {
        setQuery(q)
        performSearch(q, 1)
      }
    } else if (savedState) {
      setQuery(savedState.query || '')
      setResults(savedState.results || [])
      setTotal(savedState.total || 0)
      setTookMs(savedState.tookMs || null)
      setSearchModeUsed(savedState.searchModeUsed || null)
      setFulltextMatchCount(savedState.fulltextMatchCount || 0)
      setSemanticMatchCount(savedState.semanticMatchCount || 0)
      setPage(savedState.page || 1)
    } else {
      loadAllTalents()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadAllTalents = async (pageNum: number = 1) => {
    setSearchLoading(true)
    try {
      const response = await api.talents.list({ page: pageNum, page_size: pageSize })
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
      message.error('加载人才列表失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const performSearch = async (searchQuery: string, pageNum: number) => {
    if (!searchQuery.trim()) return loadAllTalents(pageNum)
    setSearchLoading(true)
    setTookMs(null)
    setSearchModeUsed(null)
    try {
      const response = await api.enhancedSearch.search({
        q: searchQuery.trim(),
        mode: 'hybrid',
        role_type: roleFilter,
        school_id: schoolFilter,
        min_citations: minCitations,
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

      sessionStorage.setItem(SEARCH_STATE_KEY, JSON.stringify({
        query: searchQuery.trim(),
        results: items,
        total: response.data.total || items.length,
        tookMs: response.data.took_ms || null,
        searchModeUsed: response.data.mode || 'hybrid',
        fulltextMatchCount: response.data.fulltext_count || 0,
        semanticMatchCount: response.data.semantic_count || 0,
        page: pageNum,
      }))
    } catch {
      message.error('搜索失败，请重试')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setQuery(value)
    navigate(`/search-recommend?tab=search${value.trim() ? `&q=${encodeURIComponent(value.trim())}` : ''}`)
    performSearch(value, 1)
  }

  const handleTableChange = (pagination: TablePaginationConfig) => {
    performSearch(query, pagination.current || 1)
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setSchoolFilter(undefined)
    setMinCitations(undefined)
    setCountryFilter(undefined)
    setTechDomainFilter(undefined)
    setSortBy('cited_by_count')
    setSortOrder('desc')
    performSearch(query, 1)
  }

  const handleExportRequest = (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的候选人')
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
      message.success(`已导出 ${selectedRowKeys.length} 位候选人`)
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
      setExportConfirmVisible(false)
      setPendingExportFormat(null)
    }
  }

  const exportMenu = {
    items: [{ key: 'csv', label: '导出 CSV' }, { key: 'xlsx', label: '导出 Excel' }],
    onClick: (e: { key: string }) => handleExportRequest(e.key as 'csv' | 'xlsx'),
  }

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning('请选择2-4位候选人进行对比')
      return
    }
    setCompareModalVisible(true)
  }

  const sortMenu = {
    onClick: (e: { key: string }) => { const [field, order] = e.key.split('-'); setSortBy(field); setSortOrder(order as 'desc' | 'asc'); performSearch(query, 1) },
    items: [
      { key: 'cited_by_count-desc', label: '引用数 (高到低)' },
      { key: 'cited_by_count-asc', label: '引用数 (低到高)' },
      { key: 'works_count-desc', label: '论文数 (高到低)' },
      { key: 'works_count-asc', label: '论文数 (低到高)' },
    ],
  }

  const hasActiveFilters = roleFilter || schoolFilter || minCitations || countryFilter || techDomainFilter

  const searchColumns = [
    {
      title: '收藏',
      key: 'favorite',
      width: 60,
      align: 'center' as const,
      render: (_: unknown, record: SearchTalent) => <FavoriteButton talentId={record.talent_id} size="small" />,
    },
    {
      title: '姓名',
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
            <Tooltip title={`相似推荐 (${percent}%)：该人才研究方向与搜索词语义相近，但非精准匹配`}>
              {nameContent}
            </Tooltip>
          )
        }
        return nameContent
      },
    },
    {
      title: '角色',
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = getRoleTypeConfig(role)
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '院校机构',
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
    { title: '论文', dataIndex: 'works_count', key: 'works_count', width: 80, align: 'center' as const },
    { title: '引用', dataIndex: 'cited_by_count', key: 'cited_by_count', width: 100, align: 'right' as const, render: (count: number) => formatNumber(count) },
    { title: 'H指数', dataIndex: 'h_index', key: 'h_index', width: 80, align: 'center' as const },
    {
      title: '研究方向',
      dataIndex: 'openalex_topics',
      key: 'openalex_topics',
      width: 200,
      render: (topics: string[], record: SearchTalent) => <TopicTags tags={topics && topics.length > 0 ? topics : record.topic_tags} maxVisible={2} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: SearchTalent) => (
        <Tooltip title="添加到智能推荐参考列表">
          <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => onAddToReference(record.talent_id, record.name)}>
            加入参考
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
              placeholder="搜索姓名、研究主题、论文标题... (按 / 快速搜索)"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton="搜索"
              size="large"
              allowClear
            />
          </Col>
          <Col>
            <Dropdown menu={sortMenu} trigger={['click']}>
              <Button size="large" icon={sortOrder === 'desc' ? <SortDescendingOutlined /> : <SortAscendingOutlined />}>
                排序 <DownOutlined />
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
                  智能搜索已启用：
                  {searchModeUsed === 'hybrid' && '混合搜索（关键词 + 语义向量）'}
                  {searchModeUsed === 'semantic' && '语义向量搜索'}
                  {searchModeUsed === 'keyword' && '关键词匹配'}
                  {searchModeUsed === 'fulltext' && '全文检索'}
                </span>
              </Space>
              <span>共 {total} 人</span>
              {(fulltextMatchCount > 0 || semanticMatchCount > 0) && (
                <>
                  {fulltextMatchCount > 0 && (
                    <span style={{ color: semanticColors.orange }}>
                      关键词匹配 {fulltextMatchCount} 人
                    </span>
                  )}
                  {semanticMatchCount > 0 && (
                    <span style={{ color: 'var(--domain-secondary)' }}>
                      语义匹配 {semanticMatchCount} 人
                    </span>
                  )}
                </>
              )}
              <span style={{ color: '#999' }}>耗时 {tookMs.toFixed(0)}ms</span>
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
              <Text type="secondary">筛选:</Text>
              <Select placeholder="技术领域" value={techDomainFilter} onChange={(val) => { setTechDomainFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 140 }} options={techDomainOptions} />
              <Select placeholder="国家" value={countryFilter} onChange={(val) => { setCountryFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 120 }} options={countryOptions} />
              <Select placeholder="院校机构" value={schoolFilter} onChange={(val) => { setSchoolFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 180 }} options={schoolOptions} />
              <Select placeholder="角色" value={roleFilter} onChange={(val) => { setRoleFilter(val); performSearch(query, 1) }} allowClear style={{ width: 140 }} options={[{ value: 'professor', label: '教授/研究员' }, { value: 'student', label: '学生' }, { value: 'graduated', label: '毕业生' }]} />
              <Select placeholder="最少引用" value={minCitations} onChange={(val) => { setMinCitations(val); performSearch(query, 1) }} allowClear style={{ width: 120 }} options={[{ value: 100, label: '100次以上' }, { value: 500, label: '500次以上' }, { value: 1000, label: '1000次以上' }]} />
              {hasActiveFilters && <Button type="link" icon={<ReloadOutlined />} onClick={handleResetFilters}>重置筛选</Button>}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      <Card styles={{ body: { padding: 0 } }}>
        {selectedRowKeys.length > 0 && (
          <div style={{ padding: '12px 16px', background: semanticColors.bgGrayLight, borderBottom: `1px solid ${semanticColors.borderGrayLight}` }}>
            <Space>
              <Text>已选择 <strong>{selectedRowKeys.length}</strong> 项</Text>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>取消选择</Button>
              <Button size="small" onClick={handleCompare} disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}>对比 ({selectedRowKeys.length}/4)</Button>
              <Dropdown menu={exportMenu} trigger={['click']}>
                <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>导出 <DownOutlined /></Button>
              </Dropdown>
            </Space>
          </div>
        )}
        <Spin spinning={searchLoading}>
          <Table
            dataSource={results}
            columns={searchColumns}
            rowKey="talent_id"
            rowSelection={{ selectedRowKeys, onChange: setSelectedRowKeys }}
            pagination={{ current: page, pageSize, total, showSizeChanger: false, showTotal: (t) => `共 ${t} 条结果` }}
            onChange={handleTableChange}
            locale={{ emptyText: <Empty description={query ? `未找到与"${query}"相关的人才` : '暂无人才数据'} /> }}
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
        title="保存搜索模板"
        open={saveTemplateModalVisible}
        onOk={() => {
          if (!newTemplateName.trim()) { message.warning('请输入模板名称'); return }
          addTemplate(newTemplateName.trim(), { role_type: roleFilter, min_citations: minCitations, sort_by: sortBy, sort_order: sortOrder })
          setNewTemplateName('')
          setSaveTemplateModalVisible(false)
          message.success('搜索模板已保存')
        }}
        onCancel={() => { setSaveTemplateModalVisible(false); setNewTemplateName('') }}
        okText="保存"
        cancelText="取消"
      >
        <Input placeholder="输入模板名称..." value={newTemplateName} onChange={(e) => setNewTemplateName(e.target.value)} onPressEnter={() => setSaveTemplateModalVisible(false)} />
      </Modal>
    </>
  )
}

export default SearchTab
