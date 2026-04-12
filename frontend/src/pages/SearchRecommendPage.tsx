/**
 * Search & Recommend Page - v1.4
 *
 * 功能说明：
 * - 人才搜索 Tab: 关键词/语义/混合搜索
 * - 智能推荐 Tab: 包含岗位匹配和相似推荐两种模式
 */
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
  Tabs,
  Progress,
  Alert,
  Descriptions,
  List,
  InputNumber,
  Badge,
} from 'antd'
import {
  SearchOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  DownOutlined,
  DownloadOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  RobotOutlined,
  TeamOutlined,
  PlusOutlined,
  UserAddOutlined,
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
import type { SearchTalent, TechElement, EnhancedSearchResult, JDFeatures, MatchResultItem, RecommendResultItem } from '../types'

const { Title, Text } = Typography
const { Search } = Input
const { TextArea } = Input

// Helper types
interface School { school_id: number; school_name: string }
interface Country { country_code: string; country_name_cn: string }

const SearchRecommendPage: React.FC = () => {
  const navigate = useNavigate()
  const [urlSearchParams] = useSearchParams()
  const initialTab = urlSearchParams.get('tab') || 'search'
  const [activeTab, setActiveTab] = useState(initialTab)

  // 智能推荐子 Tab 状态
  const initialRecommendMode = urlSearchParams.get('mode') || 'jd-match'
  const [recommendMode, setRecommendMode] = useState(initialRecommendMode)

  // ========== Shared State ==========
  const searchInputRef = useRef<InputRef>(null)

  // ========== Search Tab State ==========
  const [query, setQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [results, setResults] = useState<SearchTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20
  const [tookMs, setTookMs] = useState<number | null>(null)
  const [searchModeUsed, setSearchModeUsed] = useState<string | null>(null) // 实际使用的搜索模式
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [schoolFilter, setSchoolFilter] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()
  const [sortBy, setSortBy] = useState<string>('cited_by_count')
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc')
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)
  const [compareModalVisible, setCompareModalVisible] = useState(false)
  const [schools, setSchools] = useState<School[]>([])
  const [countries, setCountries] = useState<Country[]>([])
  const [techElements, setTechElements] = useState<TechElement[]>([])
  const [countryFilter, setCountryFilter] = useState<string | undefined>()
  const [techElementFilter, setTechElementFilter] = useState<number | undefined>()
  const { addTemplate } = useSearchTemplates()
  const [saveTemplateModalVisible, setSaveTemplateModalVisible] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')
  const { columns: columnConfig, toggleColumn, resetColumns } = useColumnConfig()
  const [columnSettingsVisible, setColumnSettingsVisible] = useState(false)

  // ========== JD Match Tab State ==========
  const [jdText, setJdText] = useState('')
  const [jdLoading, setJdLoading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [jdFeatures, setJdFeatures] = useState<JDFeatures | null>(null)
  const [matchResults, setMatchResults] = useState<MatchResultItem[]>([])
  const [jdTookMs, setJdTookMs] = useState<number | null>(null)

  // ========== Recommend Tab State ==========
  const [referenceTalentIds, setReferenceTalentIds] = useState<number[]>([])
  const [referenceTalentNames, setReferenceTalentNames] = useState<Map<number, string>>(new Map())
  const [recommendLimit, setRecommendLimit] = useState(10)
  const [recommendLoading, setRecommendLoading] = useState(false)
  const [talentOptions, setTalentOptions] = useState<SearchTalent[]>([])
  const [searchingTalents, setSearchingTalents] = useState(false)
  const [recommendResults, setRecommendResults] = useState<RecommendResultItem[]>([])
  const [recommendTookMs, setRecommendTookMs] = useState<number | null>(null)

  // ========== Keyboard Shortcuts ==========
  useKeyboardShortcuts([
    { key: '/', action: () => searchInputRef.current?.focus() },
    { key: 'f', ctrlKey: true, action: () => searchInputRef.current?.focus() },
    { key: 'Escape', action: () => { if (compareModalVisible) setCompareModalVisible(false) } },
  ])

  // ========== Load Reference Data ==========
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
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadReferenceData()
  }, [loadReferenceData])

  // Initialize from URL
  useEffect(() => {
    const q = urlSearchParams.get('q')
    if (q) {
      setQuery(q)
      performSearch(q, 1)
    } else {
      loadAllTalents()
    }
  }, [urlSearchParams.get('q')])

  // ========== Search Functions ==========
  const loadAllTalents = async () => {
    setSearchLoading(true)
    try {
      const response = await api.talents.list({ page: 1, page_size: pageSize })
      const items: SearchTalent[] = (response.data.items || []).map((item: SearchTalent) => ({
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
      setTotal(response.data.total || items.length)
      setTookMs(null)
      setPage(1)
    } catch {
      message.error('加载人才列表失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const performSearch = async (searchQuery: string, pageNum: number) => {
    if (!searchQuery.trim()) return loadAllTalents()
    setSearchLoading(true)
    setTookMs(null)
    setSearchModeUsed(null)
    try {
      const response = await api.enhancedSearch.search({
        q: searchQuery.trim(),
        mode: 'hybrid', // 默认使用混合搜索（最强模式）
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
        current_title: item.current_title,
        works_count: item.works_count,
        cited_by_count: item.cited_by_count,
        h_index: item.h_index,
        topic_tags: item.topic_tags || [],
        openalex_topics: item.openalex_topics || [],
      }))
      setResults(items)
      setTotal(response.data.total || items.length)
      setTookMs(response.data.took_ms || null)
      setSearchModeUsed(response.data.mode || 'hybrid')
      setPage(pageNum)
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
    setTechElementFilter(undefined)
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
      const blob = new Blob([response.data], { type: format === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv' })
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
    <Menu items={[{ key: 'csv', label: '导出 CSV' }, { key: 'xlsx', label: '导出 Excel' }]} onClick={(e) => handleExport(e.key as 'csv' | 'xlsx')} />
  )

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning('请选择2-4位候选人进行对比')
      return
    }
    setCompareModalVisible(true)
  }

  // ========== JD Match Functions ==========
  const handleParseJD = async () => {
    if (!jdText.trim()) {
      message.warning('请输入职位描述')
      return
    }
    setParsing(true)
    try {
      const response = await api.jdMatch.parse(jdText)
      setJdFeatures(response.data)
      message.success('JD 解析成功')
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || 'JD 解析失败')
    } finally {
      setParsing(false)
    }
  }

  const handleMatch = async () => {
    if (!jdText.trim()) {
      message.warning('请输入职位描述')
      return
    }
    setJdLoading(true)
    try {
      const response = await api.jdMatch.match({
        jd_text: jdText,
        config: { weights: { skill: 0.4, research: 0.3, experience: 0.2, education: 0.1 }, limit: 20 },
      })
      setMatchResults(response.data.items || [])
      setJdTookMs(response.data.took_ms)
      if (!jdFeatures) {
        const parseResponse = await api.jdMatch.parse(jdText)
        setJdFeatures(parseResponse.data)
      }
      message.success(`找到 ${response.data.total} 位匹配候选人`)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '匹配失败，请检查 LLM 配置')
    } finally {
      setJdLoading(false)
    }
  }

  const handleResetJD = () => {
    setJdText('')
    setJdFeatures(null)
    setMatchResults([])
    setJdTookMs(null)
  }

  // ========== Recommend Functions ==========
  const handleSearchTalents = async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setTalentOptions([])
      return
    }
    setSearchingTalents(true)
    try {
      const response = await api.talents.list({ keyword: searchQuery, page_size: 10 })
      setTalentOptions(response.data.items || [])
    } catch { /* ignore */ }
    finally {
      setSearchingTalents(false)
    }
  }

  const handleAddReferenceTalent = (talentId: number, talentName: string) => {
    if (referenceTalentIds.includes(talentId)) {
      message.warning('该人才已添加')
      return
    }
    if (referenceTalentIds.length >= 10) {
      message.warning('最多添加10位参考人才')
      return
    }
    setReferenceTalentIds([...referenceTalentIds, talentId])
    setReferenceTalentNames(new Map(referenceTalentNames).set(talentId, talentName))
    setTalentOptions([])
  }

  const handleRemoveReferenceTalent = (talentId: number) => {
    setReferenceTalentIds(referenceTalentIds.filter(id => id !== talentId))
    const newNames = new Map(referenceTalentNames)
    newNames.delete(talentId)
    setReferenceTalentNames(newNames)
  }

  const handleGetRecommendations = async () => {
    if (referenceTalentIds.length === 0) {
      message.warning('请至少添加一位参考人才')
      return
    }
    setRecommendLoading(true)
    try {
      const response = await api.recommend.getRecommendations({
        reference_talent_ids: referenceTalentIds,
        limit: recommendLimit,
      })
      setRecommendResults(response.data.items || [])
      setRecommendTookMs(response.data.took_ms)
      message.success(`找到 ${response.data.total} 位推荐候选人`)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '获取推荐失败')
    } finally {
      setRecommendLoading(false)
    }
  }

  const handleResetRecommend = () => {
    setReferenceTalentIds([])
    setReferenceTalentNames(new Map())
    setRecommendResults([])
    setRecommendTookMs(null)
  }

  // ========== Add to Reference (Linkage) ==========
  const handleAddToReference = (talentId: number, talentName: string) => {
    handleAddReferenceTalent(talentId, talentName)
    message.success(`已将 ${talentName} 添加到参考列表`, 2)
  }

  // ========== Table Columns ==========
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
      render: (name: string, record: SearchTalent) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          <Space direction="vertical" size={0}>
            <span>{name}</span>
            {record.name_en && <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>}
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
        name ? <a onClick={() => navigate(`/schools/${record.school_id}`)}>{name}</a> : <Text type="secondary">-</Text>,
    },
    { title: '论文', dataIndex: 'works_count', key: 'works_count', width: 80, align: 'center' as const },
    { title: '引用', dataIndex: 'cited_by_count', key: 'cited_by_count', width: 100, align: 'right' as const, render: (count: number) => count.toLocaleString() },
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
          <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => handleAddToReference(record.talent_id, record.name)}>
            加入参考
          </Button>
        </Tooltip>
      ),
    },
  ]

  const jdColumns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: MatchResultItem, index: number) => <Tag color={index < 3 ? 'gold' : 'default'}>{index + 1}</Tag>,
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: MatchResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    { title: '职位', dataIndex: 'title', key: 'title', width: 150, ellipsis: true },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 150, ellipsis: true },
    {
      title: '综合分数',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 150,
      render: (score: number) => (
        <Progress percent={score} size="small" status={score >= 70 ? 'success' : score >= 50 ? 'normal' : 'exception'} format={(percent) => `${percent?.toFixed(0)}分`} />
      ),
      sorter: (a: MatchResultItem, b: MatchResultItem) => a.overall_score - b.overall_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '匹配技能',
      dataIndex: 'highlight_skills',
      key: 'highlight_skills',
      width: 200,
      render: (skills: string[]) => (
        <Space size={[4, 4]} wrap>
          {skills?.slice(0, 5).map((skill, idx) => <Tag key={idx} color="blue" style={{ margin: 0 }}>{skill}</Tag>)}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: MatchResultItem) => (
        <Button type="link" size="small" icon={<UserAddOutlined />} onClick={() => handleAddToReference(record.talent_id, record.name)}>
          加入参考
        </Button>
      ),
    },
  ]

  const recommendColumns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: unknown, __: RecommendResultItem, index: number) => (
        <Badge count={index + 1} style={{ backgroundColor: index < 3 ? '#faad14' : '#d9d9d9', color: '#fff' }} />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: RecommendResultItem) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>{name}</a>
      ),
    },
    { title: '职位', dataIndex: 'title', key: 'title', width: 150, ellipsis: true },
    { title: '学校', dataIndex: 'school_name', key: 'school_name', width: 150, ellipsis: true },
    {
      title: '相似度',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: 120,
      render: (score: number) => <Tag color={score >= 0.7 ? 'green' : score >= 0.4 ? 'blue' : 'default'}>{(score * 100).toFixed(0)}%</Tag>,
      sorter: (a: RecommendResultItem, b: RecommendResultItem) => a.similarity_score - b.similarity_score,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '推荐原因',
      dataIndex: 'reasons',
      key: 'reasons',
      render: (reasons: string[]) => (
        <List size="small" dataSource={reasons || []} renderItem={(item) => <List.Item style={{ padding: '2px 0', border: 'none' }}><Text type="secondary" style={{ fontSize: 12 }}>• {item}</Text></List.Item>} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: RecommendResultItem) => (
        <Tooltip title="设为参考人才">
          <Button type="text" size="small" icon={<PlusOutlined />} onClick={() => handleAddReferenceTalent(record.talent_id, record.name)} disabled={referenceTalentIds.includes(record.talent_id)} />
        </Tooltip>
      ),
    },
  ]

  // ========== Options ==========
  const countryOptions = countries.map(c => ({ value: c.country_code, label: c.country_name_cn }))
  const schoolOptions = schools.map(s => ({ value: s.school_id, label: s.school_name }))
  const techElementOptions = techElements.map(e => ({ value: e.tech_element_id, label: e.element_name }))

  const sortMenu = (
    <Menu
      onClick={(e) => { const [field, order] = e.key.split('-'); setSortBy(field); setSortOrder(order as 'desc' | 'asc'); performSearch(query, 1) }}
      items={[
        { key: 'cited_by_count-desc', label: '引用数 (高到低)' },
        { key: 'cited_by_count-asc', label: '引用数 (低到高)' },
        { key: 'works_count-desc', label: '论文数 (高到低)' },
        { key: 'works_count-asc', label: '论文数 (低到高)' },
      ]}
    />
  )

  const hasActiveFilters = roleFilter || schoolFilter || minCitations || countryFilter || techElementFilter

  // ========== Tab Change Handler ==========
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'recommend') {
      navigate(`/search-recommend?tab=${key}&mode=${recommendMode}`)
    } else {
      navigate(`/search-recommend?tab=${key}`)
    }
  }

  // ========== Render ==========
  return (
    <div>
      <Title level={3}>
        <SearchOutlined style={{ marginRight: 8 }} />
        搜索推荐
      </Title>

      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        type="card"
        items={[
          {
            key: 'search',
            label: <span><SearchOutlined /> 人才搜索 {tookMs && <Text type="secondary" style={{ fontSize: 12 }}>({tookMs.toFixed(0)}ms)</Text>}</span>,
            children: (
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
                      <Dropdown overlay={sortMenu} trigger={['click']}>
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
                      <Space>
                        <ThunderboltOutlined style={{ color: '#1890ff' }} />
                        <span>
                          智能搜索已启用：
                          {searchModeUsed === 'hybrid' && '混合搜索（关键词 + 语义向量）'}
                          {searchModeUsed === 'semantic' && '语义向量搜索'}
                          {searchModeUsed === 'keyword' && '关键词匹配'}
                          {searchModeUsed === 'fulltext' && '全文检索'}
                        </span>
                      </Space>
                    }
                    type="info"
                    style={{ marginBottom: 16 }}
                    showIcon={false}
                  />
                )}

                {/* Filters */}
                <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
                  <Row gutter={[16, 8]}>
                    <Col span={24}>
                      <Space size={8} wrap>
                        <Text type="secondary">筛选:</Text>
                        <Select placeholder="技术要素" value={techElementFilter} onChange={(val) => { setTechElementFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 140 }} options={techElementOptions} />
                        <Select placeholder="国家" value={countryFilter} onChange={(val) => { setCountryFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 120 }} options={countryOptions} />
                        <Select placeholder="学校" value={schoolFilter} onChange={(val) => { setSchoolFilter(val); performSearch(query, 1) }} allowClear showSearch optionFilterProp="label" style={{ width: 180 }} options={schoolOptions} />
                        <Select placeholder="角色" value={roleFilter} onChange={(val) => { setRoleFilter(val); performSearch(query, 1) }} allowClear style={{ width: 140 }} options={[{ value: 'professor', label: '教授/研究员' }, { value: 'student', label: '学生' }, { value: 'graduated', label: '毕业生' }]} />
                        <Select placeholder="最少引用" value={minCitations} onChange={(val) => { setMinCitations(val); performSearch(query, 1) }} allowClear style={{ width: 120 }} options={[{ value: 100, label: '100次以上' }, { value: 500, label: '500次以上' }, { value: 1000, label: '1000次以上' }]} />
                        {hasActiveFilters && <Button type="link" icon={<ReloadOutlined />} onClick={handleResetFilters}>重置筛选</Button>}
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
                        <Button size="small" onClick={handleCompare} disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}>对比 ({selectedRowKeys.length}/4)</Button>
                        <Dropdown overlay={exportMenu} trigger={['click']}>
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
              </>
            ),
          },
          {
            key: 'recommend',
            label: <span><BulbOutlined /> 智能推荐</span>,
            children: (
              <>
                {/* 智能推荐模式切换 */}
                <Card style={{ marginBottom: 16 }}>
                  <Space>
                    <Text type="secondary">推荐模式:</Text>
                    <Segmented
                      value={recommendMode}
                      onChange={(value) => {
                        setRecommendMode(value as string)
                        navigate(`/search-recommend?tab=recommend&mode=${value}`)
                      }}
                      options={[
                        { value: 'jd-match', label: <span><RobotOutlined /> 岗位匹配</span> },
                        { value: 'similar', label: <span><TeamOutlined /> 相似推荐</span> },
                      ]}
                    />
                  </Space>
                </Card>

                {/* 岗位匹配模式 */}
                {recommendMode === 'jd-match' && (
                  <>
                    <Alert message="输入职位描述(JD)，系统将使用 LLM 解析关键特征并智能匹配合适的人才。需要配置 LLM API Key。" type="info" showIcon style={{ marginBottom: 16 }} />
                    <Card title="职位描述 (JD)" style={{ marginBottom: 16 }}>
                      <TextArea placeholder="请粘贴职位描述内容，包括岗位职责、任职要求、技能要求等..." value={jdText} onChange={(e) => setJdText(e.target.value)} rows={6} showCount maxLength={5000} />
                      <Space style={{ marginTop: 12 }}>
                        <Button type="primary" icon={<SearchOutlined />} onClick={handleMatch} loading={jdLoading}>智能匹配 {jdTookMs && <Text type="secondary">({jdTookMs.toFixed(0)}ms)</Text>}</Button>
                        <Button icon={<BulbOutlined />} onClick={handleParseJD} loading={parsing}>解析 JD</Button>
                        <Button icon={<ReloadOutlined />} onClick={handleResetJD}>重置</Button>
                      </Space>
                    </Card>
                    {jdFeatures && (
                      <Card title="JD 解析结果" style={{ marginBottom: 16 }} size="small">
                        <Descriptions column={2} size="small">
                          <Descriptions.Item label="技能要求">
                            <Space size={[4, 4]} wrap>{jdFeatures.skills?.map((skill, idx) => <Tag key={idx} color="blue">{skill}</Tag>)}</Space>
                          </Descriptions.Item>
                          <Descriptions.Item label="角色类型"><Tag color="purple">{jdFeatures.role_type || '未指定'}</Tag></Descriptions.Item>
                        </Descriptions>
                      </Card>
                    )}
                    <Card title={`匹配结果 (${matchResults.length} 人)`}>
                      <Spin spinning={jdLoading}>
                        {matchResults.length > 0 ? (
                          <Table dataSource={matchResults} columns={jdColumns} rowKey="talent_id" pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 位候选人` }} scroll={{ x: 1200 }} />
                        ) : (
                          <Empty description='请输入职位描述并点击"智能匹配"开始搜索' image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        )}
                      </Spin>
                    </Card>
                  </>
                )}

                {/* 相似推荐模式 */}
                {recommendMode === 'similar' && (
                  <>
                    <Alert message="选择参考人才，系统将推荐研究方向和技能相似的人才。推荐基于预计算的向量嵌入，不调用 LLM。" type="info" showIcon style={{ marginBottom: 16 }} />
                    <Card title="参考人才" style={{ marginBottom: 16 }}>
                      <Row gutter={[16, 16]}>
                        <Col span={24}>
                          <Select
                            showSearch
                            placeholder="搜索人才姓名添加参考..."
                            style={{ width: '100%' }}
                            size="large"
                            value={null}
                            onSearch={handleSearchTalents}
                            onChange={(value, option) => {
                              if (value && option) {
                                // 从 option.label 中提取姓名
                                const label = typeof option.label === 'string' ? option.label : ''
                                const name = label.split(' (')[0]
                                handleAddReferenceTalent(value, name)
                              }
                            }}
                            filterOption={false}
                            loading={searchingTalents}
                            notFoundContent={searchingTalents ? <Spin size="small" /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="输入姓名搜索人才" />}
                            options={talentOptions.map(t => ({ value: t.talent_id, label: `${t.name} (${t.school_name || '未知学校'})` }))}
                          />
                        </Col>
                        <Col span={24}>
                          <Space size={[8, 8]} wrap>
                            {referenceTalentIds.map((id) => (
                              <Tag key={id} closable onClose={() => handleRemoveReferenceTalent(id)} style={{ padding: '4px 8px' }}>
                                {referenceTalentNames.get(id) || `ID: ${id}`}
                              </Tag>
                            ))}
                            {referenceTalentIds.length === 0 && <Text type="secondary">请在上方搜索框输入姓名添加参考人才（最多10位）</Text>}
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                    <Card title="推荐配置" style={{ marginBottom: 16 }}>
                      <Row gutter={[24, 16]} align="middle">
                        <Col>
                          <Space>
                            <Text>推荐数量:</Text>
                            <InputNumber min={1} max={50} value={recommendLimit} onChange={(value) => setRecommendLimit(value ?? 10)} />
                          </Space>
                        </Col>
                        <Col>
                          <Space>
                            <Button type="primary" icon={<BulbOutlined />} onClick={handleGetRecommendations} loading={recommendLoading}>获取推荐 {recommendTookMs && <Text type="secondary">({recommendTookMs.toFixed(0)}ms)</Text>}</Button>
                            <Button icon={<ReloadOutlined />} onClick={handleResetRecommend}>重置</Button>
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                    <Card title={`推荐结果 (${recommendResults.length} 人)`}>
                      <Spin spinning={recommendLoading}>
                        {recommendResults.length > 0 ? (
                          <Table dataSource={recommendResults} columns={recommendColumns} rowKey="talent_id" pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 位候选人` }} />
                        ) : (
                          <Empty description='请添加参考人才并点击"获取推荐"开始' image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        )}
                      </Spin>
                    </Card>
                  </>
                )}
              </>
            ),
          },
        ]}
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
    </div>
  )
}

export default SearchRecommendPage
