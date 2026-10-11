import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Space, message, Checkbox } from 'antd'
import { UserOutlined, LockOutlined, IdcardOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { domainThemes } from '../../theme'

const { Text } = Typography

interface RegisterForm {
  username: string
  email: string
  employee_id: string
  password: string
  confirm_password: string
  display_name?: string
  privacy_policy_accepted: boolean
  terms_of_use_accepted: boolean
}

const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation('auth')
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
        privacy_policy_accepted: values.privacy_policy_accepted,
        terms_of_use_accepted: values.terms_of_use_accepted,
        storage_consent_level: 'necessary',
      })
      message.success(t('register.success'))
      setTimeout(() => navigate('/login'), 1500)
    } catch (err: unknown) {
      const detail =
        err instanceof Error && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      message.error(detail || t('register.failed'))
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
          boxShadow:
            '0 12px 48px rgba(30,58,95,0.08), 0 2px 8px rgba(30,58,95,0.04), inset 0 1px 0 rgba(255,255,255,0.8)',
        }}
        styles={{ body: { padding: '44px 36px' } }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: 8 }}>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: domainThemes.academic.primary,
                letterSpacing: '2px',
              }}
            >
              {t('register.title')}
            </span>
            <Text
              style={{
                fontSize: 13,
                color: '#666',
                display: 'block',
                marginTop: 6,
              }}
            >
              {t('register.subtitle')}
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
                { required: true, message: t('register.usernameRequired') },
                { min: 3, message: t('register.usernameMin') },
              ]}
            >
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.username')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: t('register.emailRequired') },
                { type: 'email', message: t('register.emailInvalid') },
              ]}
            >
              <Input
                prefix={<MailOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.email')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="employee_id"
              rules={[
                { required: true, message: t('register.employeeIdRequired') },
                {
                  pattern: /^[a-zA-Z]\d{8}$/,
                  message: t('register.employeeIdInvalid'),
                },
              ]}
            >
              <Input
                prefix={<IdcardOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.employeeId')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item name="display_name">
              <Input
                prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.displayNameOptional')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: t('register.passwordRequired') },
                { min: 8, message: t('register.passwordMin') },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.password')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="confirm_password"
              dependencies={['password']}
              rules={[
                { required: true, message: t('register.confirmPasswordRequired') },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error(t('register.passwordMismatch')))
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
                placeholder={t('register.confirmPassword')}
                style={{ borderRadius: 10, height: 44 }}
              />
            </Form.Item>

            <Form.Item
              name="privacy_policy_accepted"
              valuePropName="checked"
              rules={[
                {
                  validator: (_, value) =>
                    value
                      ? Promise.resolve()
                      : Promise.reject(new Error(t('register.privacyRequired'))),
                },
              ]}
              style={{ marginBottom: 8 }}
            >
              <Checkbox>
                <Text style={{ fontSize: 13, color: '#555' }}>
                  {t('register.agreePrefix')}{' '}
                  <a
                    onClick={e => {
                      e.preventDefault()
                      navigate('/privacy-policy')
                    }}
                    style={{ color: domainThemes.academic.primary }}
                  >
                    {t('register.privacyLink')}
                  </a>
                </Text>
              </Checkbox>
            </Form.Item>

            <Form.Item
              name="terms_of_use_accepted"
              valuePropName="checked"
              rules={[
                {
                  validator: (_, value) =>
                    value
                      ? Promise.resolve()
                      : Promise.reject(new Error(t('register.termsRequired'))),
                },
              ]}
              style={{ marginBottom: 12 }}
            >
              <Checkbox>
                <Text style={{ fontSize: 13, color: '#555' }}>
                  {t('register.agreePrefix')}{' '}
                  <a
                    onClick={e => {
                      e.preventDefault()
                      navigate('/terms-of-use')
                    }}
                    style={{ color: domainThemes.academic.primary }}
                  >
                    {t('register.termsLink')}
                  </a>
                  {t('register.termsSuffix')}
                </Text>
              </Checkbox>
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
                {t('register.submit')}
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center' }}>
            <Text style={{ fontSize: 13, color: '#666' }}>
              {t('register.hasAccount')}{' '}
              <a
                onClick={() => navigate('/login')}
                style={{ color: 'var(--domain-gradient)', cursor: 'pointer' }}
              >
                {t('register.loginNow')}
              </a>
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}

export default RegisterPage
