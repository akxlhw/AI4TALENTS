import { useState, useEffect } from 'react'
import {
  Card,
  Space,
  Button,
  Spin,
  Alert,
  Form,
  Input,
  InputNumber,
  Row,
  Col,
  message,
} from 'antd'
import { useTranslation } from 'react-i18next'
import {
  GithubOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import '../../../i18n/namespaces/system-config'
import { getErrorMessage } from './utils'

interface GitHubConfig {
  tokens_masked: string
  base_url: string
  rate_limit: number
}

const GitHubConfigTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const [githubConfig, setGitHubConfig] = useState<GitHubConfig | null>(null)
  const [githubForm] = Form.useForm()
  const [githubLoading, setGitHubLoading] = useState(false)
  const [testingGitHub, setTestingGitHub] = useState(false)
  const [testGitHubResult, setTestGitHubResult] = useState<{ success: boolean; message: string } | null>(null)

  const loadGitHubConfig = async () => {
    setGitHubLoading(true)
    try {
      const response = await api.systemConfig.getGitHubConfig()
      setGitHubConfig(response.data)
      githubForm.setFieldsValue({
        tokens: '',
        base_url: response.data.base_url,
        rate_limit: response.data.rate_limit,
      })
    } catch {
      message.error(t('github.loadFailed'))
    } finally {
      setGitHubLoading(false)
    }
  }

  const handleSaveGitHubConfig = async () => {
    try {
      const values = await githubForm.validateFields()
      setGitHubLoading(true)
      await api.systemConfig.updateGitHubConfig(values)
      message.success(t('github.saveSuccess'))
      loadGitHubConfig()
    } catch (error) {
      message.error(getErrorMessage(error, t('common.saveFailed')))
    } finally {
      setGitHubLoading(false)
    }
  }

  const handleTestGitHub = async () => {
    setTestingGitHub(true)
    setTestGitHubResult(null)
    try {
      const response = await api.systemConfig.testGitHub()
      setTestGitHubResult({
        success: response.data.success,
        message: response.data.message,
      })
      if (response.data.success) {
        message.success(t('github.testSuccess'))
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, t('common.testFailed'))
      setTestGitHubResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingGitHub(false)
    }
  }

  useEffect(() => {
    loadGitHubConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <Card>
      <Spin spinning={githubLoading}>
        <Alert
          message={t('github.infoTitle')}
          description={t('github.infoDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form
          form={githubForm}
          layout="vertical"
          onFinish={handleSaveGitHubConfig}
        >
          <Form.Item
            name="tokens"
            label={t('github.token')}
            tooltip={t('github.tokenTooltip')}
            rules={[{ required: false }]}
          >
            <Input.TextArea
              placeholder={githubConfig?.tokens_masked || t('github.tokenPlaceholder')}
              rows={2}
            />
          </Form.Item>
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="base_url"
                label={t('github.baseUrl')}
                rules={[{ required: true, message: t('github.baseUrlRequired') }]}
              >
                <Input placeholder="https://api.github.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rate_limit"
                label={t('github.rateLimit')}
                tooltip={t('github.rateLimitTooltip')}
                rules={[{ required: true }]}
              >
                <InputNumber min={60} max={50000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={githubLoading}>{t('common.saveConfig')}</Button>
              <Button onClick={handleTestGitHub} loading={testingGitHub} icon={<GithubOutlined />}>{t('common.testConnection')}</Button>
            </Space>
          </Form.Item>
        </Form>
        {testGitHubResult && (
          <Alert
            message={testGitHubResult.success ? t('common.testPassed') : t('common.testFailedShort')}
            description={testGitHubResult.message}
            type={testGitHubResult.success ? 'success' : 'error'}
            showIcon
            icon={testGitHubResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            style={{ marginTop: 16 }}
          />
        )}
      </Spin>
    </Card>
  )
}

export default GitHubConfigTab
