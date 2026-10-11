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
import { useTranslation } from 'react-i18next'
import { semanticColors } from '../../../theme'
import { formatUTCToLocal } from '../../../utils/datetime'
import '../../../i18n/namespaces/admin'
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
  const { t } = useTranslation(['admin', 'common'])
  const columns = [
    {
      title: t('users.table.colUsername'),
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
      title: t('users.table.colEmail'),
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: t('users.table.colEmployeeId'),
      dataIndex: 'employee_id',
      key: 'employee_id',
      render: (id: string | null) => id || '-',
    },
    {
      title: t('users.table.colRole'),
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={roleColorMap[role] || 'default'}>{roleTextMap[role] || role}</Tag>
      ),
    },
    {
      title: t('users.table.colStatus'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColorMap[status] || 'default'}>{statusTextMap[status] || status}</Tag>
      ),
    },
    {
      title: t('users.table.colDefaultView'),
      dataIndex: 'default_view',
      key: 'default_view',
      render: (view: string) => (
        <Tag color={view === 'tech_domain' ? 'blue' : 'green'}>
          {view === 'tech_domain' ? t('users.views.tech_domain') : t('users.views.country_school')}
        </Tag>
      ),
    },
    {
      title: t('users.table.colLastLogin'),
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string | null) => formatUTCToLocal(date),
    },
    {
      title: t('users.table.colActions'),
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
                {t('users.table.approve')}
              </Button>
              <Popconfirm
                title={t('users.table.rejectConfirmTitle')}
                description={t('users.table.rejectConfirmDescription')}
                okText={t('users.table.rejectConfirmOk')}
                cancelText={t('users.table.cancel')}
                okButtonProps={{ danger: true }}
                onConfirm={() => onRejectUser(record.user_id)}
              >
                <Button type="link" size="small" danger>
                  {t('users.table.reject')}
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
                {t('users.table.detail')}
              </Button>
              <Button
                type="link"
                size="small"
                icon={<SafetyOutlined />}
                onClick={() => onManageScopes(record.user_id)}
              >
                {t('users.table.scopes')}
              </Button>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEditUser(record)}
              >
                {t('users.table.edit')}
              </Button>
              <Popconfirm
                title={t('users.table.deactivateConfirm')}
                onConfirm={() => onDeactivateUser(record.user_id)}
                okText={t('users.table.confirm')}
                cancelText={t('users.table.cancel')}
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  {t('users.table.deactivate')}
                </Button>
              </Popconfirm>
              {record.is_active === false && (
                <Popconfirm
                  title={t('users.table.activateConfirm')}
                  onConfirm={() => onActivateUser(record.user_id)}
                  okText={t('users.table.confirm')}
                  cancelText={t('users.table.cancel')}
                >
                  <Button type="link" size="small" style={{ color: '#52c41a' }}>
                    {t('users.table.activate')}
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
              placeholder={t('users.filters.role')}
              allowClear
              style={{ width: 120 }}
              value={roleFilter}
              onChange={v => onRoleFilterChange(v)}
              options={[
                { value: 'user', label: t('users.roles.user') },
                { value: 'admin', label: t('users.roles.admin') },
                { value: 'super_admin', label: t('users.roles.super_admin') },
              ]}
            />
            <Select
              placeholder={t('users.filters.status')}
              allowClear
              style={{ width: 120 }}
              value={statusFilter}
              onChange={v => onStatusFilterChange(v)}
              options={[
                { value: 'active', label: t('users.statuses.active') },
                { value: 'inactive', label: t('users.statuses.inactive') },
                { value: 'pending_approval', label: t('users.statuses.pending_approval') },
              ]}
            />
            <DatePicker.RangePicker
              placeholder={[t('users.filters.registerStart'), t('users.filters.registerEnd')]}
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
                { value: 'created_at', label: t('users.filters.sortByCreatedAt') },
                { value: 'last_login_at', label: t('users.filters.sortByLastLogin') },
                { value: 'username', label: t('users.filters.sortByUsername') },
              ]}
            />
            <Select
              value={sortOrder}
              onChange={v => onSortOrderChange(v)}
              style={{ width: 100 }}
              options={[
                { value: 'desc', label: t('users.filters.orderDesc') },
                { value: 'asc', label: t('users.filters.orderAsc') },
              ]}
            />
          </Space>
        </Card>
      )}

      <Card
        title={
          <Space>
            <UserOutlined />
            <span>{t('users.table.title')}</span>
          </Space>
        }
        extra={
          activeTab === 'all' && (
            <Button type="primary" icon={<PlusOutlined />} onClick={onCreateUser}>
              {t('users.table.create')}
            </Button>
          )
        }
        tabList={[
          { key: 'all', tab: t('users.table.tabAll') },
          { key: 'pending', tab: t('users.table.tabPending') },
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
            showTotal: count => t('users.table.total', { n: count }),
          }}
          onChange={pagination => onPageChange(pagination.current || 1)}
        />
      </Card>
    </>
  )
}

export default UserTableSection
