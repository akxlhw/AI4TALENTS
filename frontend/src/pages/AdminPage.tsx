import { useEffect, useState } from 'react'
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
  Badge,
  Tabs,
  List,
} from 'antd'
import {
  UserOutlined,
  DeleteOutlined,
  EditOutlined,
  SafetyOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

const { Text } = Typography

interface User {
  user_id: number
  username: string
  email: string
  role: string
  display_name: string | null
  department: string | null
  is_active: boolean
  default_view: string
  last_login_at: string | null
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

const AdminPage: React.FC = () => {
  const { isSuperAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  // User modal state
  const [userModalVisible, setUserModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [userForm] = Form.useForm()

  // Scope modal state
  const [scopeModalVisible, setScopeModalVisible] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [userScopes, setUserScopes] = useState<Scope[]>([])
  const [scopeForm] = Form.useForm()

  const pageSize = 10

  useEffect(() => {
    loadUsers()
  }, [page])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const response = await api.admin.listUsers({ page, page_size: pageSize })
      setUsers(response.data.items)
      setTotal(response.data.total)
    } catch {
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
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

  const handleSaveUser = async (values: any) => {
    try {
      if (editingUser) {
        await api.admin.updateUser(editingUser.user_id, values)
        message.success('用户更新成功')
      } else {
        await api.admin.createUser(values)
        message.success('用户创建成功')
      }
      setUserModalVisible(false)
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleDeactivateUser = async (userId: number) => {
    try {
      await api.admin.deactivateUser(userId)
      message.success('用户已禁用')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
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

  const handleAddScope = async (values: any) => {
    if (!selectedUserId) return

    try {
      await api.admin.addUserScope(selectedUserId, {
        user_id: selectedUserId,
        ...values,
      })
      message.success('权限添加成功')
      scopeForm.resetFields()
      // Reload scopes
      const response = await api.admin.getUserScopes(selectedUserId)
      setUserScopes(response.data.items)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加失败')
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
    } catch (error: any) {
      message.error(error.response?.data?.detail || '移除失败')
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
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Badge
          status={active ? 'success' : 'error'}
          text={active ? '正常' : '已禁用'}
        />
      ),
    },
    {
      title: '默认视角',
      dataIndex: 'default_view',
      key: 'default_view',
      render: (view: string) => (
        <Tag color={view === 'tech_element' ? 'blue' : 'green'}>
          {view === 'tech_element' ? '技术要素' : '国家院校'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string | null) =>
        date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: User) => (
        <Space>
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
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title={
          <Space>
            <UserOutlined />
            <span>用户管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateUser}>
            新建用户
          </Button>
        }
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
                { value: 'tech_element', label: '技术要素' },
                { value: 'country_school', label: '国家院校' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

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
                                : scope.scope_type === 'tech_element'
                                ? '技术要素'
                                : '全部'}
                            </Tag>
                            <Text>{scope.scope_value}</Text>
                          </Space>
                        }
                        description={
                          <Text type="secondary">
                            授予于 {new Date(scope.granted_at).toLocaleString()}
                            {scope.expires_at &&
                              ` | 过期: ${new Date(scope.expires_at).toLocaleString()}`}
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
                        { value: 'tech_element', label: '技术要素' },
                        { value: 'all', label: '全部' },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item
                    name="scope_value"
                    label="权限值"
                    rules={[{ required: true }]}
                    extra="学校ID、国家代码(如US、CN)、技术要素ID 或 * (全部)"
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
