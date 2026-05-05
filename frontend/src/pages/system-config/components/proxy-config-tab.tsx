import { useState } from 'react'
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
import {
  GlobalOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
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
      proxyForm.setFieldsValue(response.data)
    } catch {
      message.error('加载代理配置失败')
    } finally {
      setProxyLoading(false)
    }
  }

  const handleSaveProxyConfig = async () => {
    try {
      const values = await proxyForm.validateFields()
      setProxyLoading(true)
      await api.systemConfig.updateProxyConfig(values)
      message.success('代理配置已保存')
      loadProxyConfig()
    } catch (error) {
      message.error(getErrorMessage(error, '保存失败'))
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
        message.success('代理配置测试成功')
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, '连接测试失败')
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
          message="网络代理配置"
          description="配置 HTTP 代理以访问外网 API（OpenAlex、LLM 等）。适用于企业内网环境。密码将被加密存储。"
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
              <Form.Item name="enabled" label="启用代理" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="url"
            label="代理地址"
            rules={[{ required: false, message: '请输入代理地址' }]}
          >
            <Input placeholder="http://proxy.company.com:8080" />
          </Form.Item>
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item name="username" label="用户名（可选）">
                <Input placeholder="代理认证用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label="密码（可选）">
                <Input.Password placeholder={proxyConfig?.password_masked || '代理认证密码'} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="no_proxy"
            label="不走代理的地址"
            tooltip="内网服务地址，多个用逗号分隔。匹配这些地址的请求将直连而不走代理。"
          >
            <Input.TextArea
              placeholder="localhost,127.0.0.1,*.internal.com,10.*,192.168.*"
              rows={2}
            />
          </Form.Item>
          <Form.Item
            name="ssl_verify"
            label="验证 SSL 证书"
            valuePropName="checked"
            tooltip="企业代理使用自签名证书时需关闭验证。关闭后存在中间人攻击风险，请谨慎使用。"
          >
            <Switch checkedChildren="开启" unCheckedChildren="关闭" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={proxyLoading}>保存配置</Button>
              <Button onClick={handleTestProxy} loading={testingProxy} icon={<GlobalOutlined />}>测试连接</Button>
            </Space>
          </Form.Item>
        </Form>
        {testProxyResult && (
          <div style={{ marginTop: 16 }}>
            <Alert
              message={testProxyResult.success ? '测试通过' : '测试失败'}
              description={testProxyResult.message}
              type={testProxyResult.success ? 'success' : 'error'}
              showIcon
              icon={testProxyResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              style={{ marginBottom: 12 }}
            />
            {testProxyResult.results && testProxyResult.results.length > 0 && (
              <Card size="small" title="测试详情" style={{ background: '#fafafa' }}>
                {testProxyResult.results.map((result, index) => (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      padding: '8px 0',
                      borderBottom: index < testProxyResult.results!.length - 1 ? '1px solid #f0f0f0' : 'none'
                    }}
                  >
                    {result.success ? (
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8, marginTop: 4 }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8, marginTop: 4 }} />
                    )}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500 }}>
                        {result.used_proxy ? '外网代理' : '内网直连'}
                        <Tag
                          color={result.used_proxy ? 'blue' : 'green'}
                          style={{ marginLeft: 8 }}
                        >
                          {result.used_proxy ? '走代理' : '直连'}
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {result.url}
                      </div>
                      <div style={{ fontSize: 12, color: result.success ? '#52c41a' : '#ff4d4f', marginTop: 2 }}>
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
