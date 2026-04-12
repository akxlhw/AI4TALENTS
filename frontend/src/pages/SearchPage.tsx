import { useEffect, useState, useRef, useCallback } from 'react'
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
  Menu,
  message,
  Modal,
  Tooltip,
  Segmented,
} from 'antd'
import {
  SearchOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  DownOutlined,
  DownloadOutlined,
  SaveOutlined,
  BookOutlined,
  DeleteOutlined,
  SettingOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import FavoriteButton from '../components/FavoriteButton'
import TalentCompareModal from '../components/TalentCompareModal'
import TopicTags from '../components/TopicTags'
import ColumnSettings from '../components/ColumnSettings'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useSearchTemplates } from '../hooks/useSearchTemplates'
import { useColumnConfig } from '../hooks/useColumnConfig'
import { getRoleTypeConfig } from '../constants/roleType'
import type { SearchTalent, TechElement, SearchMode, EnhancedSearchResult } from '../types'

const { Title, Text } = Typography
const { Search } = Input

// 页面内部使用的简化类型（从API响应派生）
interface School {
  school_id: number
  school_name: string
}

interface Country {
  country_code: string
  country_name_cn: string
}

const SearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''
  const searchInputRef = useRef<InputRef>(null)

  // Search state
  const [query, setQuery] = useState(initialQuery)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<SearchTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // v1.4 Search mode state
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword')
  const [tookMs, setTookMs] = useState<number | null>(null)

  // Filter state - Original
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [schoolFilter, setSchoolFilter] = useState<number | undefined>()
  const [minWorks, setMinWorks] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()

  // Filter state - New for v1.1
  const [countryFilter, setCountryFilter] = useState<string | undefined>()
  const [techElementFilter, setTechElementFilter] = useState<number | undefined>()
  const [isGraduatedFilter, setIsGraduatedFilter] = useState<string | undefined>()
  const [confirmStatusFilter, setConfirmStatusFilter] = useState<string | undefined>()

  // Sort state
  const [sortBy, setSortBy] = useState<string>('cited_by_count')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)

  // Compare state
  const [compareModalVisible, setCompareModalVisible] = useState(false)

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: '/',
      action: () => searchInputRef.current?.focus(),
    },
    {
      key: 'f',
      ctrlKey: true,
      action: () => searchInputRef.current?.focus(),
    },
    {
      key: 'Escape',
      action: () => {
        if (compareModalVisible) {
          setCompareModalVisible(false)
        }
      },
    },
  ])

  // Search templates
  const { templates, addTemplate, removeTemplate } = useSearchTemplates()
  const [saveTemplateModalVisible, setSaveTemplateModalVisible] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')

  // Column settings
  const { columns: columnConfig, toggleColumn, resetColumns, isColumnVisible } = useColumnConfig()
  const [columnSettingsVisible, setColumnSettingsVisible] = useState(false)

  // Data for dropdowns
  const [schools, setSchools] = useState<School[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [techElements, setTechElements] = useState<TechElement[]>([])

  // Load reference data
  const loadReferenceData = useCallback(async () => {
    try {
      const [schoolsRes, countriesRes, techElementsRes] = await Promise.all([
        api.schools.list({}),
        api.countries.list(),
        api.techElements.list(),
      ])
      setSchools(schoolsRes.data.items || [])
      setCountries(countriesRes.data.items || [])
      setTechElements(techElementsRes.data.items || [])
    } catch (err) {
      console.error('Failed to load reference data:', err)
    }
  }, [])

  useEffect(() => {
    loadReferenceData()
  }, [loadReferenceData])

  useEffect(() => {
    // 页面加载时默认加载所有人才列表
    if (initialQuery) {
      setQuery(initialQuery)
      performSearch(initialQuery, 1)
    } else {
      // 没有初始搜索词时，加载所有人才（使用旧版API）
      loadAllTalents()
    }
  }, [initialQuery])

  const loadAllTalents = async () => {
    setLoading(true)
    try {
      const response = await api.talents.list({
        page: 1,
        page_size: pageSize,
      })
      const data = response.data
      const items: SearchTalent[] = (data.items || []).map((item: SearchTalent) => ({
        talent_id: item.talent_id,
        name: item.name,
        name_en: item.name_en,
        role_type: item.role_type,
        school_id: item.school_id,
        school_name: item.school_name,
        current_title: item.current_title,
        works_count: item.works_count,
        cited_by_count: item.cited_by_count,
        h_index: item.h_index,
        topic_tags: item.topic_tags || [],
        openalex_topics: [],
      }))
      setResults(items)
      setTotal(data.total || items.length)
      setTookMs(null)
      setPage(1)
    } catch (err) {
      console.error('Load talents failed:', err)
      message.error('加载人才列表失败')
    } finally {
      setLoading(false)
    }
  }

  const performSearch = async (searchQuery: string, pageNum: number) => {
    // 空查询时使用旧版API加载所有人才
    if (!searchQuery.trim()) {
      return loadAllTalents()
    }

    setLoading(true)
    setTookMs(null)
    try {
      // Use enhanced search API for all modes (keyword, semantic, hybrid)
      const response = await api.enhancedSearch.search({
        q: searchQuery.trim(),
        mode: searchMode,
        role_type: roleFilter,
        school_id: schoolFilter,
        min_citations: minCitations,
        page: pageNum,
        page_size: pageSize,
      })
      const data = response.data

      // Transform results
      const items: SearchTalent[] = (data.items || []).map((item: EnhancedSearchResult) => ({
        talent_id: item.talent_id,
        name: item.name,
        name_en: item.name_en,
        role_type: item.role_type,
        school_id: item.school_id,
        school_name: item.school_name,
        current_title: item.current_title,
        works_count: item.works_count,
        cited_by_count: item.cited_by_count,
        h_index: item.h_index,
        topic_tags: item.topic_tags || [],
        openalex_topics: item.openalex_topics || [],
      }))

      setResults(items)
      setTotal(data.total || items.length)
      setTookMs(data.took_ms || null)
      setPage(pageNum)
    } catch (err) {
      console.error('Search failed:', err)
      message.error('搜索失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value: string) => {
    setQuery(value)
    if (value.trim()) {
      navigate(`/search?q=${encodeURIComponent(value.trim())}`)
    } else {
      navigate('/search')
    }
    performSearch(value, 1)
  }

  const handleTableChange = (pagination: TablePaginationConfig) => {
    performSearch(query, pagination.current || 1)
  }

  const handleFilterChange = () => {
    performSearch(query, 1)
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setSchoolFilter(undefined)
    setMinWorks(undefined)
    setMinCitations(undefined)
    setCountryFilter(undefined)
    setTechElementFilter(undefined)
    setIsGraduatedFilter(undefined)
    setConfirmStatusFilter(undefined)
    setSortBy('cited_by_count')
    setSortOrder('desc')
    performSearch(query, 1)
  }

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的候选人')
      return
    }

    setExporting(true)
    try {
      const response = await api.talents.export(selectedRowKeys as number[], format)
      const blob = new Blob([response.data], {
        type: format === 'xlsx'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'text/csv'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `talents_export.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      message.success(`已导出 ${selectedRowKeys.length} 位候选人`)
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  const exportMenu = (
    <Menu
      items={[
        { key: 'csv', label: '导出 CSV' },
        { key: 'xlsx', label: '导出 Excel' },
      ]}
      onClick={(e) => handleExport(e.key as 'csv' | 'xlsx')}
    />
  )

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning('请选择2-4位候选人进行对比')
      return
    }
    setCompareModalVisible(true)
  }

  // Template handlers
  const handleSaveTemplate = () => {
    if (!newTemplateName.trim()) {
      message.warning('请输入模板名称')
      return
    }
    addTemplate(newTemplateName.trim(), {
      role_type: roleFilter,
      min_works: minWorks,
      min_citations: minCitations,
      sort_by: sortBy,
      sort_order: sortOrder,
    })
    setNewTemplateName('')
    setSaveTemplateModalVisible(false)
    message.success('搜索模板已保存')
  }

  const handleLoadTemplate = (templateId: string) => {
    const template = templates.find(t => t.id === templateId)
    if (template) {
      setRoleFilter(template.filters.role_type)
      setMinWorks(template.filters.min_works)
      setMinCitations(template.filters.min_citations)
      setSortBy(template.filters.sort_by || 'cited_by_count')
      setSortOrder(template.filters.sort_order || 'desc')
      message.success(`已加载模板: ${template.name}`)
      performSearch(query, 1)
    }
  }

  const templateMenu = (
    <Menu
      items={[
        ...templates.map(t => ({
          key: t.id,
          label: (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minWidth: 150 }}>
              <span>{t.name}</span>
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={(e) => {
                  e.stopPropagation()
                  removeTemplate(t.id)
                  message.success('模板已删除')
                }}
              />
            </div>
          ),
        })),
        { type: 'divider' as const },
        { key: 'save', label: '保存当前筛选条件...', icon: <SaveOutlined /> },
      ]}
      onClick={(e) => {
        if (e.key === 'save') {
          setSaveTemplateModalVisible(true)
        } else {
          handleLoadTemplate(e.key)
        }
      }}
    />
  )

  const sortMenu = (
    <Menu
      onClick={(e) => {
        const [field, order] = e.key.split('-')
        setSortBy(field)
        setSortOrder(order as 'desc' | 'asc')
        performSearch(query, 1)
      }}
      items={[
        { key: 'cited_by_count-desc', label: '引用数 (高到低)' },
        { key: 'cited_by_count-asc', label: '引用数 (低到高)' },
        { key: 'works_count-desc', label: '论文数 (高到低)' },
        { key: 'works_count-asc', label: '论文数 (低到高)' },
        { key: 'h_index-desc', label: 'H指数 (高到低)' },
        { key: 'h_index-asc', label: 'H指数 (低到高)' },
      ]}
    />
  )

  // Options for dropdowns
  const countryOptions = countries.map(c => ({ value: c.country_code, label: c.country_name_cn }))
  const schoolOptions = schools.map(s => ({ value: s.school_id, label: s.school_name }))
  const techElementOptions = techElements.map(e => ({ value: e.tech_element_id, label: e.element_name }))

  const isGraduatedOptions = [
    { value: 'yes', label: '已毕业' },
    { value: 'no', label: '在读' },
  ]

  const confirmStatusOptions = [
    { value: 'confirmed', label: '已确认' },
    { value: 'pending', label: '待确认' },
  ]

  const allColumns = [
    {
      title: '收藏',
      key: 'favorite',
      width: 60,
      align: 'center' as const,
      render: (_: unknown, record: SearchTalent) => (
        <FavoriteButton talentId={record.talent_id} size="small" />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: SearchTalent) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          <Space direction="vertical" size={0}>
            <span>{name}</span>
            {record.name_en && (
              <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>
            )}
          </Space>
        </a>
      ),
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
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
      render: (name: string, record: SearchTalent) =>
        name ? (
          <a onClick={() => navigate(`/schools/${record.school_id}`)}>{name}</a>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '论文',
      dataIndex: 'works_count',
      key: 'works_count',
      width: 80,
      align: 'center' as const,
      sorter: true,
    },
    {
      title: '引用',
      dataIndex: 'cited_by_count',
      key: 'cited_by_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count.toLocaleString(),
      sorter: true,
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
      sorter: true,
    },
    {
      title: '研究方向',
      dataIndex: 'openalex_topics',
      key: 'openalex_topics',
      width: 200,
      render: (topics: string[], record: SearchTalent) => {
        // 优先显示 openalex_topics，没有则回退到 topic_tags
        const displayTopics = topics && topics.length > 0 ? topics : record.topic_tags
        return <TopicTags tags={displayTopics} maxVisible={2} />
      },
    },
  ]

  // Filter columns based on user settings
  const columns = allColumns.filter(col => isColumnVisible(col.key as string))

  // Check if any filter is active
  const hasActiveFilters = roleFilter || schoolFilter || minWorks || minCitations ||
    countryFilter || techElementFilter || isGraduatedFilter || confirmStatusFilter

  return (
    <div>
      <Title level={3}>
        <SearchOutlined style={{ marginRight: 8 }} />
        人才搜索
        {tookMs && (
          <Text type="secondary" style={{ fontSize: 14, marginLeft: 12, fontWeight: 'normal' }}>
            耗时 {tookMs.toFixed(0)}ms
          </Text>
        )}
      </Title>

      {/* Search Box */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Search
              ref={searchInputRef}
              placeholder="搜索姓名、研究主题、论文标题... (按 / 或 Ctrl+F 快速搜索)"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton="搜索"
              size="large"
              allowClear
            />
          </Col>
          <Col>
            <Dropdown overlay={sortMenu} trigger={['click']}>
              <Button size="large" icon={sortOrder === 'desc' ? <SortDescendingOutlined /> : <SortAscendingOutlined />}>
                排序 <DownOutlined />
              </Button>
            </Dropdown>
          </Col>
        </Row>

        {/* Search Scope Hint */}
        <Row style={{ marginTop: 8 }}>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>
              搜索范围：姓名、研究主题（如 Graph Neural Networks）、论文标题（如 wav2vec）
            </Text>
          </Col>
        </Row>

        {/* v1.4 Search Mode Selector */}
        <Row style={{ marginTop: 8 }}>
          <Col>
            <Space>
              <Text type="secondary">搜索模式:</Text>
              <Segmented
                value={searchMode}
                onChange={(value) => {
                  setSearchMode(value as SearchMode)
                  if (query.trim()) {
                    performSearch(query, 1)
                  }
                }}
                options={[
                  {
                    value: 'keyword',
                    label: (
                      <Tooltip title="基础关键词匹配，不调用LLM">
                        <Space size={4}>
                          <SearchOutlined />
                          <span>关键词</span>
                        </Space>
                      </Tooltip>
                    ),
                  },
                  {
                    value: 'semantic',
                    label: (
                      <Tooltip title="基于预计算向量的语义相似度搜索">
                        <Space size={4}>
                          <BulbOutlined />
                          <span>语义搜索</span>
                        </Space>
                      </Tooltip>
                    ),
                  },
                  {
                    value: 'hybrid',
                    label: (
                      <Tooltip title="结合关键词和语义搜索的综合模式">
                        <Space size={4}>
                          <ThunderboltOutlined />
                          <span>混合搜索</span>
                        </Space>
                      </Tooltip>
                    ),
                  },
                ]}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Enhanced Filters */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
        <Row gutter={[16, 8]}>
          <Col span={24}>
            <Space size={8} wrap>
              <Text type="secondary">筛选:</Text>

              {/* 技术要素 */}
              <Select
                placeholder="技术要素"
                value={techElementFilter}
                onChange={(val) => { setTechElementFilter(val); handleFilterChange(); }}
                allowClear
                showSearch
                optionFilterProp="label"
                style={{ width: 140 }}
                options={techElementOptions}
              />

              {/* 国家 */}
              <Select
                placeholder="国家"
                value={countryFilter}
                onChange={(val) => { setCountryFilter(val); handleFilterChange(); }}
                allowClear
                showSearch
                optionFilterProp="label"
                style={{ width: 120 }}
                options={countryOptions}
              />

              {/* 学校 */}
              <Select
                placeholder="学校"
                value={schoolFilter}
                onChange={(val) => { setSchoolFilter(val); handleFilterChange(); }}
                allowClear
                showSearch
                optionFilterProp="label"
                style={{ width: 180 }}
                options={schoolOptions}
              />

              {/* 角色 */}
              <Select
                placeholder="角色"
                value={roleFilter}
                onChange={(val) => { setRoleFilter(val); handleFilterChange(); }}
                allowClear
                style={{ width: 140 }}
                options={[
                  { value: 'professor', label: '教授/研究员' },
                  { value: 'student', label: '学生' },
                  { value: 'graduated', label: '毕业生' },
                ]}
              />

              {/* 是否已毕业 */}
              <Select
                placeholder="毕业状态"
                value={isGraduatedFilter}
                onChange={(val) => { setIsGraduatedFilter(val); handleFilterChange(); }}
                allowClear
                style={{ width: 100 }}
                options={isGraduatedOptions}
              />

              {/* 待确认状态 */}
              <Select
                placeholder="确认状态"
                value={confirmStatusFilter}
                onChange={(val) => { setConfirmStatusFilter(val); handleFilterChange(); }}
                allowClear
                style={{ width: 100 }}
                options={confirmStatusOptions}
              />
            </Space>
          </Col>
          <Col span={24}>
            <Space size={8}>
              {/* 最少论文 */}
              <Select
                placeholder="最少论文"
                value={minWorks}
                onChange={(val) => { setMinWorks(val); handleFilterChange(); }}
                allowClear
                style={{ width: 120 }}
                options={[
                  { value: 10, label: '10篇以上' },
                  { value: 50, label: '50篇以上' },
                  { value: 100, label: '100篇以上' },
                ]}
              />

              {/* 最少引用 */}
              <Select
                placeholder="最少引用"
                value={minCitations}
                onChange={(val) => { setMinCitations(val); handleFilterChange(); }}
                allowClear
                style={{ width: 120 }}
                options={[
                  { value: 100, label: '100次以上' },
                  { value: 500, label: '500次以上' },
                  { value: 1000, label: '1000次以上' },
                ]}
              />

              {hasActiveFilters && (
                <Button type="link" icon={<ReloadOutlined />} onClick={handleResetFilters}>
                  重置筛选
                </Button>
              )}

              <Dropdown overlay={templateMenu} trigger={['click']}>
                <Button size="small" icon={<BookOutlined />}>
                  模板 {templates.length > 0 && `(${templates.length})`}
                </Button>
              </Dropdown>

              <Button
                size="small"
                icon={<SettingOutlined />}
                onClick={() => setColumnSettingsVisible(true)}
              >
                列设置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      <Card bodyStyle={{ padding: 0 }}>
        {selectedRowKeys.length > 0 && (
          <div style={{ padding: '12px 16px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
            <Space>
              <Text>已选择 <strong>{selectedRowKeys.length}</strong> 项</Text>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>取消选择</Button>
              <Button
                size="small"
                onClick={handleCompare}
                disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}
              >
                对比 ({selectedRowKeys.length}/4)
              </Button>
              <Dropdown overlay={exportMenu} trigger={['click']}>
                <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                  导出 <DownOutlined />
                </Button>
              </Dropdown>
            </Space>
          </div>
        )}
        <Spin spinning={loading}>
          <Table
            dataSource={results}
            columns={columns}
            rowKey="talent_id"
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{
              current: page,
              pageSize,
              total: total,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 条结果`,
              pageSizeOptions: ['20', '50', '100'],
            }}
            onChange={handleTableChange}
            locale={{
              emptyText: (
                <Empty
                  description={
                    query
                      ? `未找到与"${query}"相关的人才`
                      : '暂无人才数据'
                  }
                />
              ),
            }}
          />
        </Spin>
      </Card>

      {/* Compare Modal */}
      <TalentCompareModal
        visible={compareModalVisible}
        talentIds={selectedRowKeys as number[]}
        onClose={() => setCompareModalVisible(false)}
      />

      {/* Save Template Modal */}
      <Modal
        title="保存搜索模板"
        open={saveTemplateModalVisible}
        onOk={handleSaveTemplate}
        onCancel={() => {
          setSaveTemplateModalVisible(false)
          setNewTemplateName('')
        }}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">将保存当前的筛选条件和排序设置</Text>
        </div>
        <Input
          placeholder="输入模板名称..."
          value={newTemplateName}
          onChange={(e) => setNewTemplateName(e.target.value)}
          onPressEnter={handleSaveTemplate}
        />
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            当前筛选: {[
              roleFilter && `角色=${roleFilter}`,
              techElementFilter && `技术要素`,
              countryFilter && `国家`,
              schoolFilter && `学校`,
              minWorks && `论文≥${minWorks}`,
              minCitations && `引用≥${minCitations}`,
            ].filter(Boolean).join(', ') || '无'}
          </Text>
        </div>
      </Modal>

      {/* Column Settings Modal */}
      <ColumnSettings
        visible={columnSettingsVisible}
        columns={columnConfig}
        onToggle={toggleColumn}
        onReset={resetColumns}
        onClose={() => setColumnSettingsVisible(false)}
      />
    </div>
  )
}

export default SearchPage
