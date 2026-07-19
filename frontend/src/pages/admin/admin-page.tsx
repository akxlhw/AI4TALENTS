import { useCallback, useEffect, useState } from 'react'
import { semanticColors } from '../../theme'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  List,
  Tabs,
  Drawer,
  DatePicker,
} from 'antd'
import {
  UserOutlined,
  DeleteOutlined,
  EditOutlined,
  SafetyOutlined,
  PlusOutlined,
  EyeOutlined,
  HistoryOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { api } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'
import { formatUTCToLocal } from '../../utils/datetime'

const { Text } = Typography

interface User {
  user_id: number
  username: string
  email: string
  role: string
  display_name: string | null
  department: string | null
  is_active: boolean
  status: string
  employee_id: string | null
  default_view: string
  last_login_at: string | null
  created_at: string | null
}

interface ActivityItem {
  activity_id: number
  activity_time: string
  activity_type: string
  actor: { user_id: number; username: string } | null
  target_user_id: number
  description: string
  detail: Record<string, unknown>
  ip: string | null
  status: string
}

interface Scope {
  scope_id: number
  user_id: number
  scope_type: string
  scope_value: string
  granted_by: number
  granted_at: string
  expires_at: string | null
  is_active: boolean
  notes: string | null
}

const roleColorMap: Record<string, string> = {
  super_admin: 'red',
  admin: 'orange',
  user: 'blue',
}

const roleTextMap: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}

const statusColorMap: Record<string, string> = {
  pending_approval: 'orange',
  active: 'green',
  inactive: 'red',
  rejected: 'default',
}

const statusTextMap: Record<string, string> = {
  pending_approval: '待审核',
  active: '正常',
  inactive: '已禁用',
  rejected: '已拒绝',
}

