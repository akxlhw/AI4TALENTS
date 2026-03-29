/**
 * SearchPage - 人才搜索页面 (重构版)
 *
 * 已拆分的组件:
 * - SearchFilterPanel: 筛选条件面板
 * - SearchResultsTable: 结果表格
 * - SearchTemplateModal: 模板保存弹窗
 */
import { useEffect, useState, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Input,
  InputRef,
  Typography,
  Space,
  Button,
  Dropdown,
  Menu,
  message,
} from 'antd'
import {
  SearchOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import TalentCompareModal from '../components/TalentCompareModal'
import ColumnSettings from '../components/ColumnSettings'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useSearchTemplates } from '../hooks/useSearchTemplates'
import { useColumnConfig } from '../hooks/useColumnConfig'
import type { SearchTalent, TechElement } from '../types'
import {
  SearchFilterPanel,
  SearchResultsTable,
  SearchTemplateModal,
} from '../components/search'
import type { SearchFilterValues } from '../components/search'

const { Title } = Typography
const { Search } = Input

// 页面内部使用的简化类型
interface School {
  school_id: number
  school_name: string
}

interface Country {
  country_id: number
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

  // Filter state (consolidated)
  const [filters, setFilters] = useState<SearchFilterValues>({})

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
  const { templates, addTemplate } = useSearchTemplates()
  const [saveTemplateModalVisible, setSaveTemplateModalVisible] = useState(false)
  const [newTemplateName, setNewTemplateName] = useState('')

  // Column settings
  const { columns: columnConfig, toggleColumn, resetColumns } = useColumnConfig()
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
    } catch (error) {
      console.error('Failed to load reference data:', error)
    }
  }, [])

  useEffect(() => {
    loadReferenceData()
  }, [loadReferenceData])

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery)
      performSearch(initialQuery, 1)
    } else {
      performSearch('', 1)
    }
  }, [initialQuery])

  const performSearch = async (searchQuery: string, pageNum: number) => {
    setLoading(true)
    try {
      const response = await api.talents.list({
        school_id: filters.school_id,
        country_id: filters.country_id,
        role_type: filters.role,
        keyword: searchQuery.trim() || undefined,
        page: pageNum,
        page_size: pageSize,
      })
      const data = response.data

      // Apply client-side filters
      let filteredItems: SearchTalent[] = data.items || []

      if (filters.min_works !== undefined) {
        filteredItems = filteredItems.filter((t) => t.works_count >= filters.min_works!)
      }
      if (filters.min_citations !== undefined) {
        filteredItems = filteredItems.filter((t) => t.cited_by_count >= filters.min_citations!)
      }

      // Apply sorting
      filteredItems.sort((a, b) => {
        let aVal = 0, bVal = 0
        switch (sortBy) {
          case 'works_count':
            aVal = a.works_count
            bVal = b.works_count
            break
          case 'cited_by_count':
            aVal = a.cited_by_count
            bVal = b.cited_by_count
            break
          case 'h_index':
            aVal = a.h_index
            bVal = b.h_index
            break
          default:
            aVal = a.cited_by_count
            bVal = b.cited_by_count
        }
        return sortOrder === 'desc' ? bVal - aVal : aVal - bVal
      })

      setResults(filteredItems)
      setTotal(data.total || filteredItems.length)
      setPage(pageNum)
    } catch (error) {
      console.error('Search failed:', error)
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

  const handleFilterChange = (key: keyof SearchFilterValues, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    performSearch(query, 1)
  }

  const handleResetFilters = () => {
    setFilters({})
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
    } catch (error) {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  const handleCompare = () => {
    if (selectedRowKeys.length < 2 || selectedRowKeys.length > 4) {
      message.warning('请选择2-4位候选人进行对比')
      return
    }
    setCompareModalVisible(true)
  }

  const handleSaveTemplate = () => {
    if (!newTemplateName.trim()) {
      message.warning('请输入模板名称')
      return
    }
    addTemplate(newTemplateName.trim(), {
      role_type: filters.role,
      min_works: filters.min_works,
      min_citations: filters.min_citations,
      sort_by: sortBy,
      sort_order: sortOrder,
    })
    setNewTemplateName('')
    setSaveTemplateModalVisible(false)
    message.success('搜索模板已保存')
  }

  // Options for dropdowns
  const countryOptions = countries.map(c => ({ value: c.country_id, label: c.country_name_cn }))
  const schoolOptions = schools.map(s => ({ value: s.school_id, label: s.school_name }))
  const techElementOptions = techElements.map(e => ({ value: e.tech_element_id, label: e.element_name }))

  const currentElement = techElements.find(e => e.tech_element_id === filters.tech_element_id)
  const directionOptions = (currentElement?.directions || []).map(d => ({
    value: d.tech_direction_id,
    label: d.direction_name
  }))

  const visibleColumns = columnConfig.filter(c => c.visible).map(c => c.key)

  const hasActiveFilters = Object.values(filters).some(v => v !== undefined && v !== '')

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

  return (
    <div>
      <Title level={3}>
        <SearchOutlined style={{ marginRight: 8 }} />
        人才搜索
      </Title>

      {/* Search Box */}
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Search
            ref={searchInputRef}
            placeholder="输入姓名、学校、研究方向等关键词... (按 / 或 Ctrl+F 快速搜索)"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onSearch={handleSearch}
            enterButton="搜索"
            size="large"
            allowClear
            style={{ width: 600 }}
          />
          <Dropdown overlay={sortMenu} trigger={['click']}>
            <Button size="large" icon={sortOrder === 'desc' ? <SortDescendingOutlined /> : <SortAscendingOutlined />}>
              排序 <DownOutlined />
            </Button>
          </Dropdown>
        </Space>
      </Card>

      {/* Enhanced Filters */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
        <SearchFilterPanel
          filters={filters}
          schoolOptions={schoolOptions}
          countryOptions={countryOptions}
          techElementOptions={techElementOptions}
          directionOptions={directionOptions}
          onFilterChange={handleFilterChange}
          onResetFilters={handleResetFilters}
          onOpenColumnSettings={() => setColumnSettingsVisible(true)}
          onOpenTemplateMenu={() => {}}
          templateCount={templates.length}
          hasActiveFilters={hasActiveFilters}
        />
      </Card>

      {/* Results */}
      <Card bodyStyle={{ padding: 0 }}>
        <SearchResultsTable
          results={results}
          loading={loading}
          total={total}
          page={page}
          pageSize={pageSize}
          selectedKeys={selectedRowKeys}
          visibleColumns={visibleColumns}
          onSelectChange={setSelectedRowKeys}
          onRowClick={(id) => navigate(`/talents/${id}`)}
          onSchoolClick={(id) => navigate(`/schools/${id}`)}
          onPageChange={(p) => performSearch(query, p)}
          onExport={handleExport}
          onCompare={handleCompare}
          exporting={exporting}
          searchQuery={query}
        />
      </Card>

      {/* Compare Modal */}
      <TalentCompareModal
        visible={compareModalVisible}
        talentIds={selectedRowKeys as number[]}
        onClose={() => setCompareModalVisible(false)}
      />

      {/* Save Template Modal */}
      <SearchTemplateModal
        visible={saveTemplateModalVisible}
        templateName={newTemplateName}
        filters={filters}
        onNameChange={setNewTemplateName}
        onOk={handleSaveTemplate}
        onCancel={() => {
          setSaveTemplateModalVisible(false)
          setNewTemplateName('')
        }}
      />

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
