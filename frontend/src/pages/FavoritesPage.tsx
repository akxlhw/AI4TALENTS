import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Select,
  Empty,
  Spin,
  Row,
  Col,
  Input,
  Button,
  Modal,
  message,
  Tooltip,
  Dropdown,
  Menu,
} from 'antd'
import {
  StarFilled,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  DownloadOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import TalentCompareModal from '../components/TalentCompareModal'

const { Title, Text } = Typography

interface FavoriteTalent {
  favorite_id: number
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
  notes: string | null
  created_at: string
}

interface FavoritesResponse {
  items: FavoriteTalent[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

const roleTypeMap: Record<string, { color: string; text: string }> = {
  professor: { color: 'green', text: '教授' },
  student: { color: 'blue', text: '学生' },
  graduated: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
}

const FavoritesPage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [favorites, setFavorites] = useState<FavoriteTalent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Filters
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')

  // Edit notes modal
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingFavorite, setEditingFavorite] = useState<FavoriteTalent | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [editLoading, setEditLoading] = useState(false)

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)

  // Compare state
  const [compareModalVisible, setCompareModalVisible] = useState(false)

  useEffect(() => {
    loadFavorites()
  }, [page, roleFilter, keyword])

  const loadFavorites = async () => {
    setLoading(true)
    try {
      const response = await api.favorites.list({
        page,
        page_size: pageSize,
        role_type: roleFilter,
        keyword: keyword || undefined,
      })
      const data: FavoritesResponse = response.data
      setFavorites(data.items)
      setTotal(data.total)
    } catch (error) {
      console.error('Failed to load favorites:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTableChange = (pagination: any) => {
    setPage(pagination.current)
  }

  const handleSearch = () => {
    setPage(1)
    loadFavorites()
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setKeyword('')
    setPage(1)
  }

  const handleEditNotes = (record: FavoriteTalent) => {
    setEditingFavorite(record)
    setEditNotes(record.notes || '')
    setEditModalVisible(true)
  }

  const handleSaveNotes = async () => {
    if (!editingFavorite) return

    setEditLoading(true)
    try {
      await api.favorites.update(editingFavorite.talent_id, editNotes)
      // Update local state
      setFavorites(prev => prev.map(f =>
        f.favorite_id === editingFavorite.favorite_id
          ? { ...f, notes: editNotes }
          : f
      ))
      setEditModalVisible(false)
      message.success('备注已更新')
    } catch (error) {
      message.error('更新备注失败')
    } finally {
      setEditLoading(false)
    }
  }

  const handleRemoveFavorite = (record: FavoriteTalent) => {
    Modal.confirm({
      title: '取消收藏',
      content: `确定要取消收藏 "${record.name}" 吗？`,
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await api.favorites.remove(record.talent_id)
          setFavorites(prev => prev.filter(f => f.favorite_id !== record.favorite_id))
          setTotal(prev => prev - 1)
          message.success('已取消收藏')
        } catch (error) {
          message.error('取消收藏失败')
        }
      },
    })
  }

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的候选人')
      return
    }

    setExporting(true)
    try {
      // Get talent_ids from selected favorites
      const talentIds = favorites
        .filter(f => selectedRowKeys.includes(f.favorite_id))
        .map(f => f.talent_id)

      const response = await api.talents.export(talentIds, format)
      const blob = new Blob([response.data], {
        type: format === 'xlsx'
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'text/csv'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `favorites_export.${format}`
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

  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: FavoriteTalent) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)} style={{ fontWeight: 500 }}>
          <Space direction="vertical" size={0}>
            <span>
              <StarFilled style={{ color: '#faad14', marginRight: 6 }} />
              {name}
            </span>
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
      render: (name: string, record: FavoriteTalent) =>
        name ? (
          <a onClick={() => record.school_id && navigate(`/schools/${record.school_id}`)}>
            {name}
          </a>
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
    },
    {
      title: '引用',
      dataIndex: 'cited_by_count',
      key: 'cited_by_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      width: 200,
      ellipsis: true,
      render: (notes: string | null) =>
        notes ? (
          <Tooltip title={notes}>
            <Text ellipsis style={{ maxWidth: 180 }}>{notes}</Text>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '收藏时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date: string) => {
        if (!date) return '-'
        const d = new Date(date)
        return d.toLocaleDateString('zh-CN')
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: FavoriteTalent) => (
        <Space size="small">
          <Tooltip title="编辑备注">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditNotes(record)}
            />
          </Tooltip>
          <Tooltip title="取消收藏">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleRemoveFavorite(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>
        <StarFilled style={{ marginRight: 8, color: '#faad14' }} />
        我的收藏
      </Title>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }} bodyStyle={{ padding: '12px 24px' }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space size={8}>
              <Text type="secondary">筛选:</Text>

              <Select
                placeholder="角色"
                value={roleFilter}
                onChange={(val) => { setRoleFilter(val); setPage(1); }}
                allowClear
                style={{ width: 100 }}
                options={[
                  { value: 'professor', label: '教授' },
                  { value: 'student', label: '学生' },
                  { value: 'graduated', label: '毕业生' },
                ]}
              />

              <Input.Search
                placeholder="搜索姓名..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onSearch={handleSearch}
                allowClear
                style={{ width: 200 }}
                enterButton={<SearchOutlined />}
              />

              {(roleFilter || keyword) && (
                <Button type="link" onClick={handleResetFilters}>
                  重置筛选
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Table */}
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
            dataSource={favorites}
            columns={columns}
            rowKey="favorite_id"
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            scroll={{ x: 1200 }}
            pagination={{
              current: page,
              pageSize,
              total: total,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 位收藏`,
            }}
            onChange={handleTableChange}
            locale={{
              emptyText: (
                <Empty
                  description="暂无收藏"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                >
                  <Button type="primary" onClick={() => navigate('/search')}>
                    去搜索人才
                  </Button>
                </Empty>
              ),
            }}
          />
        </Spin>
      </Card>

      {/* Compare Modal */}
      <TalentCompareModal
        visible={compareModalVisible}
        talentIds={favorites.filter(f => selectedRowKeys.includes(f.favorite_id)).map(f => f.talent_id)}
        onClose={() => setCompareModalVisible(false)}
      />

      {/* Edit Notes Modal */}
      <Modal
        title="编辑备注"
        open={editModalVisible}
        onOk={handleSaveNotes}
        onCancel={() => setEditModalVisible(false)}
        confirmLoading={editLoading}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <p style={{ marginBottom: 8 }}>
            <strong>候选人：</strong>{editingFavorite?.name}
          </p>
          <Input.TextArea
            rows={4}
            placeholder="记录关注该候选人的原因..."
            value={editNotes}
            onChange={(e) => setEditNotes(e.target.value)}
            maxLength={500}
            showCount
          />
        </div>
      </Modal>
    </div>
  )
}

export default FavoritesPage
