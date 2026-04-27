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
        background: 'linear-gradient(160deg, #F7FAFC 0%, #EEF4FA 40%, #DBEAFA 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative background pattern */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(30,58,95,0.06) 1px, transparent 0)`,
          backgroundSize: '32px 32px',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '-10%',
          right: '-5%',
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(74,144,164,0.12) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: '-15%',
          left: '-10%',
          width: 600,
          height: 600,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(30,58,95,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      <Card
        style={{
          width: 420,
          boxShadow: 'var(--shadow-xl)',
          borderRadius: 16,
          border: '1px solid var(--border-secondary)',
          background: '#FFFFFF',
        }}
        bodyStyle={{ padding: '40px 32px' }}
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
