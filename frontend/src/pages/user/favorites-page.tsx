import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
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
  Input,
  Button,
  Modal,
  message,
  Tooltip,
  Dropdown,
  Tabs,
} from 'antd'
import {
  StarFilled,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  DownloadOutlined,
  DownOutlined,
  PlusOutlined,
  FolderOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import TalentCompareModal from '../../components/TalentCompareModal'
import { semanticColors } from '../../theme'
import { getRoleTypeConfig, getFollowupStatusConfig } from '../../constants'
import type { FavoriteTalent, TalentPool, FollowupStatus } from '../../types'

const { Title, Text } = Typography

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
  const [followupFilter, setFollowupFilter] = useState<string | undefined>()

  // Talent pools
  const [pools, setPools] = useState<TalentPool[]>([])
  const [poolsLoading, setPoolsLoading] = useState(false)
  const [createPoolModalVisible, setCreatePoolModalVisible] = useState(false)
  const [newPoolName, setNewPoolName] = useState('')
  const [newPoolDesc, setNewPoolDesc] = useState('')
  const [createPoolLoading, setCreatePoolLoading] = useState(false)

  // Followup statuses
  const [followupStatuses, setFollowupStatuses] = useState<FollowupStatus[]>([])

  // Edit notes modal
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingFavorite, setEditingFavorite] = useState<FavoriteTalent | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [editLoading, setEditLoading] = useState(false)

  // Add to pool modal
  const [addToPoolModalVisible, setAddToPoolModalVisible] = useState(false)
  const [addingToPoolFavorite, setAddingToPoolFavorite] = useState<FavoriteTalent | null>(null)
  const [selectedPoolId, setSelectedPoolId] = useState<number | undefined>()

  // Selection state
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [exporting, setExporting] = useState(false)

  // Compare state
  const [compareModalVisible, setCompareModalVisible] = useState(false)

  // Active tab
  const [activeTab, setActiveTab] = useState('favorites')

  const loadFavorites = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.favorites.list({
        page,
        page_size: pageSize,
        role_type: roleFilter,
        keyword: keyword || undefined,
      })
      setFavorites(response.data.items || [])
      setTotal(response.data.total || 0)
    } catch {
      console.error("Operation failed")
    } finally {
      setLoading(false)
    }
  }, [page, roleFilter, keyword])

  const loadPools = useCallback(async () => {
    setPoolsLoading(true)
    try {
      const response = await api.talentPools.list()
      setPools(response.data.items || [])
    } catch {
      console.error("Operation failed")
    } finally {
      setPoolsLoading(false)
    }
  }, [])

  const loadFollowupStatuses = useCallback(async () => {
    try {
      const response = await api.talentPools.getFollowupStatuses()
      setFollowupStatuses(response.data || [])
    } catch {
      console.error("Operation failed")
    }
  }, [])

  useEffect(() => {
    loadFavorites()
    loadPools()
    loadFollowupStatuses()
  }, [loadFavorites, loadPools, loadFollowupStatuses])

  const handleTableChange = (pagination: TablePaginationConfig) => {
    setPage(pagination.current || 1)
  }

  const handleSearch = () => {
    setPage(1)
    loadFavorites()
  }

  const handleResetFilters = () => {
    setRoleFilter(undefined)
    setKeyword('')
    setFollowupFilter(undefined)
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
      setFavorites(prev => prev.map(f =>
        f.favorite_id === editingFavorite.favorite_id
          ? { ...f, notes: editNotes }
          : f
      ))
      setEditModalVisible(false)
      message.success('备注已更新')
    } catch {
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
        } catch {
          message.error('取消收藏失败')
        }
      },
    })
  }

  const handleUpdateFollowupStatus = async (talentId: number, status: string) => {
    try {
      await api.talentPools.updateFollowupStatus(talentId, status)
      setFavorites(prev => prev.map(f =>
        f.talent_id === talentId ? { ...f, followup_status: status } : f
      ))
      message.success('跟进状态已更新')
    } catch {
      message.error('更新失败')
    }
  }

  const handleCreatePool = async () => {
    if (!newPoolName.trim()) {
      message.warning('请输入人才池名称')
      return
    }

    setCreatePoolLoading(true)
    try {
      await api.talentPools.create({
        pool_name: newPoolName.trim(),
        scope_desc: newPoolDesc || undefined,
      })
      message.success('人才池已创建')
      setCreatePoolModalVisible(false)
      setNewPoolName('')
      setNewPoolDesc('')
      loadPools()
    } catch {
      message.error('创建失败')
    } finally {
      setCreatePoolLoading(false)
    }
  }

  const handleAddToPool = async () => {
    if (!selectedPoolId || !addingToPoolFavorite) return

    try {
      await api.talentPools.addMember(selectedPoolId, addingToPoolFavorite.talent_id)
      message.success('已加入人才池')
      setAddToPoolModalVisible(false)
      setSelectedPoolId(undefined)
      setAddingToPoolFavorite(null)
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        message.warning(axiosError.response.data.detail)
      } else {
        message.error('加入失败')
      }
    }
  }

  const handleExport = async (format: 'csv' | 'xlsx') => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的候选人')
      return
    }

    setExporting(true)
    try {
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
    } catch {
      message.error('导出失败')
    } finally {
      setExporting(false)
    }
  }

  const exportMenu = {
    items: [
      { key: 'csv', label: '导出 CSV' },
      { key: 'xlsx', label: '导出 Excel' },
    ],
    onClick: (e: { key: string }) => handleExport(e.key as 'csv' | 'xlsx'),
  }

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
              <StarFilled style={{ color: semanticColors.gold, marginRight: 6 }} />
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
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '跟进状态',
      dataIndex: 'followup_status',
      key: 'followup_status',
      width: 120,
      render: (status: string, record: FavoriteTalent) => {
        const config = getFollowupStatusConfig(status)
        return (
          <Dropdown
            trigger={['click']}
            menu={{
              items: followupStatuses.map(s => ({
                key: s.value,
                label: s.label,
              })),
              onClick: (e) => handleUpdateFollowupStatus(record.talent_id, e.key),
            }}
          >
            <Tag color={config.color} style={{ cursor: 'pointer' }}>
              {config.text} <DownOutlined style={{ marginLeft: 4, fontSize: 10 }} />
            </Tag>
          </Dropdown>
        )
      },
    },
    {
      title: '备注',
      dataIndex: 'notes',
      key: 'notes',
      width: 150,
      ellipsis: true,
      render: (notes: string | null) =>
        notes ? (
          <Tooltip title={notes}>
            <Text ellipsis style={{ maxWidth: 130 }}>{notes}</Text>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right' as const,
      render: (_record: FavoriteTalent, record: FavoriteTalent) => (
        <Space size="small">
          <Tooltip title="加入人才池">
            <Button
              type="text"
              size="small"
              icon={<FolderOutlined />}
              onClick={() => {
                setAddingToPoolFavorite(record)
                setAddToPoolModalVisible(true)
              }}
            />
          </Tooltip>
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
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={3}>
        <StarFilled style={{ marginRight: 8, color: semanticColors.gold }} />
        我的收藏
      </Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'favorites',
          label: <><StarFilled /> 收藏列表</>,
          children: (
            <>
              {/* Filters */}
              <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '12px 24px' } }}>
                <Row gutter={16} align="middle">
                  <Col>
                    <Space size={8}>
                      <Text type="secondary">筛选:</Text>

                      <Select
                        placeholder="角色"
                        value={roleFilter}
                        onChange={(val) => { setRoleFilter(val); setPage(1); }}
                        allowClear
                        style={{ width: 140 }}
                        options={[
                          { value: 'professor', label: '教授/研究员' },
                          { value: 'student', label: '学生' },
                          { value: 'graduated', label: '毕业生' },
                        ]}
                      />

                      <Select
                        placeholder="跟进状态"
                        value={followupFilter}
                        onChange={(val) => { setFollowupFilter(val); setPage(1); }}
                        allowClear
                        style={{ width: 120 }}
                        options={followupStatuses}
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

                      {(roleFilter || keyword || followupFilter) && (
                        <Button type="link" onClick={handleResetFilters}>
                          重置筛选
                        </Button>
                      )}
                    </Space>
                  </Col>
                </Row>
              </Card>

              {/* Table */}
              <Card styles={{ body: { padding: 0 } }}>
                {selectedRowKeys.length > 0 && (
                  <div style={{ padding: '12px 16px', background: semanticColors.bgGrayLight, borderBottom: `1px solid ${semanticColors.borderGrayLight}` }}>
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
                      <Dropdown menu={exportMenu} trigger={['click']}>
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
                    scroll={{ x: 1000 }}
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
            </>
          ),
        },
        {
          key: 'pools',
          label: <><FolderOutlined /> 人才池</>,
          children: (
            <Card>
              <div style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreatePoolModalVisible(true)}
                >
                  创建人才池
                </Button>
              </div>

              <Spin spinning={poolsLoading}>
                {pools.length > 0 ? (
                  <Row gutter={[16, 16]}>
                    {pools.map(pool => (
                      <Col span={8} key={pool.pool_id}>
                        <Card
                          hoverable
                          onClick={() => navigate(`/pools/${pool.pool_id}`)}
                        >
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Text strong style={{ fontSize: 16 }}>
                              <FolderOutlined style={{ marginRight: 8 }} />
                              {pool.pool_name}
                            </Text>
                            {pool.scope_desc && (
                              <Text type="secondary" ellipsis>
                                {pool.scope_desc}
                              </Text>
                            )}
                            <div>
                              <Tag color="blue">
                                <TeamOutlined style={{ marginRight: 4 }} />
                                {pool.member_count} 人
                              </Tag>
                              <Tag>{pool.pool_type === 'custom' ? '自定义' : pool.pool_type}</Tag>
                            </div>
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                ) : (
                  <Empty description="暂无人才池">
                    <Button type="primary" onClick={() => setCreatePoolModalVisible(true)}>
                      创建人才池
                    </Button>
                  </Empty>
                )}
              </Spin>
            </Card>
          ),
        },
      ]} />

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

      {/* Create Pool Modal */}
      <Modal
        title="创建人才池"
        open={createPoolModalVisible}
        onOk={handleCreatePool}
        onCancel={() => {
          setCreatePoolModalVisible(false)
          setNewPoolName('')
          setNewPoolDesc('')
        }}
        confirmLoading={createPoolLoading}
        okText="创建"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">人才池可以帮助您分类管理关注的候选人</Text>
        </div>
        <Input
          placeholder="人才池名称"
          value={newPoolName}
          onChange={(e) => setNewPoolName(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        <Input.TextArea
          placeholder="描述（可选）"
          value={newPoolDesc}
          onChange={(e) => setNewPoolDesc(e.target.value)}
          rows={3}
        />
      </Modal>

      {/* Add to Pool Modal */}
      <Modal
        title="加入人才池"
        open={addToPoolModalVisible}
        onOk={handleAddToPool}
        onCancel={() => {
          setAddToPoolModalVisible(false)
          setSelectedPoolId(undefined)
          setAddingToPoolFavorite(null)
        }}
        okText="加入"
        cancelText="取消"
        okButtonProps={{ disabled: !selectedPoolId }}
      >
        <div style={{ marginBottom: 16 }}>
          <Text>将 <strong>{addingToPoolFavorite?.name}</strong> 加入人才池：</Text>
        </div>
        <Select
          placeholder="选择人才池"
          value={selectedPoolId}
          onChange={setSelectedPoolId}
          style={{ width: '100%' }}
          options={pools.map(p => ({ value: p.pool_id, label: `${p.pool_name} (${p.member_count}人)` }))}
        />
        {pools.length === 0 && (
          <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
            暂无人才池，请先创建
          </Text>
        )}
      </Modal>
    </div>
  )
}

export default FavoritesPage
