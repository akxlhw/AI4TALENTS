import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Badge,
  Tabs,
  Descriptions,
  Statistic,
  Row,
  Col,
  Tooltip,
} from 'antd'
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  EditOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Text, Title } = Typography

// Types
interface DataVersion {
  version_id: number
  version_code: string
  version_name: string
  version_type: string
  base_version_id: number | null
  source_task_id: number | null
  total_talents: number
  total_schools: number
  total_works: number
  is_active: boolean
  is_published: boolean
  published_at: string | null
  published_by: number | null
  description: string | null
  created_at: string
}

interface QualityMetrics {
  talent_total: number
  talent_orcid_rate: number
  talent_affiliation_rate: number
  talent_works_rate: number
  talent_completeness_avg: number
  school_total: number
  school_ror_rate: number
  school_country_rate: number
  work_total: number
  work_doi_rate: number
  tech_tag_total: number
  tech_tag_confirmed_rate: number
  tech_tag_auto_rate: number
  tech_tag_pending: number
  issues_critical: number
  issues_warning: number
  issues_info: number
}

interface Correction {
  correction_id: number
  target_type: string
  target_id: number
  field_name: string
  original_value: string | null
  corrected_value: string | null
  correction_type: string
  reason: string | null
  source: string | null
  corrected_by: number
  status: string
  created_at: string
}

