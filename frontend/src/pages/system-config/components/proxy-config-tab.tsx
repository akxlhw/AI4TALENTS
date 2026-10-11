import { useState, useEffect } from 'react'
import { semanticColors } from '../../../theme'
import {
  Card,
  Space,
  Button,
  Spin,
  Alert,
  Form,
  Input,
  Row,
  Col,
  Switch,
  Tag,
  message,
} from 'antd'
import { useTranslation } from 'react-i18next'
import {
  GlobalOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import '../../../i18n/namespaces/system-config'
import { getErrorMessage } from './utils'

interface ProxyConfig {
  enabled: boolean
  url: string
  username: string
  password_masked: string
  no_proxy: string
  ssl_verify: boolean
}

const ProxyConfigTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const [proxyConfig, setProxyConfig] = useState<ProxyConfig | null>(null)
  const [proxyForm] = Form.useForm()
  const [proxyLoading, setProxyLoading] = useState(false)
  const [testingProxy, setTestingProxy] = useState(false)
  const [testProxyResult, setTestProxyResult] = useState<{
    success: boolean
    message: string
    results?: Array<{
      url: string
      success: boolean
      message: string
      used_proxy: boolean
    }>
  } | null>(null)

  const loadProxyConfig = async () => {
    setProxyLoading(true)
    try {
      const response = await api.systemConfig.getProxyConfig()
      setProxyConfig(response.data)
      proxyForm.setFieldsValue({
        ...response.data,
        password: response.data.password_masked,
      })
    } catch {
      message.error(t('proxy.loadFailed'))
    } finally {
      setProxyLoading(false)
    }
  }

  useEffect(() => {
    loadProxyConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSaveProxyConfig = async () => {
    try {
      const values = await proxyForm.validateFields()
      setProxyLoading(true)
      await api.systemConfig.updateProxyConfig(values)
      message.success(t('proxy.saveSuccess'))
      loadProxyConfig()
    } catch (error) {
      message.error(getErrorMessage(error, t('common.saveFailed')))
    } finally {
      setProxyLoading(false)
    }
  }

  const handleTestProxy = async () => {
    setTestingProxy(true)
    setTestProxyResult(null)
    try {
      const response = await api.systemConfig.testProxy()
      setTestProxyResult({
        success: response.data.success,
        message: response.data.message,
        results: response.data.results,
      })
      if (response.data.success) {
        message.success(t('proxy.testSuccess'))
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, t('common.testFailed'))
      setTestProxyResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingProxy(false)
    }
  }

  return (
    <Card>
      <Spin spinning={proxyLoading}>
        <Alert
          message={t('proxy.infoTitle')}
          description={t('proxy.infoDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form
          form={proxyForm}
          layout="vertical"
          onFinish={handleSaveProxyConfig}
          initialValues={{ enabled: false }}
        >
          <Row gutter={24}>
            <Col span={8}>
              <Form.Item name="enabled" label={t('proxy.enableProxy')} valuePropName="checked">
                <Switch checkedChildren={t('common.on')} unCheckedChildren={t('common.off')} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="url"
            label={t('proxy.url')}
            rules={[{ required: false, message: t('proxy.urlRequired') }]}
          >
            <Input placeholder="http://proxy.company.com:8080" />
          </Form.Item>
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item name="username" label={t('proxy.username')}>
                <Input placeholder={t('proxy.usernamePlaceholder')} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label={t('proxy.password')}>
                <Input.Password placeholder={proxyConfig?.password_masked || t('proxy.passwordPlaceholder')} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="no_proxy"
            label={t('proxy.noProxy')}
            tooltip={t('proxy.noProxyTooltip')}
          >
            <Input.TextArea
              placeholder="localhost,127.0.0.1,*.internal.com,10.*,192.168.*"
              rows={2}
            />
          </Form.Item>
          <Form.Item
            name="ssl_verify"
            label={t('proxy.sslVerify')}
            valuePropName="checked"
            tooltip={t('proxy.sslVerifyTooltip')}
          >
            <Switch checkedChildren={t('common.on')} unCheckedChildren={t('common.off')} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={proxyLoading}>{t('common.saveConfig')}</Button>
              <Button onClick={handleTestProxy} loading={testingProxy} icon={<GlobalOutlined />}>{t('common.testConnection')}</Button>
            </Space>
          </Form.Item>
        </Form>
        {testProxyResult && (
          <div style={{ marginTop: 16 }}>
            <Alert
              message={testProxyResult.success ? t('common.testPassed') : t('common.testFailedShort')}
              description={testProxyResult.message}
              type={testProxyResult.success ? 'success' : 'error'}
              showIcon
              icon={testProxyResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              style={{ marginBottom: 12 }}
            />
            {testProxyResult.results && testProxyResult.results.length > 0 && (
              <Card size="small" title={t('common.testDetails')} style={{ background: semanticColors.bgGrayLight }}>
                {testProxyResult.results.map((result, index) => (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      padding: '8px 0',
                      borderBottom: index < testProxyResult.results!.length - 1 ? `1px solid ${semanticColors.borderGrayLight}` : 'none'
                    }}
                  >
                    {result.success ? (
                      <CheckCircleOutlined style={{ color: semanticColors.green, marginRight: 8, marginTop: 4 }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: semanticColors.red, marginRight: 8, marginTop: 4 }} />
                    )}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500 }}>
                        {result.used_proxy ? t('proxy.viaExternalProxy') : t('proxy.directInternal')}
                        <Tag
                          color={result.used_proxy ? 'blue' : 'green'}
                          style={{ marginLeft: 8 }}
                        >
                          {result.used_proxy ? t('proxy.tagViaProxy') : t('proxy.tagDirect')}
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {result.url}
                      </div>
                      <div style={{ fontSize: 12, color: result.success ? semanticColors.green : semanticColors.red, marginTop: 2 }}>
                        {result.message}
                      </div>
                    </div>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}
      </Spin>
    </Card>
  )
}

export default ProxyConfigTab
