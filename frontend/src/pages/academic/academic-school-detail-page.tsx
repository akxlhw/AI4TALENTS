import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { logger } from '../../utils/logger'
import { navigateBack } from '../../utils/navigation'
import {
  Card,
  Typography,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  Table,
  Spin,
  Button,
  Empty,
  Badge,
  message,
} from 'antd'
import {
  BankOutlined,
  GlobalOutlined,
  TeamOutlined,
  UserOutlined,
  TrophyOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { semanticColors } from '../../theme'
import { getRoleTypeConfig, LEGACY_ROLE_TYPE_MAP, ROLE_TYPE_MAP } from '../../constants/roleType'
import TopicTags from '../../components/TopicTags'
import { formatNumber } from '../../utils/format'
import { getErrorMessage } from '../../utils'
import '../../i18n/namespaces/academic'

const { Title, Text, Paragraph } = Typography

interface SchoolDetail {
  school_id: number
  school_name: string
  school_alias: string | null
  country_id: number
  country_name: string | null
  country_code: string | null
  school_intro: string | null
  homepage_url: string | null
  professor_count: number
  student_count: number
  talent_count: number
  graduate_count: number
  unknown_count: number
}

interface Talent {
  talent_id: number
  name: string
  name_en: string | null
  role_type: string
  role_confidence: number
  school_id: number | null
  school_name: string | null
  current_title: string | null
  works_count: number
  cited_by_count: number
  h_index: number
  topic_tags: string[]
  openalex_topics: string[]  // OpenAlex研究主题（具体研究方向）
}

interface TalentListResponse {
  items: Talent[]
  total: number
  page: number
  page_size: number
}

const SchoolDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(['academic', 'common'])
  const [loading, setLoading] = useState(true)
  const [school, setSchool] = useState<SchoolDetail | null>(null)
  const [talents, setTalents] = useState<Talent[]>([])
  const [talentsLoading, setTalentsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [talentsTotal, setTalentsTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const pageSize = 20

  const fetchSchoolDetail = useCallback(async (schoolId: number) => {
    setLoading(true)
    setLoadError(null)
    try {
      const response = await api.schools.get(schoolId)
      setSchool(response.data)
    } catch (error) {
      logger.error('Failed to fetch school detail:', error)
      setLoadError(getErrorMessage(error, t('schoolDetail.loadError')))
    } finally {
      setLoading(false)
    }
  }, [t])

  const fetchTalents = useCallback(async (pageNum: number) => {
    if (!school) return

    setTalentsLoading(true)
    try {
      const response = await api.schools.getTalents(school.school_id, {
        role_type: roleFilter,
        page: pageNum,
      })
      const data: TalentListResponse = response.data
      setTalents(data.items)
      setTalentsTotal(data.total)
      setPage(pageNum)
    } catch (error) {
      logger.error('Failed to fetch talents:', error)
      message.error(getErrorMessage(error, t('schoolDetail.loadTalentsError')))
    } finally {
      setTalentsLoading(false)
    }
  }, [school, roleFilter, t])

  useEffect(() => {
    if (id) {
      fetchSchoolDetail(parseInt(id))
    }
  }, [id, fetchSchoolDetail])

  useEffect(() => {
    if (school) {
      fetchTalents(1)
    }
  }, [school, fetchTalents])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!school) {
    return (
      <Card>
        {loadError ? (
          <Empty description={loadError}>
            <Button type="primary" onClick={() => id && fetchSchoolDetail(parseInt(id))}>
              {t('common:actions.retry')}
            </Button>
          </Empty>
        ) : (
          <Empty description={t('schoolDetail.notFound')} />
        )}
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigateBack(navigate, '/country-school')}>{t('detail.back')}</Button>
        </div>
      </Card>
    )
  }

  const columns = [
    {
      title: t('columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 160,
      render: (name: string, record: Talent) => (
        <a onClick={() => navigate(`/talents/${record.talent_id}`)}>
          <Space direction="vertical" size={0}>
            <span style={{ fontWeight: 500 }}>{name}</span>
            {record.name_en && (
              <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>
            )}
          </Space>
        </a>
      ),
    },
    {
      title: t('columns.role'),
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = getRoleTypeConfig(role)
        const roleKey = LEGACY_ROLE_TYPE_MAP[role] || role
        return <Tag color={config.color}>{t(`roles.${roleKey}`, { defaultValue: config.text })}</Tag>
      },
    },
    {
      title: t('columns.works'),
      dataIndex: 'works_count',
      key: 'works_count',
      width: 80,
      align: 'center' as const,
    },
    {
      title: t('columns.citations'),
      dataIndex: 'cited_by_count',
      key: 'cited_by_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => formatNumber(count),
    },
    {
      title: t('columns.hIndex'),
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
    },
    {
      title: t('columns.researchDirections'),
      dataIndex: 'openalex_topics',
      key: 'openalex_topics',
      width: 200,
      render: (topics: string[], record: Talent) => {
        // 优先显示 openalex_topics，没有则回退到 topic_tags
        const displayTopics = topics && topics.length > 0 ? topics : record.topic_tags
        return <TopicTags tags={displayTopics} maxVisible={2} />
      },
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* 学校基本信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col flex="auto">
            <Space direction="vertical" size={8}>
              <Title level={2} style={{ margin: 0 }}>
                <BankOutlined style={{ marginRight: 8, color: semanticColors.blue }} />
                {school.school_name}
                {school.school_alias && (
                  <Text type="secondary" style={{ fontSize: 18, marginLeft: 8 }}>
                    ({school.school_alias})
                  </Text>
                )}
              </Title>
              <Space size={8}>
                {school.country_name && (
                  <Tag icon={<GlobalOutlined />} color="blue">
                    {school.country_name} ({school.country_code})
                  </Tag>
                )}
                {school.homepage_url && (
                  <a href={school.homepage_url} target="_blank" rel="noopener noreferrer">
                    <Tag color="green">{t('schoolDetail.visitHomepage')}</Tag>
                  </a>
                )}
              </Space>
              {school.school_intro && (
                <Paragraph type="secondary" style={{ margin: 0, maxWidth: 800 }}>
                  {school.school_intro}
                </Paragraph>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 人才统计 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('stats.totalTalentCount')}
              value={school.talent_count}
              prefix={<TeamOutlined />}
              valueStyle={{ color: semanticColors.blue }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('stats.professors')}
              value={school.professor_count}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: semanticColors.green }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('stats.students')}
              value={school.student_count}
              prefix={<UserOutlined />}
              valueStyle={{ color: semanticColors.gold }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('stats.graduates')}
              value={school.graduate_count}
              valueStyle={{ color: semanticColors.purple }}
            />
          </Col>
        </Row>
      </Card>

      {/* 人才列表 */}
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>{t('schoolDetail.talentsTitle')}</span>
            <Badge count={talentsTotal} showZero style={{ backgroundColor: semanticColors.blue }} />
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">{t('filters.label')}</Text>
            <Tag
              color={!roleFilter ? 'blue' : 'default'}
              style={{ cursor: 'pointer' }}
              onClick={() => setRoleFilter(undefined)}
            >
              {t('schoolDetail.allRoles')}
            </Tag>
            {Object.entries(ROLE_TYPE_MAP).map(([key, config]) => (
              <Tag
                key={key}
                color={roleFilter === key ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => setRoleFilter(key)}
              >
                {t(`roles.${key}`, { defaultValue: config.text })}
              </Tag>
            ))}
          </Space>
        }
      >
        <Table
          dataSource={talents}
          columns={columns}
          rowKey="talent_id"
          loading={talentsLoading}
          pagination={{
            current: page,
            pageSize,
            total: talentsTotal,
            showSizeChanger: false,
            showTotal: (total) => t('schoolDetail.talentsTotal', { n: total }),
          }}
          onChange={(pagination) => fetchTalents(pagination.current || 1)}
          locale={{
            emptyText: <Empty description={t('schoolDetail.empty')} />,
          }}
        />
      </Card>
    </div>
  )
}

export default SchoolDetailPage
