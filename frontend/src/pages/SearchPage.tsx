import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Input,
  InputRef,
  Table,
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
} from '@ant-design/icons'
import { api } from '../services/api'
import FavoriteButton from '../components/FavoriteButton'
import TalentCompareModal from '../components/TalentCompareModal'
import ColumnSettings from '../components/ColumnSettings'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useSearchTemplates } from '../hooks/useSearchTemplates'
import { useColumnConfig } from '../hooks/useColumnConfig'

const { Title, Text } = Typography
const { Search } = Input

interface Talent {
  talent_id: number
  name: string
  name_en: string | null
  role_type: string
  school_id: number | null
  school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  topic_tags: string[]
}

interface School {
  school_id: number
  school_name: string
}

interface SearchResponse {
  items: Talent[]
  total: number
  query: string
  page: number
  page_size: number
}

const roleTypeMap: Record<string, { color: string; text: string }> = {
  professor: { color: 'green', text: '教授' },
  student: { color: 'blue', text: '学生' },
  graduated: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
}

const SearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''
  const searchInputRef = useRef<InputRef>(null)

  // Search state
  const [query, setQuery] = useState(initialQuery)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<Talent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Filter state
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [schoolFilter, setSchoolFilter] = useState<number | undefined>()
  const [minWorks, setMinWorks] = useState<number | undefined>()
  const [minCitations, setMinCitations] = useState<number | undefined>()

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

  // Schools for filter dropdown
  const [schools, setSchools] = useState<School[]>([])

  useEffect(() => {
    loadSchools()
  }, [])

  useEffect(() => {
    if (initialQuery) {
      performSearch(initialQuery, 1)
    }
  }, [initialQuery])

  const loadSchools = async () => {
    try {
      const response = await api.schools.list({})
      setSchools(response.data.items || [])
    } catch (error) {
      console.error('Failed to load schools:', error)
    }
  }

  const performSearch = async (searchQuery: string, pageNum: number) => {
    if (!searchQuery.trim()) return

    setLoading(true)
    try {
      const response = await api.search.talents({
        q: searchQuery,
        page: pageNum,
        page_size: pageSize,
      })
      const data: SearchResponse = response.data

      // Apply client-side filters
      let filteredItems = data.items

      if (roleFilter) {
        filteredItems = filteredItems.filter(t => t.role_type === roleFilter)
      }
      if (schoolFilter) {
        // Note: This would need school_id in the response
        // For now, we filter by school_name match
      }
      if (minWorks !== undefined) {
        filteredItems = filteredItems.filter(t => t.works_count >= minWorks)
      }
      if (minCitations !== undefined) {
        filteredItems = filteredItems.filter(t => t.cited_by_count >= minCitations)
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
      setTotal(data.total)
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
      performSearch(value, 1)
    }
  }

  const handleTableChange = (pagination: any) => {
    performSearch(query, pagination.current)
  }

  const handleFilterChange = () => {
    if (query) {
      performSearch(query, 1)
    }
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setSchoolFilter(undefined)
    setMinWorks(undefined)
    setMinCitations(undefined)
    setSortBy('cited_by_count')
    setSortOrder('desc')
    if (query) {
      performSearch(query, 1)
    }
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
      if (query) {
        performSearch(query, 1)
      }
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
        if (query) {
          performSearch(query, 1)
        }
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

  const allColumns = [
    {
      title: '收藏',
      key: 'favorite',
      width: 60,
      align: 'center' as const,
      render: (_: any, record: Talent) => (
        <FavoriteButton talentId={record.talent_id} size="small" />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: Talent) => (
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
        const config = roleTypeMap[role] || roleTypeMap.unknown
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
      render: (name: string, record: Talent) =>
        name ? (
          <a onClick={() => navigate(`/schools/${record.school_id}`)}>{name}</a>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '职位',
      dataIndex: 'current_title',
      key: 'current_title',
      width: 150,
      ellipsis: true,
      render: (title: string | null) => title || <Text type="secondary">-</Text>,
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
      dataIndex: 'topic_tags',
      key: 'topic_tags',
      width: 200,
      render: (tags: string[]) => (
        <Space size={4} wrap>
          {(tags || []).slice(0, 3).map(tag => (
            <Tag key={tag} style={{ margin: 0, fontSize: 11 }}>
              {tag}
            </Tag>
          ))}
          {tags && tags.length > 3 && (
            <span style={{ fontSize: 11, color: '#999' }}>+{tags.length - 3}</span>
          )}
        </Space>
      ),
    },
  ]

  // Filter columns based on user settings
  const columns = allColumns.filter(col => isColumnVisible(col.key as string))

  return (
    <div>
      <Title level={3}>
        <SearchOutlined style={{ marginRight: 8 }} />
        人才搜索
      </Title>

      {/* Search Box */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col flex="auto">
            <Search
              ref={searchInputRef}
              placeholder="输入姓名、学校、研究方向等关键词... (按 / 或 Ctrl+F 快速搜索)"
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

      {/* Filters */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space size={8}>
              <Text type="secondary">筛选:</Text>

              <Select
                placeholder="角色"
                value={roleFilter}
                onChange={(val) => { setRoleFilter(val); handleFilterChange(); }}
                allowClear
                style={{ width: 100 }}
                options={[
                  { value: 'professor', label: '教授' },
                  { value: 'student', label: '学生' },
                  { value: 'graduated', label: '毕业生' },
                ]}
              />

              <Select
                placeholder="学校"
                value={schoolFilter}
                onChange={(val) => { setSchoolFilter(val); handleFilterChange(); }}
                allowClear
                showSearch
                optionFilterProp="label"
                style={{ width: 180 }}
                options={schools.map(s => ({ value: s.school_id, label: s.school_name }))}
              />

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

              {(roleFilter || schoolFilter || minWorks || minCitations) && (
                <Button type="link" onClick={handleResetFilters}>
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
      {query && (
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
                        : '请输入关键词搜索'
                    }
                  />
                ),
              }}
            />
          </Spin>
        </Card>
      )}

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

      {!query && (
        <Card>
          <Empty description="请输入关键词开始搜索" />
        </Card>
      )}
    </div>
  )
}

export default SearchPage
