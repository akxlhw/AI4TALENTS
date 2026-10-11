import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { logger } from '../../utils/logger'
import { navigateBack } from '../../utils/navigation'
import {
  Card,
  Descriptions,
  Typography,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Table,
  Spin,
  Button,
  Divider,
  Empty,
  Tooltip,
  Alert,
  Progress,
  message,
  Tabs,
} from 'antd'
import {
  UserOutlined,
  BankOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
  GlobalOutlined,
  TrophyOutlined,
  TeamOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { semanticColors } from '../../theme'
import FavoriteButton from '../../components/FavoriteButton'
import CollaborationGraph, { CollaborationNode, CollaborationLink } from '../../components/CollaborationGraph'
import GenealogyGraph, { GenealogyNode, GenealogyLink } from '../../components/GenealogyGraph'
import { getRoleTypeConfig, LEGACY_ROLE_TYPE_MAP } from '../../constants/roleType'
import '../../i18n/namespaces/academic'
import { formatNumber } from '../../utils/format'
import { getErrorMessage } from '../../utils'

const { Title, Text, Paragraph } = Typography

interface TalentDetail {
  talent_id: number
  name: string
  name_en: string | null
  orcid: string | null
  role_type: string
  role_confidence: number
  school_id: number | null
  school_name: string | null
  // Primary institutions (v1.5)
  education_school_id: number | null
  education_school_name: string | null
  company_school_id: number | null
  company_school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  latest_active_year: number | null
  topic_tags: string[]
  openalex_topics: string[]  // CR-02: OpenAlex研究主题
  research_interests: string | null
  summary: string | null
  department_name: string | null
  lab_name: string | null
  role_reason: string | null
  academic_age: number | null
  selected_works: SelectedWork[]
  // v1.1 新增字段
  recruitment_summary?: string | null
  data_completeness?: number
  pending_confirm_items?: string[]
  is_graduated?: boolean
}

interface SelectedWork {
  work_id: number
  title: string
  publication_year: number | null
  venue_name: string | null
  citation_count: number
  doi: string | null
}

const TalentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(['academic', 'common'])
  const [loading, setLoading] = useState(true)
  const [talent, setTalent] = useState<TalentDetail | null>(null)
  const [collabLoading, setCollabLoading] = useState(false)
  const [collabNodes, setCollabNodes] = useState<CollaborationNode[]>([])
  const [collabLinks, setCollabLinks] = useState<CollaborationLink[]>([])
  const [genealogyLoading, setGenealogyLoading] = useState(false)
  const [genealogyRoot, setGenealogyRoot] = useState<GenealogyNode | null>(null)
  const [genealogyNodes, setGenealogyNodes] = useState<GenealogyNode[]>([])
  const [genealogyLinks, setGenealogyLinks] = useState<GenealogyLink[]>([])
  const [genealogyError, setGenealogyError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (id) {
      fetchTalentDetail(parseInt(id))
    }
  }, [id])

  const fetchTalentDetail = async (talentId: number) => {
    setLoading(true)
    setLoadError(null)
    try {
      const response = await api.talents.get(talentId)
      setTalent(response.data)
    } catch (error) {
      logger.error('Failed to fetch talent detail:', error)
      setLoadError(getErrorMessage(error, t('detail.loadError')))
    } finally {
      setLoading(false)
    }
  }

  const fetchCollaborations = async (talentId: number) => {
    setCollabLoading(true)
    try {
      const response = await api.talents.getCollaborations(talentId)
      setCollabNodes(response.data.nodes || [])
      setCollabLinks(response.data.links || [])
    } catch (error) {
      logger.error('Failed to fetch collaborations:', error)
      message.error(getErrorMessage(error, t('detail.collabError')))
    } finally {
      setCollabLoading(false)
    }
  }

  const fetchGenealogy = async (talentId: number) => {
    setGenealogyLoading(true)
    setGenealogyError(null)
    try {
      const response = await api.talents.getGenealogy(talentId)
      setGenealogyRoot(response.data.root_talent || null)
      setGenealogyNodes(response.data.nodes || [])
      setGenealogyLinks(response.data.links || [])
    } catch (error: any) {
      logger.error('Failed to fetch genealogy:', error)
      const msg = error?.response?.data?.detail || getErrorMessage(error, t('detail.genealogyError'))
      setGenealogyError(msg)
      setGenealogyRoot(null)
      setGenealogyNodes([])
      setGenealogyLinks([])
    } finally {
      setGenealogyLoading(false)
    }
  }

  // Fetch collaborations and genealogy when talent is loaded
  useEffect(() => {
    if (talent) {
      fetchCollaborations(talent.talent_id)
      fetchGenealogy(talent.talent_id)
    }
  }, [talent])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!talent) {
    return (
      <Card>
        {loadError ? (
          <Empty description={loadError}>
            <Button type="primary" onClick={() => id && fetchTalentDetail(parseInt(id))}>
              {t('common:actions.retry')}
            </Button>
          </Empty>
        ) : (
          <Empty description={t('detail.notFound')} />
        )}
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigateBack(navigate, '/search-recommend')}>{t('detail.back')}</Button>
        </div>
      </Card>
    )
  }

  const roleConfig = getRoleTypeConfig(talent.role_type)
  const roleKey = LEGACY_ROLE_TYPE_MAP[talent.role_type] || talent.role_type

  const workColumns = [
    {
      title: t('columns.year'),
      dataIndex: 'publication_year',
      key: 'publication_year',
      width: 80,
      render: (year: number | null) => year || '-',
    },
    {
      title: t('columns.workTitle'),
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string, record: SelectedWork) => {
        if (record.doi) {
          return (
            <a href={`https://doi.org/${record.doi}`} target="_blank" rel="noopener noreferrer">
              {title}
            </a>
          )
        }
        return title
      },
    },
    {
      title: t('columns.venue'),
      dataIndex: 'venue_name',
      key: 'venue_name',
      width: 200,
      ellipsis: true,
      render: (venue: string | null) => venue || '-',
    },
    {
      title: t('columns.citationCount'),
      dataIndex: 'citation_count',
      key: 'citation_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => formatNumber(count),
    },
  ]

  const completeness = talent.data_completeness ?? calculateCompleteness(talent)

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* 返回按钮 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Button type="link" onClick={() => navigateBack(navigate, '/search-recommend')} style={{ paddingLeft: 0 }}>
          <ArrowLeftOutlined /> {t('detail.back')}
        </Button>
        <FavoriteButton talentId={talent.talent_id} showText />
      </div>

      {/* 待确认项提示 */}
      {talent.pending_confirm_items && talent.pending_confirm_items.length > 0 && (
        <Alert
          type="warning"
          icon={<ExclamationCircleOutlined />}
          message={t('detail.pendingConfirm')}
          description={
            <Space direction="vertical" size={4}>
              {talent.pending_confirm_items.map((item, index) => (
                <Text key={index}>• {item}</Text>
              ))}
            </Space>
          }
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 基本信息卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col flex="auto">
            <Space direction="vertical" size={8}>
              <Title level={2} style={{ margin: 0 }}>
                <UserOutlined style={{ marginRight: 8, color: semanticColors.blue }} />
                {talent.name}
                {talent.name_en && (
                  <Text type="secondary" style={{ fontSize: 18, marginLeft: 8 }}>
                    ({talent.name_en})
                  </Text>
                )}
              </Title>
              <Space size={8}>
                <Tag color={roleConfig.color} style={{ fontSize: 14, padding: '2px 8px' }}>
                  {t(`roles.${roleKey}`, { defaultValue: roleConfig.text })}
                </Tag>
                {talent.is_graduated && (
                  <Tag color="orange">{t('detail.graduated')}</Tag>
                )}
                {/* Display education school */}
                {talent.education_school_name && (
                  <Tooltip title={t('detail.educationSchool')}>
                    <Tag
                      icon={<BankOutlined />}
                      color="blue"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/schools/${talent.education_school_id}`)}
                    >
                      {talent.education_school_name}
                    </Tag>
                  </Tooltip>
                )}
                {/* Display company school if different from education */}
                {talent.company_school_name && talent.company_school_name !== talent.education_school_name && (
                  <Tooltip title={t('detail.companySchool')}>
                    <Tag
                      icon={<BankOutlined />}
                      color="green"
                      style={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/schools/${talent.company_school_id}`)}
                    >
                      {talent.company_school_name}
                    </Tag>
                  </Tooltip>
                )}
                {/* Fallback to legacy school_name if no new fields */}
                {!talent.education_school_name && !talent.company_school_name && talent.school_name && (
                  <Tag
                    icon={<BankOutlined />}
                    color="blue"
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/schools/${talent.school_id}`)}
                  >
                    {talent.school_name}
                  </Tag>
                )}
                {talent.current_title && <Text type="secondary">{talent.current_title}</Text>}
              </Space>
              {talent.summary && (
                <Paragraph type="secondary" style={{ margin: 0, maxWidth: 800 }}>
                  {talent.summary}
                </Paragraph>
              )}
            </Space>
          </Col>
          <Col>
            <Space direction="vertical" align="end">
              {/* 数据完整度 */}
              <div style={{ textAlign: 'center', marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{t('detail.dataCompleteness')}</Text>
                <Progress
                  percent={completeness}
                  size="small"
                  style={{ width: 120 }}
                  strokeColor={completeness >= 80 ? semanticColors.green : completeness >= 50 ? semanticColors.gold : semanticColors.red}
                />
              </div>
              {talent.orcid && (
                <a
                  href={talent.orcid.startsWith('http') ? talent.orcid : `https://orcid.org/${talent.orcid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Tag icon={<GlobalOutlined />} color="green">
                    ORCID: {talent.orcid.replace('https://orcid.org/', '').replace('http://orcid.org/', '')}
                  </Tag>
                </a>
              )}
              {talent.role_reason && (
                <Tooltip title={t('detail.roleBasis')}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {talent.role_reason}
                  </Text>
                </Tooltip>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        {/* 学术统计 */}
        <Col xs={24} lg={8}>
          <Card title={<><TrophyOutlined style={{ marginRight: 8 }} />{t('detail.metricsTitle')}</>} style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title={t('detail.papers')}
                  value={talent.works_count}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: semanticColors.blue }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('detail.citations')}
                  value={talent.cited_by_count}
                  valueStyle={{ color: semanticColors.green }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('detail.hIndex')}
                  value={talent.h_index}
                  valueStyle={{ color: semanticColors.purple }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={t('detail.latestActiveYear')}
                  value={talent.latest_active_year || '-'}
                  valueStyle={{ color: semanticColors.gold }}
                />
              </Col>
              {talent.academic_age && (
                <Col span={12}>
                  <Statistic
                    title={t('detail.academicAge')}
                    value={talent.academic_age}
                    suffix={t('detail.yearsUnit')}
                  />
                </Col>
              )}
            </Row>
          </Card>

          {/* 招聘判断摘要 - v1.1新增 */}
          {talent.recruitment_summary && (
            <Card
              title={<><BulbOutlined style={{ marginRight: 8 }} />{t('detail.recruitmentSummary')}</>}
              style={{ marginBottom: 16 }}
              styles={{ body: { backgroundColor: semanticColors.greenBg } }}
            >
              <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {talent.recruitment_summary}
              </Paragraph>
            </Card>
          )}
        </Col>

        {/* 研究方向 */}
        <Col xs={24} lg={16}>
          {/* 研究方向 - CR-02: 使用OpenAlex研究主题 */}
          <Card title={<><BulbOutlined style={{ marginRight: 8 }} />{t('detail.researchDirections')}</>} style={{ marginBottom: 16 }}>
            {talent.openalex_topics && talent.openalex_topics.length > 0 ? (
              <Space size={[8, 16]} wrap>
                {talent.openalex_topics.map((topic, index) => (
                  <Tag
                    key={index}
                    style={{
                      fontSize: 14,
                      padding: '4px 12px',
                      background: `hsl(${(index * 60) % 360}, 70%, 95%)`,
                      border: `1px solid hsl(${(index * 60) % 360}, 70%, 85%)`,
                      cursor: 'pointer',
                    }}
                    onClick={() => navigate(`/search-recommend?q=${encodeURIComponent(topic)}`)}
                  >
                    {topic}
                  </Tag>
                ))}
              </Space>
            ) : talent.topic_tags.length > 0 ? (
              <Space size={[8, 16]} wrap>
                {talent.topic_tags.map((tag, index) => (
                  <Tag
                    key={index}
                    style={{
                      fontSize: 14,
                      padding: '4px 12px',
                      background: `hsl(${(index * 60) % 360}, 70%, 95%)`,
                      border: `1px solid hsl(${(index * 60) % 360}, 70%, 85%)`,
                      cursor: 'pointer',
                    }}
                    onClick={() => navigate(`/search-recommend?q=${encodeURIComponent(tag)}`)}
                  >
                    {tag}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Empty description={t('detail.noResearch')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
            {talent.research_interests && (
              <>
                <Divider style={{ margin: '16px 0' }} />
                <Text type="secondary">{talent.research_interests}</Text>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* 机构信息 */}
      {(talent.department_name || talent.lab_name) && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions column={2}>
            {talent.department_name && (
              <Descriptions.Item label={t('detail.department')}>{talent.department_name}</Descriptions.Item>
            )}
            {talent.lab_name && (
              <Descriptions.Item label={t('detail.lab')}>{talent.lab_name}</Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}

      {/* 代表作品 */}
      <Card title={<><FileTextOutlined style={{ marginRight: 8 }} />{t('detail.selectedWorks')}</>} style={{ marginBottom: 16 }}>
        {talent.selected_works.length > 0 ? (
          <Table
            dataSource={talent.selected_works}
            columns={workColumns}
            rowKey="work_id"
            pagination={false}
            size="small"
          />
        ) : (
          <Empty description={t('detail.noWorks')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* 合作网络 + 学术族谱 */}
      <Card>
        <Tabs
          defaultActiveKey="collaboration"
          items={[
            {
              key: 'collaboration',
              label: (
                <span>
                  <TeamOutlined style={{ marginRight: 6 }} />
                  {t('detail.collaborationTab')}
                </span>
              ),
              children: collabLoading ? (
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Spin size="large" />
                </div>
              ) : collabNodes.length > 0 ? (
                <CollaborationGraph
                  nodes={collabNodes}
                  links={collabLinks}
                  loading={collabLoading}
                  onNodeClick={(nodeId) => {
                    if (nodeId !== String(talent.talent_id)) {
                      navigate(`/talents/${nodeId}`)
                    }
                  }}
                />
              ) : (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="secondary">{t('detail.noCollab')}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('detail.noCollabHint')}
                      </Text>
                    </Space>
                  }
                />
              ),
            },
            {
              key: 'genealogy',
              label: (
                <span>
                  <GlobalOutlined style={{ marginRight: 6 }} />
                  {t('detail.genealogyTab')}
                </span>
              ),
              children: genealogyError ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="danger">{t('detail.genealogyFailed')}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {genealogyError}
                      </Text>
                    </Space>
                  }
                >
                  <Button onClick={() => fetchGenealogy(talent.talent_id)}>{t('common:actions.retry')}</Button>
                </Empty>
              ) : genealogyLoading ? (
                <div style={{ textAlign: 'center', padding: '100px 0' }}>
                  <Spin size="large" />
                </div>
              ) : genealogyRoot ? (
                <GenealogyGraph
                  rootTalent={genealogyRoot}
                  nodes={genealogyNodes}
                  links={genealogyLinks}
                  loading={genealogyLoading}
                  onNodeClick={(nodeId) => {
                    if (nodeId !== talent.talent_id) {
                      navigate(`/talents/${nodeId}`)
                    }
                  }}
                />
              ) : (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="secondary">{t('detail.noGenealogy')}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t('detail.noGenealogyHint')}
                      </Text>
                    </Space>
                  }
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

// Helper function to calculate completeness
function calculateCompleteness(talent: TalentDetail): number {
  let score = 0
  const weights = {
    name: 10,
    school: 15,
    role: 15,
    title: 10,
    works: 10,
    citations: 10,
    h_index: 5,
    topic_tags: 10,
    research_interests: 5,
    orcid: 5,
  }

  if (talent.name) score += weights.name
  if (talent.school_id) score += weights.school
  if (talent.role_type && talent.role_type !== 'unknown') score += weights.role
  if (talent.current_title) score += weights.title
  if (talent.works_count > 0) score += weights.works
  if (talent.cited_by_count > 0) score += weights.citations
  if (talent.h_index > 0) score += weights.h_index
  if (talent.topic_tags && talent.topic_tags.length > 0) score += weights.topic_tags
  if (talent.research_interests) score += weights.research_interests
  if (talent.orcid) score += weights.orcid

  return score
}

export default TalentDetailPage
