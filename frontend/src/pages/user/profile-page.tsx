import { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Typography,
  Descriptions,
  Avatar,
  Space,
} from 'antd'
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  SafetyOutlined,
  SecurityScanOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { semanticColors } from '../../theme'
import { useNavigate } from 'react-router-dom'

const { Title, Text } = Typography

interface UserInfo {
  user_id: number
  username: string
  email: string
  role: string
  display_name: string | null
  department: string | null
  is_active: boolean
  last_login_at: string | null
  privacy_policy_accepted_at: string | null
  privacy_policy_version: string | null
  terms_of_use_accepted_at: string | null
  terms_of_use_version: string | null
  storage_consent_level: string
}

const roleMap: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}

const ProfilePage: React.FC = () => {
  const navigate = useNavigate()
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    loadUserInfo()
  }, [])

  const loadUserInfo = async () => {
    setLoading(true)
    try {
      const response = await api.auth.me()
      setUser(response.data)
    } catch {
      message.error('获取用户信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handlePasswordChange = async (values: {
    currentPassword: string
    newPassword: string
    confirmPassword: string
  }) => {
    if (values.newPassword !== values.confirmPassword) {
      message.error('两次输入的新密码不一致')
      return
    }

    setPasswordLoading(true)
    try {
      await api.auth.changePassword(values.currentPassword, values.newPassword)
      message.success('密码修改成功')
      form.resetFields()
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      message.error(axiosError.response?.data?.detail || '密码修改失败')
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <div style={{ padding: '88px 32px 80px', maxWidth: 800, margin: '0 auto' }}>
      <Title level={3}>
        <UserOutlined style={{ marginRight: 8 }} />
        个人信息
      </Title>

      {/* User Info Card */}
      <Card loading={loading} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
          <Avatar size={64} icon={<UserOutlined />} style={{ backgroundColor: semanticColors.blue }} />
          <div style={{ marginLeft: 16 }}>
            <Title level={4} style={{ margin: 0 }}>
              {user?.display_name || user?.username}
            </Title>
            <Text type="secondary">@{user?.username}</Text>
          </div>
        </div>

        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="用户名">{user?.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">
            <MailOutlined style={{ marginRight: 8 }} />
            {user?.email}
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            <SafetyOutlined style={{ marginRight: 8 }} />
            {user?.role ? roleMap[user.role] || user.role : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="部门">{user?.department || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            {user?.is_active ? (
              <Text type="success">正常</Text>
            ) : (
              <Text type="danger">已禁用</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="最后登录">
            {user?.last_login_at
              ? new Date(user.last_login_at).toLocaleString('zh-CN')
              : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Change Password Card */}
      <Card title={<><LockOutlined style={{ marginRight: 8 }} />修改密码</>} style={{ marginBottom: 24 }}>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          为保障账户安全，建议定期更换密码（密码长度至少8位）
        </Text>

        <Form
          form={form}
          layout="vertical"
          onFinish={handlePasswordChange}
          style={{ maxWidth: 400 }}
        >
          <Form.Item
            name="currentPassword"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password placeholder="请输入当前密码" />
          </Form.Item>

          <Form.Item
            name="newPassword"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 8, message: '密码长度至少8位' },
            ]}
          >
            <Input.Password placeholder="请输入新密码（至少8位）" />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={passwordLoading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Privacy & Data Card */}
      <Card title={<><SecurityScanOutlined style={{ marginRight: 8 }} />隐私与数据</>}>
        <Descriptions column={2} bordered size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="隐私政策">
            {user?.privacy_policy_accepted_at ? (
              <Text type="success">
                已同意（版本 {user.privacy_policy_version || '-'}）
              </Text>
            ) : (
              <Text type="warning">未同意</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="同意时间">
            {user?.privacy_policy_accepted_at
              ? new Date(user.privacy_policy_accepted_at).toLocaleString('zh-CN')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="用户协议">
            {user?.terms_of_use_accepted_at ? (
              <Text type="success">
                已同意（版本 {user.terms_of_use_version || '-'}）
              </Text>
            ) : (
              <Text type="warning">未同意</Text>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="同意时间">
            {user?.terms_of_use_accepted_at
              ? new Date(user.terms_of_use_accepted_at).toLocaleString('zh-CN')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="数据存储偏好">
            {user?.storage_consent_level === 'necessary' && '必要'}
            {user?.storage_consent_level === 'functional' && '功能偏好'}
            {user?.storage_consent_level === 'analytics' && '分析统计'}
            {!user?.storage_consent_level && '必要'}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {user?.privacy_policy_accepted_at && user?.terms_of_use_accepted_at ? (
              <Text type="success">合规</Text>
            ) : (
              <Text type="danger">待补录</Text>
            )}
          </Descriptions.Item>
        </Descriptions>

        <Space>
          <Button onClick={() => navigate('/privacy-policy')}>查看隐私政策</Button>
          <Button onClick={() => navigate('/terms-of-use')}>查看用户协议</Button>
        </Space>
      </Card>
    </div>
  )
}

export default ProfilePage
