import { Button, Card, DatePicker, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  SafetyOutlined,
  UserOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { semanticColors } from '../../../theme'
import { formatUTCToLocal } from '../../../utils/datetime'
import { roleColorMap, roleTextMap, statusColorMap, statusTextMap } from './types'
import type { User } from './types'

const { Text } = Typography

type DateRange = [dayjs.Dayjs | null, dayjs.Dayjs | null] | null

interface UserTableSectionProps {
  users: User[]
  total: number
  page: number
  pageSize: number
  loading: boolean
  activeTab: 'all' | 'pending'
  isSuperAdmin: boolean
  roleFilter: string | undefined
  statusFilter: string | undefined
  dateRange: DateRange
  sortBy: string
  sortOrder: string
  onTabChange: (key: 'all' | 'pending') => void
  onPageChange: (page: number) => void
  onRoleFilterChange: (value: string | undefined) => void
  onStatusFilterChange: (value: string | undefined) => void
  onDateRangeChange: (dates: DateRange) => void
  onSortByChange: (value: string) => void
  onSortOrderChange: (value: string) => void
  onCreateUser: () => void
  onApproveUser: (userId: number) => void
  onRejectUser: (userId: number) => void
  onViewDetail: (user: User) => void
  onManageScopes: (userId: number) => void
  onEditUser: (user: User) => void
  onDeactivateUser: (userId: number) => void
  onActivateUser: (userId: number) => void
}

const UserTableSection: React.FC<UserTableSectionProps> = ({
  users,
  total,
  page,
  pageSize,
  loading,
  activeTab,
  isSuperAdmin,
  roleFilter,
  statusFilter,
  dateRange,
  sortBy,
  sortOrder,
  onTabChange,
  onPageChange,
  onRoleFilterChange,
  onStatusFilterChange,
  onDateRangeChange,
  onSortByChange,
  onSortOrderChange,
  onCreateUser,
  onApproveUser,
  onRejectUser,
  onViewDetail,
  onManageScopes,
  onEditUser,
  onDeactivateUser,
  onActivateUser,
}) => {
  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (name: string, record: User) => (
        <Space>
          <UserOutlined />
          <span>{name}</span>
          {record.display_name && <Text type="secondary">({record.display_name})</Text>}
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '工号',
      dataIndex: 'employee_id',
      key: 'employee_id',
      render: (id: string | null) => id || '-',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={roleColorMap[role] || 'default'}>{roleTextMap[role] || role}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColorMap[status] || 'default'}>{statusTextMap[status] || status}</Tag>
      ),
    },
    {
      title: '默认视角',
      dataIndex: 'default_view',
      key: 'default_view',
      render: (view: string) => (
        <Tag color={view === 'tech_domain' ? 'blue' : 'green'}>
          {view === 'tech_domain' ? '技术领域' : '国家院校'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string | null) => formatUTCToLocal(date),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: User) => (
        <Space>
          {record.status === 'pending_approval' && isSuperAdmin ? (
            <>
              <Button
                type="link"
                size="small"
                style={{ color: semanticColors.green }}
                onClick={() => onApproveUser(record.user_id)}
              >
                通过
              </Button>
              <Popconfirm
                title="确认拒绝该用户的注册申请？"
                description="拒绝后该账号将无法登录"
                okText="确认拒绝"
                cancelText="取消"
                okButtonProps={{ danger: true }}
                onConfirm={() => onRejectUser(record.user_id)}
              >
                <Button type="link" size="small" danger>
                  拒绝
                </Button>
              </Popconfirm>
            </>
          ) : (
            <>
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onViewDetail(record)}
              >
                详情
              </Button>
              <Button
                type="link"
                size="small"
                icon={<SafetyOutlined />}
                onClick={() => onManageScopes(record.user_id)}
              >
                权限
              </Button>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEditUser(record)}
              >
                编辑
              </Button>
              <Popconfirm
                title="确定要禁用该用户吗？"
                onConfirm={() => onDeactivateUser(record.user_id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  禁用
                </Button>
              </Popconfirm>
              {record.is_active === false && (
                <Popconfirm
                  title="确定要启用该用户吗？"
                  onConfirm={() => onActivateUser(record.user_id)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button type="link" size="small" style={{ color: '#52c41a' }}>
                    启用
                  </Button>
                </Popconfirm>
              )}
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <>
      {/* Filter Bar */}
      {activeTab === 'all' && (
        <Card style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="角色"
              allowClear
              style={{ width: 120 }}
              value={roleFilter}
              onChange={v => onRoleFilterChange(v)}
              options={[
                { value: 'user', label: '普通用户' },
                { value: 'admin', label: '管理员' },
                { value: 'super_admin', label: '超级管理员' },
              ]}
            />
            <Select
              placeholder="状态"
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={v => onStatusFilterChange(v)}
              options={[
                { value: 'active', label: '正常' },
                { value: 'inactive', label: '已禁用' },
                { value: 'pending_approval', label: '待审核' },
              ]}
            />
            <DatePicker.RangePicker
              placeholder={['注册开始', '注册结束']}
              value={dateRange as [dayjs.Dayjs, dayjs.Dayjs] | null}
              onChange={dates =>
                onDateRangeChange(
                  dates as unknown as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null
                )
              }
            />
            <Select
              value={sortBy}
              onChange={v => onSortByChange(v)}
              style={{ width: 140 }}
              options={[
                { value: 'created_at', label: '注册时间' },
                { value: 'last_login_at', label: '最后登录' },
                { value: 'username', label: '用户名' },
              ]}
            />
            <Select
              value={sortOrder}
              onChange={v => onSortOrderChange(v)}
              style={{ width: 100 }}
              options={[
                { value: 'desc', label: '降序' },
                { value: 'asc', label: '升序' },
              ]}
            />
          </Space>
        </Card>
      )}

      <Card
        title={
          <Space>
            <UserOutlined />
            <span>用户管理</span>
          </Space>
        }
        extra={
          activeTab === 'all' && (
            <Button type="primary" icon={<PlusOutlined />} onClick={onCreateUser}>
              新建用户
            </Button>
          )
        }
        tabList={[
          { key: 'all', tab: '全部用户' },
          { key: 'pending', tab: '待审核' },
        ]}
        activeTabKey={activeTab}
        onTabChange={key => onTabChange(key as 'all' | 'pending')}
      >
        <Table
          dataSource={users}
          columns={columns}
          rowKey="user_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: false,
            showTotal: t => `共 ${t} 个用户`,
          }}
          onChange={pagination => onPageChange(pagination.current || 1)}
        />
      </Card>
    </>
  )
}

export default UserTableSection
