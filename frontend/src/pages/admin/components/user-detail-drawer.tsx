import { Button, Card, Drawer, List, Space, Table, Tabs, Tag, Typography } from 'antd'
import { EditOutlined, HistoryOutlined, SafetyOutlined, UserOutlined } from '@ant-design/icons'
import { formatUTCToLocal } from '../../../utils/datetime'
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
          '用户详情'
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
                  <UserOutlined /> 基本信息
                </span>
              ),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Card size="small">
                    <p>
                      <strong>用户名：</strong>
                      {user.username}
                    </p>
                    <p>
                      <strong>邮箱：</strong>
                      {user.email}
                    </p>
                    <p>
                      <strong>显示名称：</strong>
                      {user.display_name || '-'}
                    </p>
                    <p>
                      <strong>部门：</strong>
                      {user.department || '-'}
                    </p>
                    <p>
                      <strong>工号：</strong>
                      {user.employee_id || '-'}
                    </p>
                    <p>
                      <strong>角色：</strong>
                      {roleTextMap[user.role] || user.role}
                    </p>
                    <p>
                      <strong>状态：</strong>
                      <Tag color={statusColorMap[user.status] || 'default'}>
                        {statusTextMap[user.status] || user.status}
                      </Tag>
                    </p>
                    <p>
                      <strong>注册时间：</strong>
                      {formatUTCToLocal(user.created_at)}
                    </p>
                    <p>
                      <strong>最后登录：</strong>
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
                      编辑信息
                    </Button>
                  </Card>
                </Space>
              ),
            },
            {
              key: 'activities',
              label: (
                <span>
                  <HistoryOutlined /> 活动记录
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
                      title: '时间',
                      dataIndex: 'activity_time',
                      key: 'activity_time',
                      render: (t: string) => formatUTCToLocal(t),
                      width: 180,
                    },
                    {
                      title: '类型',
                      dataIndex: 'activity_type',
                      key: 'activity_type',
                      render: (t: string) => (
                        <Tag color={activityTypeColorMap[t] || 'default'}>
                          {activityTypeTextMap[t] || t}
                        </Tag>
                      ),
                      width: 120,
                    },
                    {
                      title: '描述',
                      dataIndex: 'description',
                      key: 'description',
                    },
                    {
                      title: '操作人',
                      dataIndex: 'actor',
                      key: 'actor',
                      render: (actor: { username: string } | null) =>
                        actor ? actor.username : '系统',
                      width: 120,
                    },
                    {
                      title: 'IP',
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
                  <SafetyOutlined /> 权限范围
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
                    管理权限
                  </Button>
                  <List
                    dataSource={userScopes}
                    renderItem={scope => (
                      <List.Item>
                        <List.Item.Meta
                          title={
                            <Space>
                              <Tag color={scope.scope_type === 'all' ? 'red' : 'blue'}>
                                {scope.scope_type === 'school'
                                  ? '学校'
                                  : scope.scope_type === 'country'
                                    ? '国家'
                                    : scope.scope_type === 'tech_domain'
                                      ? '技术领域'
                                      : '全部'}
                              </Tag>
                              <Text>{scope.scope_value}</Text>
                            </Space>
                          }
                          description={
                            <Text type="secondary">
                              授予于 {formatUTCToLocal(scope.granted_at)}
                              {scope.expires_at && ` | 过期: ${formatUTCToLocal(scope.expires_at)}`}
                            </Text>
                          }
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: '暂无权限' }}
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