const DataVersionPage: React.FC = () => {
  // Version state
  const [versions, setVersions] = useState<DataVersion[]>([])
  const [versionTotal, setVersionTotal] = useState(0)
  const [versionPage, setVersionPage] = useState(1)
  const [activeVersion, setActiveVersion] = useState<DataVersion | null>(null)

  // Quality state
  const [qualityMetrics, setQualityMetrics] = useState<QualityMetrics | null>(null)

  // Correction state
  const [corrections, setCorrections] = useState<Correction[]>([])
  const [correctionTotal, setCorrectionTotal] = useState(0)
  const [correctionPage, setCorrectionPage] = useState(1)

  // Modal state
  const [versionModalVisible, setVersionModalVisible] = useState(false)
  const [versionForm] = Form.useForm()

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  useEffect(() => {
    loadVersions()
  }, [versionPage])

  useEffect(() => {
    loadCorrections()
  }, [correctionPage])

  const loadAll = async () => {
    setLoading(true)
    try {
      await Promise.all([loadVersions(), loadActiveVersion(), loadQualityMetrics(), loadCorrections()])
    } finally {
      setLoading(false)
    }
  }

  const loadVersions = async () => {
    try {
      const response = await api.dataVersion.listVersions({ page: versionPage, page_size: 10 })
      setVersions(response.data.items)
      setVersionTotal(response.data.total)
    } catch {
      message.error('加载版本列表失败')
    }
  }

  const loadActiveVersion = async () => {
    try {
      const response = await api.dataVersion.getActiveVersion()
      setActiveVersion(response.data)
    } catch {
      // No active version
    }
  }

  const loadQualityMetrics = async () => {
    try {
      const response = await api.dataVersion.getQualityMetrics()
      setQualityMetrics(response.data)
    } catch {
      // No metrics
    }
  }

  const loadCorrections = async () => {
    try {
      const response = await api.dataVersion.listCorrections({ page: correctionPage, page_size: 10 })
      setCorrections(response.data.items)
      setCorrectionTotal(response.data.total)
    } catch {
      message.error('加载纠偏记录失败')
    }
  }

  const handleCreateVersion = () => {
    versionForm.resetFields()
    setVersionModalVisible(true)
  }

  const handleSaveVersion = async (values: any) => {
    try {
      await api.dataVersion.createVersion({
        version_code: values.version_code,
        version_name: values.version_name,
        version_type: values.version_type || 'snapshot',
        description: values.description,
      })
      message.success('版本创建成功')
      setVersionModalVisible(false)
      loadVersions()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建失败')
    }
  }

  const handlePublishVersion = async (versionId: number) => {
    try {
      await api.dataVersion.publishVersion(versionId)
      message.success('版本发布成功')
      loadVersions()
      loadActiveVersion()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发布失败')
    }
  }

  // Version columns
  const versionColumns = [
    {
      title: '版本编码',
      dataIndex: 'version_code',
      key: 'version_code',
      width: 150,
    },
    {
      title: '版本名称',
      dataIndex: 'version_name',
      key: 'version_name',
    },
    {
      title: '类型',
      dataIndex: 'version_type',
      key: 'version_type',
      render: (type: string) => (
        <Tag color={type === 'release' ? 'green' : 'blue'}>
          {type === 'release' ? '发布版' : '快照'}
        </Tag>
      ),
    },
    {
      title: '数据统计',
      key: 'stats',
      render: (_: any, record: DataVersion) => (
        <Space size={4}>
          <Tooltip title="人才">
            <Tag>{record.total_talents} 人才</Tag>
          </Tooltip>
          <Tooltip title="学校">
            <Tag>{record.total_schools} 学校</Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_: any, record: DataVersion) => (
        <Space>
          {record.is_active && (
            <Badge status="success" text="当前生效" />
          )}
          {record.is_published && !record.is_active && (
            <Badge status="default" text="已发布" />
          )}
          {!record.is_published && (
            <Badge status="warning" text="未发布" />
          )}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: DataVersion) => (
        <Space>
          {!record.is_active && !record.is_published && (
            <Button
              type="link"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handlePublishVersion(record.version_id)}
            >
              发布
            </Button>
          )}
        </Space>
      ),
    },
  ]

  // Correction columns
  const correctionColumns = [
    {
      title: '目标类型',
      dataIndex: 'target_type',
      key: 'target_type',
      render: (type: string) => {
        const map: Record<string, string> = {
          talent: '人才',
          school: '学校',
          tech_tag: '技术标签',
        }
        return map[type] || type
      },
    },
    {
      title: '目标ID',
      dataIndex: 'target_id',
      key: 'target_id',
    },
    {
      title: '字段',
      dataIndex: 'field_name',
      key: 'field_name',
    },
    {
      title: '修正类型',
      dataIndex: 'correction_type',
      key: 'correction_type',
      render: (type: string) => {
        const map: Record<string, { label: string; color: string }> = {
          manual: { label: '手动', color: 'blue' },
          system: { label: '系统', color: 'green' },
          import: { label: '导入', color: 'orange' },
        }
        const item = map[type] || { label: type, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const map: Record<string, { label: string; status: 'success' | 'processing' | 'error' | 'default' }> = {
          applied: { label: '已应用', status: 'success' },
          pending: { label: '待处理', status: 'processing' },
          reverted: { label: '已撤销', status: 'error' },
        }
        const item = map[status] || { label: status, status: 'default' as const }
        return <Badge status={item.status} text={item.label} />
      },
    },
    {
      title: '修正时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>数据版本管理</Title>

      {/* Active Version & Quality Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                当前版本
              </Space>
            }
          >
            {activeVersion ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="版本">{activeVersion.version_name}</Descriptions.Item>
                <Descriptions.Item label="编码">{activeVersion.version_code}</Descriptions.Item>
                <Descriptions.Item label="人才数">{activeVersion.total_talents.toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="学校数">{activeVersion.total_schools.toLocaleString()}</Descriptions.Item>
                <Descriptions.Item label="发布时间">
                  {activeVersion.published_at ? new Date(activeVersion.published_at).toLocaleString() : '-'}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">暂无生效版本</Text>
            )}
          </Card>
        </Col>
        <Col span={16}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined />
                数据质量概览
              </Space>
            }
          >
            {qualityMetrics ? (
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="人才数据"
                    value={qualityMetrics.talent_total}
                    suffix={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        完整度 {qualityMetrics.talent_completeness_avg}%
                      </Text>
                    }
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="学校数据"
                    value={qualityMetrics.school_total}
                    suffix={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        ROR {qualityMetrics.school_ror_rate}%
                      </Text>
                    }
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="论文数据"
                    value={qualityMetrics.work_total}
                    suffix={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        DOI {qualityMetrics.work_doi_rate}%
                      </Text>
                    }
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="待确认标签"
                    value={qualityMetrics.tech_tag_pending}
                    valueStyle={{ color: qualityMetrics.tech_tag_pending > 0 ? '#faad14' : '#52c41a' }}
                  />
                </Col>
              </Row>
            ) : (
              <Text type="secondary">暂无质量数据</Text>
            )}
          </Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'versions',
            label: (
              <span>
                <DatabaseOutlined />
                数据版本
              </span>
            ),
            children: (
              <Card
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateVersion}>
                创建版本
              </Button>
                }
              >
                <Table
                  dataSource={versions}
                  columns={versionColumns}
                  rowKey="version_id"
                  loading={loading}
                  pagination={{
                    current: versionPage,
                    pageSize: 10,
                    total: versionTotal,
                    showTotal: (t) => `共 ${t} 个版本`,
                    onChange: (p) => setVersionPage(p),
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'corrections',
            label: (
              <span>
                <EditOutlined />
                纠偏记录
              </span>
            ),
            children: (
              <Card>
                <Table
                  dataSource={corrections}
                  columns={correctionColumns}
                  rowKey="correction_id"
                  loading={loading}
                  pagination={{
                    current: correctionPage,
                    pageSize: 10,
                    total: correctionTotal,
                    showTotal: (t) => `共 ${t} 条记录`,
                    onChange: (p) => setCorrectionPage(p),
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Create Version Modal */}
      <Modal
        title="创建数据版本"
        open={versionModalVisible}
        onCancel={() => setVersionModalVisible(false)}
        onOk={() => versionForm.submit()}
      >
        <Form form={versionForm} layout="vertical" onFinish={handleSaveVersion}>
          <Form.Item
            name="version_code"
            label="版本编码"
            rules={[{ required: true }]}
          >
            <Input placeholder="如: V20240101" />
          </Form.Item>
          <Form.Item
            name="version_name"
            label="版本名称"
            rules={[{ required: true }]}
          >
            <Input placeholder="如: 2024年1月数据快照" />
          </Form.Item>
          <Form.Item
            name="version_type"
            label="版本类型"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: 'snapshot', label: '快照' },
                { value: 'release', label: '发布版' },
              ]}
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataVersionPage
