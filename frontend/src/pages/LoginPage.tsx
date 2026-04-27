import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Space, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const { Text } = Typography

interface LoginForm {
  username: string
  password: string
}

interface LocationState {
  from?: { pathname: string }
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [loading, setLoading] = useState(false)

  const from = (location.state as LocationState)?.from?.pathname || '/'

  const handleSubmit = async (values: LoginForm) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      // Navigate to previous page or home
      navigate(from, { replace: true })
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      const detail = axiosError.response?.data?.detail || '登录失败，请检查用户名和密码'
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
          {/* Logo and Title */}
          <div style={{ textAlign: 'center', marginBottom: 8 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                justifyContent: 'center',
                gap: 8,
                marginBottom: 12,
              }}
            >
              <span
                style={{
                  fontSize: 28,
                  fontWeight: 800,
                  background: 'var(--domain-gradient)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  letterSpacing: '3px',
                  fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
                }}
              >
                AI4TALENT
              </span>
              <span
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  color: '#1a1a2e',
                  letterSpacing: '2px',
                }}
              >
                智能人才库
              </span>
            </div>
            <Text
              style={{
                fontSize: 14,
                color: '#666',
                letterSpacing: '1px',
                display: 'block',
              }}
            >
              顶尖优秀人才发现平台
            </Text>
          </div>

          <Form
            name="login"
            onFinish={handleSubmit}
            autoComplete="off"
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="用户名或邮箱"
                style={{ borderRadius: 10, height: 44 }}
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder="密码"
                style={{ borderRadius: 10, height: 44 }}
                autoComplete="new-password"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 16 }}>
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
                登 录
              </Button>
            </Form.Item>
          </Form>

          {/* Tagline */}
          <div style={{ textAlign: 'center' }}>
            <Text
              style={{
                fontSize: 13,
                color: '#666',
                letterSpacing: '2px',
              }}
            >
              数聚良才，智选慧才
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}

export default LoginPage
