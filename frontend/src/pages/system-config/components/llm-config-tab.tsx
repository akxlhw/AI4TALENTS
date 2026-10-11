import { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Button,
  Spin,
  Alert,
  Form,
  Input,
  InputNumber,
  Row,
  Col,
  Switch,
  Select,
  message,
} from 'antd'
import { useTranslation } from 'react-i18next'
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import '../../../i18n/namespaces/system-config'
import { getErrorMessage } from './utils'

const { Text, Title } = Typography

interface LLMConfig {
  enabled: boolean
  embedding_enabled: boolean
  api_format: string
  api_key_masked: string
  api_base: string
  model: string
  embedding_model: string
  embedding_api_base: string
  embedding_api_key_masked: string
  embedding_api_format: string
  embedding_dimension: number
  timeout: number
}

const LLMConfigTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const [llmConfig, setLLMConfig] = useState<LLMConfig | null>(null)
  const [llmForm] = Form.useForm()
  const [llmLoading, setLLMLoading] = useState(false)
  const [testingLLM, setTestingLLM] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [testingEmbedding, setTestingEmbedding] = useState(false)
  const [embeddingTestResult, setEmbeddingTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const loadLLMConfig = async () => {
    setLLMLoading(true)
    try {
      const response = await api.systemConfig.getLLMConfig()
      setLLMConfig(response.data)
      llmForm.setFieldsValue({
        ...response.data,
        api_key: response.data.api_key_masked,
        embedding_api_key: response.data.embedding_api_key_masked,
      })
    } catch {
      message.error(t('llm.loadFailed'))
    } finally {
      setLLMLoading(false)
    }
  }

  useEffect(() => {
    loadLLMConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSaveLLMConfig = async () => {
    try {
      const values = await llmForm.validateFields()
      setLLMLoading(true)
      const response = await api.systemConfig.updateLLMConfig(values)
      message.success(t('llm.saveSuccess'))
      if (response.data?.warning) {
        message.warning(response.data.warning, 6)
      }
      loadLLMConfig()
    } catch (error) {
      message.error(getErrorMessage(error, t('common.saveFailed')))
    } finally {
      setLLMLoading(false)
    }
  }

  const handleTestLLM = async () => {
    setTestingLLM(true)
    setTestResult(null)
    try {
      const response = await api.systemConfig.testLLM()
      setTestResult({
        success: response.data.success,
        message: response.data.message,
      })
      if (response.data.success) {
        message.success(t('llm.chatTestSuccess'))
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, t('common.testFailed'))
      setTestResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingLLM(false)
    }
  }

  const handleTestEmbedding = async () => {
    setTestingEmbedding(true)
    setEmbeddingTestResult(null)
    try {
      const response = await api.systemConfig.testEmbedding()
      setEmbeddingTestResult({
        success: response.data.success,
        message: response.data.message,
      })
      if (response.data.success) {
        message.success(t('llm.embeddingTestSuccess'))
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, t('llm.embeddingTestFailed'))
      setEmbeddingTestResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingEmbedding(false)
    }
  }

  return (
    <Card>
      <Spin spinning={llmLoading}>
        <Alert
          message={t('llm.infoTitle')}
          description={t('llm.infoDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form
          form={llmForm}
          layout="vertical"
          onFinish={handleSaveLLMConfig}
          initialValues={{ enabled: false, embedding_enabled: false, api_format: 'openai', embedding_dimension: 1024, timeout: 60 }}
        >
          <Row gutter={48}>
            {/* 左侧：对话模型配置 */}
            <Col span={12}>
              <Title level={5} style={{ marginBottom: 8 }}>{t('llm.chatTitle')}</Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                {t('llm.chatSubtitle')}
              </Text>
              <Form.Item name="enabled" label={t('common.enabled')} valuePropName="checked">
                <Switch checkedChildren={t('common.on')} unCheckedChildren={t('common.off')} />
              </Form.Item>
              <Form.Item name="api_format" label={t('llm.apiFormat')} tooltip={t('llm.apiFormatTooltip')}>
                <Select options={[
                  { value: 'openai', label: t('llm.openaiFormatLabel') },
                  { value: 'minimax', label: t('llm.minimaxFormatLabel') },
                ]} />
              </Form.Item>
              <Form.Item name="api_key" label={t('llm.apiKey')}>
                <Input.Password placeholder={llmConfig?.api_key_masked || t('llm.apiKeyPlaceholder')} />
              </Form.Item>
              <Form.Item name="api_base" label={t('llm.apiBase')}>
                <Input placeholder={t('llm.apiBasePlaceholder')} />
              </Form.Item>
              <Form.Item name="model" label={t('llm.model')}>
                <Input placeholder={t('llm.modelPlaceholder')} />
              </Form.Item>
              <Form.Item>
                <Button onClick={handleTestLLM} loading={testingLLM} icon={<ApiOutlined />}>{t('common.testConnection')}</Button>
              </Form.Item>
            </Col>

            {/* 右侧：嵌入模型配置 */}
            <Col span={12}>
              <Title level={5} style={{ marginBottom: 8 }}>{t('llm.embeddingTitle')}</Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                {t('llm.embeddingSubtitle')}
              </Text>
              <Form.Item name="embedding_enabled" label={t('common.enabled')} valuePropName="checked">
                <Switch checkedChildren={t('common.on')} unCheckedChildren={t('common.off')} />
              </Form.Item>
              <Form.Item name="embedding_api_format" label={t('llm.apiFormat')} tooltip={t('llm.embeddingApiFormatTooltip')}>
                <Select allowClear placeholder={t('llm.embeddingApiFormatPlaceholder')} options={[
                  { value: 'openai', label: t('llm.openaiFormatLabel') },
                  { value: 'minimax', label: t('llm.minimaxFormatLabel') },
                ]} />
              </Form.Item>
              <Form.Item name="embedding_api_key" label={t('llm.apiKey')}>
                <Input.Password placeholder={llmConfig?.embedding_api_key_masked || t('llm.apiKeyPlaceholder')} />
              </Form.Item>
              <Form.Item name="embedding_api_base" label={t('llm.apiBase')}>
                <Input placeholder={t('llm.embeddingApiBasePlaceholder')} />
              </Form.Item>
              <Form.Item name="embedding_model" label={t('llm.model')}>
                <Input placeholder={t('llm.embeddingModelPlaceholder')} />
              </Form.Item>
              <Form.Item name="embedding_dimension" label={t('llm.dimension')} tooltip={t('llm.dimensionTooltip')}>
                <InputNumber min={128} max={4096} style={{ width: '100%' }} placeholder="1024" />
              </Form.Item>
              <Form.Item>
                <Button onClick={handleTestEmbedding} loading={testingEmbedding} icon={<ApiOutlined />}>{t('common.testConnection')}</Button>
              </Form.Item>
            </Col>
          </Row>

          {/* 公共配置 */}
          <Row gutter={24} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Form.Item name="timeout" label={t('llm.timeout')}>
                <InputNumber min={10} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={llmLoading}>{t('common.saveConfig')}</Button>
          </Form.Item>
        </Form>
        {testResult && (
          <Alert
            message={testResult.success ? t('llm.chatConnected') : t('llm.chatConnectFailed')}
            description={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            style={{ marginTop: 16 }}
          />
        )}
        {embeddingTestResult && (
          <Alert
            message={embeddingTestResult.success ? t('llm.embeddingConnected') : t('llm.embeddingConnectFailed')}
            description={embeddingTestResult.message}
            type={embeddingTestResult.success ? 'success' : 'error'}
            showIcon
            icon={embeddingTestResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            style={{ marginTop: 16 }}
          />
        )}
      </Spin>
    </Card>
  )
}

export default LLMConfigTab