const AdminPage: React.FC = () => {
  const { isSuperAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  // User modal state
  const [activeTab, setActiveTab] = useState<'all' | 'pending'>('all')
  const [userModalVisible, setUserModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [userForm] = Form.useForm()

  // Scope modal state
  const [scopeModalVisible, setScopeModalVisible] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [userScopes, setUserScopes] = useState<Scope[]>([])
  const [scopeForm] = Form.useForm()

  // Filter state
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<string>('desc')

  // Detail drawer state
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [detailUser, setDetailUser] = useState<User | null>(null)
  const [detailTab, setDetailTab] = useState<string>('profile')
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [activitiesLoading, setActivitiesLoading] = useState(false)
  const [activitiesTotal, setActivitiesTotal] = useState(0)
  const [activitiesPage, setActivitiesPage] = useState(1)

  const pageSize = 10

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (activeTab === 'pending') {
        params.status = 'pending_approval'
      }
      if (roleFilter) {
        params.role = roleFilter
      }
      if (statusFilter && activeTab !== 'pending') {
        params.status = statusFilter
      }
      if (dateRange && dateRange[0]) {
        params.created_after = dateRange[0].format('YYYY-MM-DDTHH:mm:ss')
      }
      if (dateRange && dateRange[1]) {
        params.created_before = dateRange[1].format('YYYY-MM-DDTHH:mm:ss')
      }
      const response = await api.admin.listUsers(params)
      setUsers(response.data.items)
      setTotal(response.data.total)
    } catch {
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, activeTab, roleFilter, statusFilter, dateRange, sortBy, sortOrder])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleApproveUser = async (userId: number) => {
    try {
      await api.admin.approveUser(userId)
      message.success('用户已通过')
      loadUsers()
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '操作失败')
    }
  }

  const handleRejectUser = async (userId: number) => {
    try {
      await api.admin.rejectUser(userId)
      message.success('用户已拒绝')
      loadUsers()
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '操作失败')
    }
  }

  const handleCreateUser = () => {
    setEditingUser(null)
    userForm.resetFields()
    setUserModalVisible(true)
  }

  const handleEditUser = (user: User) => {
    setEditingUser(user)
    userForm.setFieldsValue({
      display_name: user.display_name,
      department: user.department,
      role: user.role,
      default_view: user.default_view,
    })
    setUserModalVisible(true)
  }

  const handleSaveUser = async (values: Record<string, unknown>) => {
    try {
      if (editingUser) {
        await api.admin.updateUser(editingUser.user_id, values)
        message.success('用户更新成功')
      } else {
        await api.admin.createUser(values as Parameters<typeof api.admin.createUser>[0])
        message.success('用户创建成功')
      }
      setUserModalVisible(false)
      loadUsers()
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '操作失败')
    }
  }

  const handleDeactivateUser = async (userId: number) => {
    try {
      await api.admin.deactivateUser(userId)
      message.success('用户已禁用')
      loadUsers()
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '操作失败')
    }
  }

  const handleManageScopes = async (userId: number) => {
    setSelectedUserId(userId)
    try {
      const response = await api.admin.getUserScopes(userId)
      setUserScopes(response.data.items)
    } catch {
      message.error('加载权限失败')
    }
    setScopeModalVisible(true)
  }

  const handleViewDetail = async (user: User) => {
    setDetailUser(user)
    setDetailDrawerVisible(true)
    setDetailTab('profile')
    setActivitiesPage(1)
    await loadActivities(user.user_id, 1)
  }

  const loadActivities = async (userId: number, pageNum: number) => {
    setActivitiesLoading(true)
    try {
      const response = await api.admin.getUserActivities(userId, {
        page: pageNum,
        page_size: 10,
      })
      setActivities(response.data.items)
      setActivitiesTotal(response.data.total)
      setActivitiesPage(pageNum)
    } catch {
      message.error('加载活动记录失败')
    } finally {
      setActivitiesLoading(false)
    }
  }

  const activityTypeColorMap: Record<string, string> = {
    login: 'blue',
    login_failure: 'red',
    profile_update: 'orange',
    role_change: 'purple',
    account_activated: 'green',
    account_deactivated: 'red',
    account_created: 'cyan',
    account_approved: 'green',
    account_rejected: 'red',
    scope_grant: 'geekblue',
    scope_revoke: 'magenta',
    password_change: 'gold',
    other: 'default',
  }

  const activityTypeTextMap: Record<string, string> = {
    login: '登录',
    login_failure: '登录失败',
    profile_update: '信息更新',
    role_change: '角色变更',
    account_activated: '账号启用',
    account_deactivated: '账号禁用',
    account_created: '账号创建',
    account_approved: '注册通过',
    account_rejected: '注册拒绝',
    scope_grant: '权限授予',
    scope_revoke: '权限移除',
    password_change: '密码重置',
    other: '其他',
  }

  const handleAddScope = async (values: Record<string, unknown>) => {
    if (!selectedUserId) return

    try {
      await api.admin.addUserScope(selectedUserId, {
        ...values as Omit<Parameters<typeof api.admin.addUserScope>[1], 'user_id'>,
      })
      message.success('权限添加成功')
      scopeForm.resetFields()
      // Reload scopes
      const response = await api.admin.getUserScopes(selectedUserId)
      setUserScopes(response.data.items)
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '添加失败')
    }
  }

  const handleRemoveScope = async (scopeId: number) => {
    if (!selectedUserId) return

    try {
      await api.admin.removeUserScope(selectedUserId, scopeId)
      message.success('权限已移除')
      // Reload scopes
      const response = await api.admin.getUserScopes(selectedUserId)
      setUserScopes(response.data.items)
    } catch (error: unknown) {
      const detail = error instanceof Error && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined
      message.error(detail || '移除失败')
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (name: string, record: User) => (
        <Space>
          <UserOutlined />
          <span>{name}</span>
          {record.display_name && (
            <Text type="secondary">({record.display_name})</Text>
          )}
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
        <Tag color={roleColorMap[role] || 'default'}>
          {roleTextMap[role] || role}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColorMap[status] || 'default'}>
          {statusTextMap[status] || status}
        </Tag>
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
                onClick={() => handleApproveUser(record.user_id)}
              >
                通过
              </Button>
              <Popconfirm
                title="确认拒绝该用户的注册申请？"
                description="拒绝后该账号将无法登录"
                okText="确认拒绝"
                cancelText="取消"
                okButtonProps={{ danger: true }}
                onConfirm={() => handleRejectUser(record.user_id)}
              >
                <Button
                  type="link"
                  size="small"
                  danger
                >
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
                onClick={() => handleViewDetail(record)}
              >
                详情
              </Button>
              <Button
                type="link"
                size="small"
                icon={<SafetyOutlined />}
                onClick={() => handleManageScopes(record.user_id)}
              >
                权限
              </Button>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEditUser(record)}
              >
                编辑
              </Button>
              <Popconfirm
                title="确定要禁用该用户吗？"
                onConfirm={() => handleDeactivateUser(record.user_id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  禁用
                </Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* Filter Bar */}
      {activeTab === 'all' && (
        <Card style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="角色"
              allowClear
              style={{ width: 120 }}
              value={roleFilter}
              onChange={(v) => { setRoleFilter(v); setPage(1) }}
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
              onChange={(v) => { setStatusFilter(v); setPage(1) }}
              options={[
                { value: 'active', label: '正常' },
                { value: 'inactive', label: '已禁用' },
                { value: 'pending_approval', label: '待审核' },
              ]}
            />
            <DatePicker.RangePicker
              placeholder={['注册开始', '注册结束']}
              value={dateRange as [dayjs.Dayjs, dayjs.Dayjs] | null}
              onChange={(dates) => { setDateRange(dates as unknown as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null); setPage(1) }}
            />
            <Select
              value={sortBy}
              onChange={(v) => { setSortBy(v); setPage(1) }}
              style={{ width: 140 }}
              options={[
                { value: 'created_at', label: '注册时间' },
                { value: 'last_login_at', label: '最后登录' },
                { value: 'username', label: '用户名' },
              ]}
            />
            <Select
              value={sortOrder}
              onChange={(v) => { setSortOrder(v); setPage(1) }}
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
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateUser}>
              新建用户
            </Button>
          )
        }
        tabList={[
          { key: 'all', tab: '全部用户' },
          { key: 'pending', tab: '待审核' },
        ]}
        activeTabKey={activeTab}
        onTabChange={(key) => {
          setActiveTab(key as 'all' | 'pending')
          setPage(1)
        }}
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
            showTotal: (t) => `共 ${t} 个用户`,
          }}
          onChange={(pagination) => setPage(pagination.current || 1)}
        />
      </Card>

      {/* User Edit/Create Modal */}
      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={userModalVisible}
        onCancel={() => setUserModalVisible(false)}
        onOk={() => userForm.submit()}
      >
        <Form form={userForm} layout="vertical" onFinish={handleSaveUser}>
          {!editingUser && (
            <>
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="email"
                label="邮箱"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入有效的邮箱地址' },
                ]}
              >
                <Input />
              </Form.Item>
              <Form.Item
                name="password"
                label="密码"
                rules={[
                  { required: true, message: '请输入密码' },
                  { min: 8, message: '密码至少8位' },
                ]}
              >
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="display_name" label="显示名称">
            <Input />
          </Form.Item>
          <Form.Item name="department" label="部门">
            <Input />
          </Form.Item>
          {isSuperAdmin && (
            <Form.Item name="role" label="角色">
              <Select
                options={[
                  { value: 'user', label: '普通用户' },
                  { value: 'admin', label: '管理员' },
                  { value: 'super_admin', label: '超级管理员' },
                ]}
              />
            </Form.Item>
          )}
          <Form.Item name="default_view" label="默认视角">
            <Select
              options={[
                { value: 'tech_domain', label: '技术领域' },
                { value: 'country_school', label: '国家院校' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* User Detail Drawer */}
      <Drawer
        title={
          detailUser ? (
            <Space>
              <UserOutlined />
              <span>{detailUser.username}</span>
              <Tag color={roleColorMap[detailUser.role] || 'default'}>
                {roleTextMap[detailUser.role] || detailUser.role}
              </Tag>
            </Space>
          ) : '用户详情'
        }
        width={720}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {detailUser && (
          <Tabs
            activeKey={detailTab}
            onChange={setDetailTab}
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
                      <p><strong>用户名：</strong>{detailUser.username}</p>
                      <p><strong>邮箱：</strong>{detailUser.email}</p>
                      <p><strong>显示名称：</strong>{detailUser.display_name || '-'}</p>
                      <p><strong>部门：</strong>{detailUser.department || '-'}</p>
                      <p><strong>工号：</strong>{detailUser.employee_id || '-'}</p>
                      <p><strong>角色：</strong>{roleTextMap[detailUser.role] || detailUser.role}</p>
                      <p><strong>状态：</strong>
                        <Tag color={statusColorMap[detailUser.status] || 'default'}>
                          {statusTextMap[detailUser.status] || detailUser.status}
                        </Tag>
                      </p>
                      <p><strong>注册时间：</strong>{formatUTCToLocal(detailUser.created_at)}</p>
                      <p><strong>最后登录：</strong>{formatUTCToLocal(detailUser.last_login_at)}</p>
                      <Button
                        type="primary"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => {
                          setDetailDrawerVisible(false)
                          handleEditUser(detailUser)
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
                    onChange={(p) => {
                      if (detailUser) {
                        loadActivities(detailUser.user_id, p.current || 1)
                      }
                    }}
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
                        setDetailDrawerVisible(false)
                        handleManageScopes(detailUser.user_id)
                      }}
                    >
                      管理权限
                    </Button>
                    <List
                      dataSource={userScopes}
                      renderItem={(scope) => (
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

      {/* Scope Management Modal */}
      <Modal
        title="权限管理"
        open={scopeModalVisible}
        onCancel={() => setScopeModalVisible(false)}
        footer={null}
        width={600}
      >
        <Tabs
          items={[
            {
              key: 'current',
              label: '当前权限',
              children: (
                <List
                  dataSource={userScopes}
                  renderItem={(scope) => (
                    <List.Item
                      actions={[
                        <Popconfirm
                          key="remove"
                          title="确定移除此权限？"
                          onConfirm={() => handleRemoveScope(scope.scope_id)}
                          okText="确定"
                          cancelText="取消"
                        >
                          <Button type="link" danger size="small">
                            移除
                          </Button>
                        </Popconfirm>,
                      ]}
                    >
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
                            {scope.expires_at &&
                              ` | 过期: ${formatUTCToLocal(scope.expires_at)}`}
                          </Text>
                        }
                      />
                    </List.Item>
                  )}
                  locale={{ emptyText: '暂无权限' }}
                />
              ),
            },
            {
              key: 'add',
              label: '添加权限',
              children: (
                <Form form={scopeForm} layout="vertical" onFinish={handleAddScope}>
                  <Form.Item
                    name="scope_type"
                    label="权限类型"
                    rules={[{ required: true }]}
                  >
                    <Select
                      options={[
                        { value: 'school', label: '学校' },
                        { value: 'country', label: '国家' },
                        { value: 'tech_domain', label: '技术领域' },
                        { value: 'all', label: '全部' },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item
                    name="scope_value"
                    label="权限值"
                    rules={[{ required: true }]}
                    extra="学校ID、国家代码(如US、CN)、技术领域ID 或 * (全部)"
                  >
                    <Input placeholder="如: 1, US, 1, *" />
                  </Form.Item>
                  <Form.Item name="notes" label="备注">
                    <Input.TextArea rows={2} />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit">
                      添加权限
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  )
}

export default AdminPage
