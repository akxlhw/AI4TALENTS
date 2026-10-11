import { useCallback, useEffect, useState } from 'react'
import { semanticColors } from '../../theme'
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
import { api } from '../../services/api'
import { formatUTCToLocal } from '../../utils/datetime'
import { formatNumber } from '../../utils/format'
import { useTranslation } from 'react-i18next'
import '../../i18n/namespaces/admin'

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
  const { t } = useTranslation(['admin', 'common'])
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

  const loadVersions = useCallback(async () => {
    try {
      const response = await api.dataVersion.listVersions({ page: versionPage, page_size: 10 })
      setVersions(response.data.items)
      setVersionTotal(response.data.total)
    } catch {
      message.error(t('dataVersion.messages.loadVersionsFailed'))
    }
  }, [versionPage, t])

  const loadActiveVersion = useCallback(async () => {
    try {
      const response = await api.dataVersion.getActiveVersion()
      setActiveVersion(response.data)
    } catch {
      // No active version
    }
  }, [])

  const loadQualityMetrics = useCallback(async () => {
    try {
      const response = await api.dataVersion.getQualityMetrics()
      setQualityMetrics(response.data)
    } catch {
      // No metrics
    }
  }, [])

  const loadCorrections = useCallback(async () => {
    try {
      const response = await api.dataVersion.listCorrections({
        page: correctionPage,
        page_size: 10,
      })
      setCorrections(response.data.items)
      setCorrectionTotal(response.data.total)
    } catch {
      message.error(t('dataVersion.messages.loadCorrectionsFailed'))
    }
  }, [correctionPage, t])

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true)
      try {
        await Promise.all([
          loadVersions(),
          loadActiveVersion(),
          loadQualityMetrics(),
          loadCorrections(),
        ])
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [loadVersions, loadActiveVersion, loadQualityMetrics, loadCorrections])

  useEffect(() => {
    loadVersions()
  }, [loadVersions])

  useEffect(() => {
    loadCorrections()
  }, [loadCorrections])

  const handleCreateVersion = () => {
    versionForm.resetFields()
    setVersionModalVisible(true)
  }

  const handleSaveVersion = async (values: Record<string, unknown>) => {
    try {
      await api.dataVersion.createVersion({
        version_code: values.version_code as string,
        version_name: values.version_name as string,
        version_type: (values.version_type as string) || 'snapshot',
        description: values.description as string | undefined,
      })
      message.success(t('dataVersion.messages.createSuccess'))
      setVersionModalVisible(false)
      loadVersions()
    } catch (error: unknown) {
      const detail =
        error instanceof Error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      message.error(detail || t('dataVersion.messages.createFailed'))
    }
  }

  const handlePublishVersion = async (versionId: number) => {
    try {
      await api.dataVersion.publishVersion(versionId)
      message.success(t('dataVersion.messages.publishSuccess'))
      loadVersions()
      loadActiveVersion()
    } catch (error: unknown) {
      const detail =
        error instanceof Error && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      message.error(detail || t('dataVersion.messages.publishFailed'))
    }
  }

  // Version columns
  const versionColumns = [
    {
      title: t('dataVersion.versionColumns.code'),
      dataIndex: 'version_code',
      key: 'version_code',
      width: 150,
    },
    {
      title: t('dataVersion.versionColumns.name'),
      dataIndex: 'version_name',
      key: 'version_name',
    },
    {
      title: t('dataVersion.versionColumns.type'),
      dataIndex: 'version_type',
      key: 'version_type',
      render: (type: string) => (
        <Tag color={type === 'release' ? 'green' : 'blue'}>
          {type === 'release'
            ? t('dataVersion.versionType.release')
            : t('dataVersion.versionType.snapshot')}
        </Tag>
      ),
    },
    {
      title: t('dataVersion.versionColumns.stats'),
      key: 'stats',
      render: (_: unknown, record: DataVersion) => (
        <Space size={4}>
          <Tooltip title={t('dataVersion.stats.talentTooltip')}>
            <Tag>{t('dataVersion.stats.talents', { n: record.total_talents })}</Tag>
          </Tooltip>
          <Tooltip title={t('dataVersion.stats.schoolTooltip')}>
            <Tag>{t('dataVersion.stats.schools', { n: record.total_schools })}</Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: t('dataVersion.versionColumns.status'),
      key: 'status',
      render: (_: unknown, record: DataVersion) => (
        <Space>
          {record.is_active && <Badge status="success" text={t('dataVersion.badges.active')} />}
          {record.is_published && !record.is_active && (
            <Badge status="default" text={t('dataVersion.badges.published')} />
          )}
          {!record.is_published && (
            <Badge status="warning" text={t('dataVersion.badges.unpublished')} />
          )}
        </Space>
      ),
    },
    {
      title: t('dataVersion.versionColumns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: t('dataVersion.versionColumns.actions'),
      key: 'actions',
      width: 120,
      render: (_: unknown, record: DataVersion) => (
        <Space>
          {!record.is_active && !record.is_published && (
            <Button
              type="link"
              size="small"
              icon={<ThunderboltOutlined />}
              onClick={() => handlePublishVersion(record.version_id)}
            >
              {t('dataVersion.actions.publish')}
            </Button>
          )}
        </Space>
      ),
    },
  ]

  // Correction columns
  const correctionColumns = [
    {
      title: t('dataVersion.correctionColumns.targetType'),
      dataIndex: 'target_type',
      key: 'target_type',
      render: (type: string) => t(`dataVersion.targets.${type}`, { defaultValue: type }),
    },
    {
      title: t('dataVersion.correctionColumns.targetId'),
      dataIndex: 'target_id',
      key: 'target_id',
    },
    {
      title: t('dataVersion.correctionColumns.field'),
      dataIndex: 'field_name',
      key: 'field_name',
    },
    {
      title: t('dataVersion.correctionColumns.correctionType'),
      dataIndex: 'correction_type',
      key: 'correction_type',
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          manual: 'blue',
          system: 'green',
          import: 'orange',
        }
        return (
          <Tag color={colorMap[type] || 'default'}>
            {t(`dataVersion.correctionTypes.${type}`, { defaultValue: type })}
          </Tag>
        )
      },
    },
    {
      title: t('dataVersion.correctionColumns.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusBadgeMap: Record<
          string,
          { status: 'success' | 'processing' | 'error' | 'default' }
        > = {
          applied: { status: 'success' },
          pending: { status: 'processing' },
          reverted: { status: 'error' },
        }
        const item = statusBadgeMap[status] || { status: 'default' as const }
        return (
          <Badge
            status={item.status}
            text={t(`dataVersion.correctionStatus.${status}`, { defaultValue: status })}
          />
        )
      },
    },
    {
      title: t('dataVersion.correctionColumns.correctedAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatUTCToLocal(date),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={4}>{t('dataVersion.title')}</Title>

      {/* Active Version & Quality Overview */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                {t('dataVersion.currentVersion')}
              </Space>
            }
          >
            {activeVersion ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label={t('dataVersion.labels.version')}>
                  {activeVersion.version_name}
                </Descriptions.Item>
                <Descriptions.Item label={t('dataVersion.labels.code')}>
                  {activeVersion.version_code}
                </Descriptions.Item>
                <Descriptions.Item label={t('dataVersion.labels.talentCount')}>
                  {formatNumber(activeVersion.total_talents)}
                </Descriptions.Item>
                <Descriptions.Item label={t('dataVersion.labels.schoolCount')}>
                  {formatNumber(activeVersion.total_schools)}
                </Descriptions.Item>
                <Descriptions.Item label={t('dataVersion.labels.publishedAt')}>
                  {formatUTCToLocal(activeVersion.published_at)}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">{t('dataVersion.noActiveVersion')}</Text>
            )}
          </Card>
        </Col>
        <Col span={16}>
          <Card
            title={
              <Space>
                <CheckCircleOutlined />
                {t('dataVersion.qualityOverview')}
              </Space>
            }
          >
            {qualityMetrics ? (
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title={t('dataVersion.quality.talent')}
                    value={qualityMetrics.talent_total}
                    suffix={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('dataVersion.quality.completeness', {
                          value: qualityMetrics.talent_completeness_avg,
                        })}
                      </Text>
                    }
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={t('dataVersion.quality.school')}
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
                    title={t('dataVersion.quality.works')}
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
                    title={t('dataVersion.quality.pendingTags')}
                    value={qualityMetrics.tech_tag_pending}
                    valueStyle={{
                      color:
                        qualityMetrics.tech_tag_pending > 0
                          ? semanticColors.gold
                          : semanticColors.green,
                    }}
                  />
                </Col>
              </Row>
            ) : (
              <Text type="secondary">{t('dataVersion.noQualityData')}</Text>
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
                {t('dataVersion.tabs.versions')}
              </span>
            ),
            children: (
              <Card
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateVersion}>
                    {t('dataVersion.createVersion')}
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
                    showTotal: count => t('dataVersion.totalVersions', { n: count }),
                    onChange: p => setVersionPage(p),
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
                {t('dataVersion.tabs.corrections')}
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
                    showTotal: count => t('dataVersion.totalRecords', { n: count }),
                    onChange: p => setCorrectionPage(p),
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Create Version Modal */}
      <Modal
        title={t('dataVersion.modal.title')}
        open={versionModalVisible}
        onCancel={() => setVersionModalVisible(false)}
        onOk={() => versionForm.submit()}
      >
        <Form form={versionForm} layout="vertical" onFinish={handleSaveVersion}>
          <Form.Item
            name="version_code"
            label={t('dataVersion.form.code')}
            rules={[{ required: true }]}
          >
            <Input placeholder={t('dataVersion.form.codePlaceholder')} />
          </Form.Item>
          <Form.Item
            name="version_name"
            label={t('dataVersion.form.name')}
            rules={[{ required: true }]}
          >
            <Input placeholder={t('dataVersion.form.namePlaceholder')} />
          </Form.Item>
          <Form.Item
            name="version_type"
            label={t('dataVersion.form.type')}
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: 'snapshot', label: t('dataVersion.versionType.snapshot') },
                { value: 'release', label: t('dataVersion.versionType.release') },
              ]}
            />
          </Form.Item>
          <Form.Item name="description" label={t('dataVersion.form.description')}>
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DataVersionPage
