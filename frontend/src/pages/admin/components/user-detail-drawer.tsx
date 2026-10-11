import { Button, Card, Drawer, List, Space, Table, Tabs, Tag, Typography } from 'antd'
import { EditOutlined, HistoryOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { formatUTCToLocal } from '../../../utils/datetime'
import '../../../i18n/namespaces/admin'
import {
  activityTypeColorMap,
  activityTypeTextMap,
  roleColorMap,
  roleTextMap,
  statusColorMap,
  statusTextMap,
} from './types'
import type { ActivityItem, Scope, User } from './types'

const { Text } = Typography

interface UserDetailDrawerProps {
  open: boolean
  user: User | null
  activeTab: string
  activities: ActivityItem[]
  activitiesLoading: boolean
  activitiesTotal: number
  activitiesPage: number
  userScopes: Scope[]
  onClose: () => void
  onTabChange: (key: string) => void
  onActivitiesPageChange: (page: number) => void
  onEditUser: (user: User) => void
  onManageScopes: (userId: number) => void
}

const UserDetailDrawer: React.FC<UserDetailDrawerProps> = ({
  open,
  user,
  activeTab,
  activities,
  activitiesLoading,
  activitiesTotal,
  activitiesPage,
  userScopes,
  onClose,
  onTabChange,
  onActivitiesPageChange,
  onEditUser,
  onManageScopes,
}) => {
  const { t } = useTranslation(['admin', 'common'])
  return (
    <Drawer
      title={
        user ? (
          <Space>
            <UserOutlined />
            <span>{user.username}</span>
            <Tag color={roleColorMap[user.role] || 'default'}>
              {roleTextMap[user.role] || user.role}
            </Tag>
          </Space>
        ) : (
          t('users.detail.title')
        )
      }
      width={720}
      open={open}
      onClose={onClose}
    >
      {user && (
        <Tabs
          activeKey={activeTab}
          onChange={onTabChange}
          items={[
            {
              key: 'profile',
              label: (
                <span>
                  <UserOutlined /> {t('users.detail.tabProfile')}
                </span>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Card size="small">
                    <p>
                      <strong>{t('users.detail.username')}</strong>
                      {user.username}
                    </p>
                    <p>
                      <strong>{t('users.detail.email')}</strong>
                      {user.email}
                    </p>
                    <p>
                      <strong>{t('users.detail.displayName')}</strong>
                      {user.display_name || '-'}
                    </p>
                    <p>
                      <strong>{t('users.detail.department')}</strong>
                      {user.department || '-'}
                    </p>
                    <p>
                      <strong>{t('users.detail.employeeId')}</strong>
                      {user.employee_id || '-'}
                    </p>
                    <p>
                      <strong>{t('users.detail.role')}</strong>
                      {roleTextMap[user.role] || user.role}
                    </p>
                    <p>
                      <strong>{t('users.detail.status')}</strong>
                      <Tag color={statusColorMap[user.status] || 'default'}>
                        {statusTextMap[user.status] || user.status}
                      </Tag>
                    </p>
                    <p>
                      <strong>{t('users.detail.createdAt')}</strong>
                      {formatUTCToLocal(user.created_at)}
                    </p>
                    <p>
                      <strong>{t('users.detail.lastLogin')}</strong>
                      {formatUTCToLocal(user.last_login_at)}
                    </p>
                    <Button
                      type="primary"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        onClose()
                        onEditUser(user)
                      }}
                    >
                      {t('users.detail.editInfo')}
                    </Button>
                  </Card>
                </Space>
              ),
            },
            {
              key: 'activities',
              label: (
                <span>
                  <HistoryOutlined /> {t('users.detail.tabActivities')}
                </span>
              ),
              children: (
                <Table
                  dataSource={activities}
                  rowKey="activity_id"
                  loading={activitiesLoading}
                  pagination={{
                    current: activitiesPage,
                    pageSize: 10,
                    total: activitiesTotal,
                    showSizeChanger: false,
                  }}
                  onChange={p => onActivitiesPageChange(p.current || 1)}
                  columns={[
                    {
                      title: t('users.detail.colTime'),
                      dataIndex: 'activity_time',
                      key: 'activity_time',
                      render: (time: string) => formatUTCToLocal(time),
                      width: 180,
                    },
                    {
                      title: t('users.detail.colType'),
                      dataIndex: 'activity_type',
                      key: 'activity_type',
                      render: (type: string) => (
                        <Tag color={activityTypeColorMap[type] || 'default'}>
                          {activityTypeTextMap[type] || type}
                        </Tag>
                      ),
                      width: 120,
                    },
                    {
                      title: t('users.detail.colDescription'),
                      dataIndex: 'description',
                      key: 'description',
                    },
                    {
                      title: t('users.detail.colActor'),
                      dataIndex: 'actor',
                      key: 'actor',
                      render: (actor: { username: string } | null) =>
                        actor ? actor.username : t('users.detail.system'),
                      width: 120,
                    },
                    {
                      title: t('users.detail.colIp'),
                      dataIndex: 'ip',
                      key: 'ip',
                      render: (ip: string | null) => ip || '-',
                      width: 140,
                    },
                  ]}
                />
              ),
            },
            {
              key: 'scopes',
              label: (
                <span>
                  <SafetyOutlined /> {t('users.detail.tabScopes')}
                </span>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => {
                      onClose()
                      onManageScopes(user.user_id)
                    }}
                  >
                    {t('users.detail.manageScopes')}
                  </Button>
                  <List
                    dataSource={userScopes}
                    renderItem={scope => (
                      <List.Item>
                        <List.Item.Meta
                          title={
                            <Space>
                              <Tag color={scope.scope_type === 'all' ? 'red' : 'blue'}>
                                {t(`users.detail.scopeTypes.${scope.scope_type}`, {
                                  defaultValue: scope.scope_type,
                                })}
                              </Tag>
                              <Text>{scope.scope_value}</Text>
                            </Space>
                          }
                          description={
                            <Text type="secondary">
                              {t('users.detail.grantedAt', {
                                time: formatUTCToLocal(scope.granted_at),
                              })}
                              {scope.expires_at &&
                                ` | ${t('users.detail.expiresAt', { time: formatUTCToLocal(scope.expires_at) })}`}
                            </Text>
                          }
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: t('users.detail.noScopes') }}
                  />
                </Space>
              ),
            },
          ]}
        />
      )}
    </Drawer>
  )
}

export default UserDetailDrawer
