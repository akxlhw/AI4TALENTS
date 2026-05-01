import { useState } from 'react'
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
import {
  GithubOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from './utils'

interface GitHubConfig {
  tokens_masked: string
  base_url: string
  rate_limit: number
}

const GitHubConfigTab: React.FC = () => {
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
      message.error('加载 GitHub 配置失败')
    } finally {
      setGitHubLoading(false)
    }
  }

  const handleSaveGitHubConfig = async () => {
    try {
      const values = await githubForm.validateFields()
      setGitHubLoading(true)
      await api.systemConfig.updateGitHubConfig(values)
      message.success('GitHub 配置已保存')
      loadGitHubConfig()
    } catch (error) {
      message.error(getErrorMessage(error, '保存失败'))
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
        message.success('GitHub API 连接测试成功')
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, '连接测试失败')
      setTestGitHubResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingGitHub(false)
    }
  }

  // Load on mount
  useState(() => {
    loadGitHubConfig()
  })

  return (
    <Card>
      <Spin spinning={githubLoading}>
        <Alert
          message="GitHub API 配置"
          description="配置 GitHub Personal Access Token 用于开源人才数据采集。支持多 Token 轮询（逗号分隔），单个 Token 速率限制为 5000 req/hour。"
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
            label="GitHub Token"
            tooltip="支持多个 Token，用逗号分隔。每个 Token 需要有 repo 和 read:user 权限。"
            rules={[{ required: false }]}
          >
            <Input.TextArea
              placeholder={githubConfig?.tokens_masked || '请输入 GitHub Personal Access Token'}
              rows={2}
            />
          </Form.Item>
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="base_url"
                label="API 基础地址"
                rules={[{ required: true, message: '请输入 API 基础地址' }]}
              >
                <Input placeholder="https://api.github.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rate_limit"
                label="单 Token 速率限制（req/hour）"
                tooltip="用于监控预警，达到 80% 时触发警告"
                rules={[{ required: true }]}
              >
                <InputNumber min={60} max={50000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={githubLoading}>保存配置</Button>
              <Button onClick={handleTestGitHub} loading={testingGitHub} icon={<GithubOutlined />}>测试连接</Button>
            </Space>
          </Form.Item>
        </Form>
        {testGitHubResult && (
          <Alert
            message={testGitHubResult.success ? '测试通过' : '测试失败'}
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
