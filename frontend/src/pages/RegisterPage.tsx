import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Space, message } from 'antd'
import { UserOutlined, LockOutlined, IdcardOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'

const { Text } = Typography

interface RegisterForm {
  username: string
  email: string
  employee_id: string
  password: string
  confirm_password: string
  display_name?: string
}

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const handleSubmit = async (values: RegisterForm) => {
    setLoading(true)
    try {
      await api.auth.register({
        username: values.username,
        email: values.email,
        password: values.password,
        employee_id: values.employee_id,
        display_name: values.display_name || undefined,
      })
      message.success('注册成功，请等待管理员审核')
      setTimeout(() => navigate('/login'), 1500)
    } catch (err: any) {
      const detail = err.response?.data?.detail || '注册失败，请稍后重试'
      message.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundImage: 'url(/login_background.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Card
        style={{
          width: 420,
          borderRadius: 20,
          border: '1px solid rgba(255,255,255,0.6)',
          background: 'rgba(255,255,255,0.88)',
          backdropFilter: 'blur(20px) saturate(130%)',
          WebkitBackdropFilter: 'blur(20px) saturate(130%)',
          boxShadow: '0 12px 48px rgba(30,58,95,0.08), 0 2px 8px rgba(30,58,95,0.04), inset 0 1px 0 rgba(255,255,255,0.8)',
        }}
        bodyStyle={{ padding: '44px 36px' }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: 8 }}>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: '#1a1a2e',
                letterSpacing: '2px',
              }}
            >
              用户注册
            </span>
            <Text
              style={{
                fontSize: 13,
                color: '#666',
                display: 'block',
                marginTop: 6,
              }}
            >
              注册后需管理员审核通过方可登录
            </Text>
          </div>

          <Form
            form={form}
            name="register"
            onFinish={handleSubmit}
            autoComplete="off"
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名' },
                { min: 3, message: '用户名至少3位' },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="用户名"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={<MailOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="邮箱"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="employee_id"
              rules={[
                { required: true, message: '请输入工号' },
                {
                  pattern: /^[a-zA-Z]\d{8}$/,
                  message: '工号格式为1个字母+8个数字，如 h00123456',
                },
              ]}
            >
              <Input
                prefix={<IdcardOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="工号（如 h00123456）"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item name="display_name">
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="显示名称（可选）"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少8位' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="密码"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="confirm_password"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="确认密码"
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 12 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                style={{
                  height: 48,
                  borderRadius: 8,
                  fontWeight: 600,
                  fontSize: 16,
                  background: 'var(--domain-gradient)',
                  border: 'none',
                  boxShadow: '0 4px 15px rgba(30,58,95,0.25)',
                }}
              >
                注 册
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center' }}>
            <Text style={{ fontSize: 13, color: '#666' }}>
              已有账号？{' '}
              <a onClick={() => navigate('/login')} style={{ color: 'var(--domain-gradient)', cursor: 'pointer' }}>
                立即登录
              </a>
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}

export default RegisterPage
