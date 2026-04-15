import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Space, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const { Title, Text } = Typography

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
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card
        style={{
          width: 400,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title
              level={2}
              style={{
                marginBottom: 8,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                fontWeight: 700,
                letterSpacing: '2px',
              }}
            >
              AI4TALENT
            </Title>
            <Title
              level={4}
              style={{
                margin: 0,
                color: '#1890ff',
                fontWeight: 500,
                letterSpacing: '4px',
              }}
            >
              智能人才库
            </Title>
            <Text type="secondary" style={{ fontSize: 13, marginTop: 8, display: 'block' }}>
              学术人才发现平台
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
                prefix={<UserOutlined />}
                placeholder="用户名或邮箱"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="密码"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  )
}

export default LoginPage
