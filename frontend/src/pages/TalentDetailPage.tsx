import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
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
} from 'antd'
import {
  UserOutlined,
  BankOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
  GlobalOutlined,
  TrophyOutlined,
  TeamOutlined,
  AppstoreOutlined,
  ExclamationCircleOutlined,
  BulbOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import FavoriteButton from '../components/FavoriteButton'
import CollaborationGraph, { CollaborationNode, CollaborationLink } from '../components/CollaborationGraph'

const { Title, Text, Paragraph } = Typography

interface TechTag {
  tech_element_id: number
  tech_element_name: string
  tech_direction_id: number
  tech_direction_name: string
  tag_level: string
  confidence_score: number
  confirm_status: string
}

interface TalentDetail {
  talent_id: number
  name: string
  name_en: string | null
  orcid: string | null
  role_type: string
  role_confidence: number
  school_id: number | null
  school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  latest_active_year: number | null
  topic_tags: string[]
  research_interests: string | null
  summary: string | null
  department_name: string | null
  lab_name: string | null
  role_reason: string | null
  academic_age: number | null
  selected_works: SelectedWork[]
  // v1.1 新增字段
  tech_tags?: TechTag[]
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

const roleTypeMap: Record<string, { color: string; text: string }> = {
  professor: { color: 'green', text: '教授' },
  student: { color: 'blue', text: '学生' },
  graduated: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
}

const confirmStatusMap: Record<string, { color: string; text: string }> = {
  confirmed: { color: 'success', text: '已确认' },
  auto_identified: { color: 'processing', text: '自动识别' },
  pending_confirm: { color: 'warning', text: '待确认' },
}

const TalentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [talent, setTalent] = useState<TalentDetail | null>(null)
  const [collabLoading, setCollabLoading] = useState(false)
  const [collabNodes, setCollabNodes] = useState<CollaborationNode[]>([])
  const [collabLinks, setCollabLinks] = useState<CollaborationLink[]>([])

  useEffect(() => {
    if (id) {
      fetchTalentDetail(parseInt(id))
    }
  }, [id])

  const fetchTalentDetail = async (talentId: number) => {
    setLoading(true)
    try {
      const response = await api.talents.get(talentId)
      setTalent(response.data)
    } catch (error) {
      console.error('Failed to fetch talent detail:', error)
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
      console.error('Failed to fetch collaborations:', error)
    } finally {
      setCollabLoading(false)
    }
  }

  // Fetch collaborations when talent is loaded
  useEffect(() => {
    if (talent) {
      fetchCollaborations(talent.talent_id)
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
        <Empty description="未找到该人才信息" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate(-1)}>返回</Button>
        </div>
      </Card>
    )
  }

  const roleConfig = roleTypeMap[talent.role_type] || roleTypeMap.unknown

  const workColumns = [
    {
      title: '年份',
      dataIndex: 'publication_year',
      key: 'publication_year',
      width: 80,
      render: (year: number | null) => year || '-',
    },
    {
      title: '标题',
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
      title: '期刊/会议',
      dataIndex: 'venue_name',
      key: 'venue_name',
      width: 200,
      ellipsis: true,
      render: (venue: string | null) => venue || '-',
    },
    {
      title: '引用数',
      dataIndex: 'citation_count',
      key: 'citation_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count.toLocaleString(),
    },
  ]

  // 计算数据完整度
  const completeness = talent.data_completeness ?? calculateCompleteness(talent)

  return (
    <div>
      {/* 返回按钮 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Button type="link" onClick={() => navigate(-1)} style={{ paddingLeft: 0 }}>
          <ArrowLeftOutlined /> 返回
        </Button>
        <FavoriteButton talentId={talent.talent_id} showText />
      </div>

      {/* 待确认项提示 */}
      {talent.pending_confirm_items && talent.pending_confirm_items.length > 0 && (
        <Alert
          type="warning"
          icon={<ExclamationCircleOutlined />}
          message="存在待确认信息"
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
                <UserOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                {talent.name}
                {talent.name_en && (
                  <Text type="secondary" style={{ fontSize: 18, marginLeft: 8 }}>
                    ({talent.name_en})
                  </Text>
                )}
              </Title>
              <Space size={8}>
                <Tag color={roleConfig.color} style={{ fontSize: 14, padding: '2px 8px' }}>
                  {roleConfig.text}
                </Tag>
                {talent.is_graduated && (
                  <Tag color="orange">已毕业</Tag>
                )}
                {talent.school_name && (
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
                <Text type="secondary" style={{ fontSize: 12 }}>数据完整度</Text>
                <Progress
                  percent={completeness}
                  size="small"
                  style={{ width: 120 }}
                  strokeColor={completeness >= 80 ? '#52c41a' : completeness >= 50 ? '#faad14' : '#ff4d4f'}
                />
              </div>
              {talent.orcid && (
                <a
                  href={`https://orcid.org/${talent.orcid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Tag icon={<GlobalOutlined />} color="green">
                    ORCID: {talent.orcid}
                  </Tag>
                </a>
              )}
              {talent.role_reason && (
                <Tooltip title="角色识别依据">
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
          <Card title={<><TrophyOutlined style={{ marginRight: 8 }} />学术指标</>} style={{ marginBottom: 16 }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="发表论文"
                  value={talent.works_count}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="总引用数"
                  value={talent.cited_by_count}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="H指数"
                  value={talent.h_index}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="最近活跃年份"
                  value={talent.latest_active_year || '-'}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              {talent.academic_age && (
                <Col span={12}>
                  <Statistic
                    title="学术年龄"
                    value={talent.academic_age}
                    suffix="年"
                  />
                </Col>
              )}
            </Row>
          </Card>

          {/* 招聘判断摘要 - v1.1新增 */}
          {talent.recruitment_summary && (
            <Card
              title={<><BulbOutlined style={{ marginRight: 8 }} />招聘判断摘要</>}
              style={{ marginBottom: 16 }}
              bodyStyle={{ backgroundColor: '#f6ffed' }}
            >
              <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {talent.recruitment_summary}
              </Paragraph>
            </Card>
          )}
        </Col>

        {/* 研究方向 & 技术标签 */}
        <Col xs={24} lg={16}>
          {/* 技术要素与技术方向 - v1.1新增 */}
          {talent.tech_tags && talent.tech_tags.length > 0 && (
            <Card
              title={<><AppstoreOutlined style={{ marginRight: 8 }} />技术要素与技术方向</>}
              style={{ marginBottom: 16 }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {Object.entries(groupBy(talent.tech_tags, 'tech_element_name')).map(([element, tags]) => (
                  <div key={element}>
                    <Text strong style={{ marginBottom: 4, display: 'block' }}>{element}</Text>
                    <Space size={4} wrap>
                      {tags.map((tag, index) => (
                        <Tooltip
                          key={index}
                          title={`置信度: ${(tag.confidence_score * 100).toFixed(0)}% | ${confirmStatusMap[tag.confirm_status]?.text || tag.confirm_status}`}
                        >
                          <Tag
                            color={tag.tag_level === 'primary' ? 'blue' : 'default'}
                            style={{ marginBottom: 4 }}
                          >
                            {tag.tech_direction_name}
                            {tag.confirm_status === 'pending_confirm' && (
                              <ExclamationCircleOutlined style={{ marginLeft: 4, color: '#faad14' }} />
                            )}
                          </Tag>
                        </Tooltip>
                      ))}
                    </Space>
                  </div>
                ))}
              </Space>
            </Card>
          )}

          {/* 研究方向 */}
          <Card title="研究方向" style={{ marginBottom: 16 }}>
            {talent.topic_tags.length > 0 ? (
              <Space size={[8, 16]} wrap>
                {talent.topic_tags.map((tag, index) => (
                  <Tag
                    key={index}
                    style={{
                      fontSize: 14,
                      padding: '4px 12px',
                      background: `hsl(${(index * 60) % 360}, 70%, 95%)`,
                      border: `1px solid hsl(${(index * 60) % 360}, 70%, 85%)`,
                    }}
                  >
                    {tag}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Empty description="暂无研究方向数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
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
              <Descriptions.Item label="院系">{talent.department_name}</Descriptions.Item>
            )}
            {talent.lab_name && (
              <Descriptions.Item label="实验室">{talent.lab_name}</Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}

      {/* 代表作品 */}
      <Card title={<><FileTextOutlined style={{ marginRight: 8 }} />代表作品</>} style={{ marginBottom: 16 }}>
        {talent.selected_works.length > 0 ? (
          <Table
            dataSource={talent.selected_works}
            columns={workColumns}
            rowKey="work_id"
            pagination={false}
            size="small"
          />
        ) : (
          <Empty description="暂无代表作品数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* 合作网络 */}
      <Card title={<><TeamOutlined style={{ marginRight: 8 }} />合作网络</>}>
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
      </Card>
    </div>
  )
}

// Helper function to group tech tags by element
function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((result, item) => {
    const groupKey = String(item[key])
    if (!result[groupKey]) {
      result[groupKey] = []
    }
    result[groupKey].push(item)
    return result
  }, {} as Record<string, T[]>)
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
    tech_tags: 5,
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
  if (talent.tech_tags && talent.tech_tags.length > 0) score += weights.tech_tags

  return score
}

export default TalentDetailPage
