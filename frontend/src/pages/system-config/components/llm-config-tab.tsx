import { useState } from 'react'
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
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
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
      llmForm.setFieldsValue(response.data)
    } catch {
      message.error('加载 LLM 配置失败')
    } finally {
      setLLMLoading(false)
    }
  }

  const handleSaveLLMConfig = async () => {
    try {
      const values = await llmForm.validateFields()
      setLLMLoading(true)
      const response = await api.systemConfig.updateLLMConfig(values)
      message.success('LLM 配置已保存')
      if (response.data?.warning) {
        message.warning(response.data.warning, 6)
      }
      loadLLMConfig()
    } catch (error) {
      message.error(getErrorMessage(error, '保存失败'))
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
        message.success('LLM 连接测试成功')
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, '连接测试失败')
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
        message.success('嵌入模型连接测试成功')
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, '嵌入模型连接测试失败')
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
          message="LLM 配置说明"
          description="配置 LLM API 以启用岗位匹配、智能推荐等功能。API Key 将被加密存储，前端仅显示脱敏值。"
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
              <Title level={5} style={{ marginBottom: 8 }}>对话模型</Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                用于 JD 解析、推荐理由生成
              </Text>
              <Form.Item name="enabled" label="启用" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
              <Form.Item name="api_format" label="API 格式" tooltip="openai: OpenAI 兼容格式；minimax: MiniMax 专用格式">
                <Select options={[
                  { value: 'openai', label: 'OpenAI 兼容格式' },
                  { value: 'minimax', label: 'MiniMax 格式' },
                ]} />
              </Form.Item>
              <Form.Item name="api_key" label="API Key">
                <Input.Password placeholder={llmConfig?.api_key_masked || '请输入 API Key'} />
              </Form.Item>
              <Form.Item name="api_base" label="API 地址">
                <Input placeholder="如 https://api.deepseek.com/v1" />
              </Form.Item>
              <Form.Item name="model" label="模型名称">
                <Input placeholder="如 deepseek-chat, gpt-4o" />
              </Form.Item>
              <Form.Item>
                <Button onClick={handleTestLLM} loading={testingLLM} icon={<ApiOutlined />}>测试连接</Button>
              </Form.Item>
            </Col>

            {/* 右侧：嵌入模型配置 */}
            <Col span={12}>
              <Title level={5} style={{ marginBottom: 8 }}>嵌入模型</Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                用于语义搜索、相似人才推荐
              </Text>
              <Form.Item name="embedding_enabled" label="启用" valuePropName="checked">
                <Switch checkedChildren="开启" unCheckedChildren="关闭" />
              </Form.Item>
              <Form.Item name="embedding_api_format" label="API 格式" tooltip="嵌入模型的 API 格式，留空则使用对话模型的 API 格式">
                <Select allowClear placeholder="留空使用对话模型格式" options={[
                  { value: 'openai', label: 'OpenAI 兼容格式' },
                  { value: 'minimax', label: 'MiniMax 格式' },
                ]} />
              </Form.Item>
              <Form.Item name="embedding_api_key" label="API Key">
                <Input.Password placeholder={llmConfig?.embedding_api_key_masked || '请输入 API Key'} />
              </Form.Item>
              <Form.Item name="embedding_api_base" label="API 地址">
                <Input placeholder="如 https://api.openai.com/v1" />
              </Form.Item>
              <Form.Item name="embedding_model" label="模型名称">
                <Input placeholder="如 text-embedding-3-small, bge-m3" />
              </Form.Item>
              <Form.Item name="embedding_dimension" label="向量维度" tooltip="嵌入模型输出的向量维度。常见值：OpenAI 1536，千问/BGE 1024。注意：修改维度会清空现有向量数据">
                <InputNumber min={128} max={4096} style={{ width: '100%' }} placeholder="1024" />
              </Form.Item>
              <Form.Item>
                <Button onClick={handleTestEmbedding} loading={testingEmbedding} icon={<ApiOutlined />}>测试连接</Button>
              </Form.Item>
            </Col>
          </Row>

          {/* 公共配置 */}
          <Row gutter={24} style={{ marginTop: 16 }}>
            <Col span={12}>
              <Form.Item name="timeout" label="超时时间（秒）">
                <InputNumber min={10} max={300} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={llmLoading}>保存配置</Button>
          </Form.Item>
        </Form>
        {testResult && (
          <Alert
            message={testResult.success ? '对话模型连接成功' : '对话模型连接失败'}
            description={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            style={{ marginTop: 16 }}
          />
        )}
        {embeddingTestResult && (
          <Alert
            message={embeddingTestResult.success ? '嵌入模型连接成功' : '嵌入模型连接失败'}
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
