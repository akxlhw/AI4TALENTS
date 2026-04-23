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
        background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative elements */}
      <div
        style={{
          position: 'absolute',
          top: '-50%',
          left: '-50%',
          width: '200%',
          height: '200%',
          background: 'radial-gradient(circle at 30% 70%, rgba(102, 126, 234, 0.15) 0%, transparent 50%), radial-gradient(circle at 70% 30%, rgba(118, 75, 162, 0.1) 0%, transparent 50%)',
          pointerEvents: 'none',
        }}
      />

      <Card
        style={{
          width: 420,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1)',
          borderRadius: 16,
          background: 'rgba(255, 255, 255, 0.98)',
          backdropFilter: 'blur(20px)',
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
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
                prefix={<UserOutlined style={{ color: '#999' }} />}
                placeholder="用户名或邮箱"
                style={{ borderRadius: 8 }}
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#999' }} />}
                placeholder="密码"
                style={{ borderRadius: 8 }}
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
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
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
