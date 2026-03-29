/**
 * FavoriteTalentTable - 收藏人才表格组件
 *
 * 职责：
 * - 显示收藏的人才列表
 * - 支持筛选和搜索
 * - 提供操作按钮（加入人才池、编辑备注、取消收藏）
 */
import { Table, Typography, Tag, Space, Select, Input, Button, Empty, Spin, Dropdown, Tooltip } from 'antd'
import { StarFilled, EditOutlined, DeleteOutlined, SearchOutlined, DownloadOutlined, DownOutlined, FolderOutlined } from '@ant-design/icons'
import type { FavoriteTalent, FollowupStatus } from '../../types'
import { getRoleTypeConfig } from '../../constants/roleType'

const { Text } = Typography

// Follow-up status display config
const followupStatusMap: Record<string, { color: string; text: string }> = {
  new_found: { color: 'blue', text: '新发现' },
  reviewed: { color: 'cyan', text: '已审阅' },
  followed: { color: 'green', text: '已跟进' },
  pending_evaluation: { color: 'orange', text: '待评估' },
  recommend_contact: { color: 'purple', text: '推荐联系' },
  no_followup: { color: 'default', text: '暂不跟进' },
}

export interface FavoriteTalentTableProps {
  data: FavoriteTalent[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  selectedKeys: React.Key[]
  followupStatuses: FollowupStatus[]
  // Filter state
  roleFilter: string | undefined
  keyword: string
  followupFilter: string | undefined
  // Callbacks
  onSelectChange: (keys: React.Key[]) => void
  onPageChange: (page: number) => void
  onSearch: () => void
  onResetFilters: () => void
  onRoleFilterChange: (value: string | undefined) => void
  onKeywordChange: (value: string) => void
  onFollowupFilterChange: (value: string | undefined) => void
  onEditNotes: (record: FavoriteTalent) => void
  onRemoveFavorite: (record: FavoriteTalent) => void
  onUpdateFollowupStatus: (talentId: number, status: string) => void
  onAddToPool: (record: FavoriteTalent) => void
  onTalentClick: (talentId: number) => void
  onSchoolClick: (schoolId: number) => void
  onExport: (format: 'csv' | 'xlsx') => void
  onCompare: () => void
  exporting: boolean
}

const FavoriteTalentTable: React.FC<FavoriteTalentTableProps> = ({
  data,
  loading,
  total,
  page,
  pageSize,
  selectedKeys,
  followupStatuses,
  roleFilter,
  keyword,
  followupFilter,
  onSelectChange,
  onPageChange,
  onSearch,
  onResetFilters,
  onRoleFilterChange,
  onKeywordChange,
  onFollowupFilterChange,
  onEditNotes,
  onRemoveFavorite,
  onUpdateFollowupStatus,
  onAddToPool,
  onTalentClick,
  onSchoolClick,
  onExport,
  onCompare,
  exporting,
}) => {
  const hasActiveFilters = roleFilter || keyword || followupFilter

  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: FavoriteTalent) => (
        <a onClick={() => onTalentClick(record.talent_id)} style={{ fontWeight: 500 }}>
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
          <a onClick={() => record.school_id && onSchoolClick(record.school_id)}>
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
        const config = followupStatusMap[status] || { color: 'default', text: status }
        return (
          <Dropdown
            trigger={['click']}
            menu={{
              items: followupStatuses.map(s => ({
                key: s.value,
                label: s.label,
              })),
              onClick: (e) => onUpdateFollowupStatus(record.talent_id, e.key),
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
      render: (_: unknown, record: FavoriteTalent) => (
        <Space size="small">
          <Tooltip title="加入人才池">
            <Button
              type="text"
              size="small"
              icon={<FolderOutlined />}
              onClick={() => onAddToPool(record)}
            />
          </Tooltip>
          <Tooltip title="编辑备注">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEditNotes(record)}
            />
          </Tooltip>
          <Tooltip title="取消收藏">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onRemoveFavorite(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const exportMenu = {
    items: [
      { key: 'csv', label: '导出 CSV' },
      { key: 'xlsx', label: '导出 Excel' },
    ],
    onClick: (e: { key: string }) => onExport(e.key as 'csv' | 'xlsx'),
  }

  return (
    <div>
      {/* Filters */}
      <div style={{ marginBottom: 16, padding: '12px 24px', background: '#fafafa', borderRadius: 4 }}>
        <Space size={8}>
          <Text type="secondary">筛选:</Text>

          <Select
            placeholder="角色"
            value={roleFilter}
            onChange={onRoleFilterChange}
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
            onChange={onFollowupFilterChange}
            allowClear
            style={{ width: 120 }}
            options={followupStatuses}
          />

          <Input.Search
            placeholder="搜索姓名..."
            value={keyword}
            onChange={(e) => onKeywordChange(e.target.value)}
            onSearch={onSearch}
            allowClear
            style={{ width: 200 }}
            enterButton={<SearchOutlined />}
          />

          {hasActiveFilters && (
            <Button type="link" onClick={onResetFilters}>
              重置筛选
            </Button>
          )}
        </Space>
      </div>

      {/* Selection Actions */}
      {selectedKeys.length > 0 && (
        <div style={{ padding: '12px 16px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', marginBottom: 16 }}>
          <Space>
            <Text>已选择 <strong>{selectedKeys.length}</strong> 项</Text>
            <Button size="small" onClick={() => onSelectChange([])}>取消选择</Button>
            <Button
              size="small"
              onClick={onCompare}
              disabled={selectedKeys.length < 2 || selectedKeys.length > 4}
            >
              对比 ({selectedKeys.length}/4)
            </Button>
            <Dropdown menu={exportMenu} trigger={['click']}>
              <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                导出 <DownOutlined />
              </Button>
            </Dropdown>
          </Space>
        </div>
      )}

      {/* Table */}
      <Spin spinning={loading}>
        <Table
          dataSource={data}
          columns={columns}
          rowKey="favorite_id"
          rowSelection={{
            selectedRowKeys: selectedKeys,
            onChange: onSelectChange,
          }}
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize,
            total: total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 位收藏`,
          }}
          onChange={(pagination) => onPageChange(pagination.current || 1)}
          locale={{
            emptyText: (
              <Empty
                description="暂无收藏"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Spin>
    </div>
  )
}

export default FavoriteTalentTable
