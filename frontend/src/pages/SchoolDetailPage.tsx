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
  Empty,
  Tabs,
  Badge,
} from 'antd'
import {
  BankOutlined,
  GlobalOutlined,
  TeamOutlined,
  UserOutlined,
  ArrowLeftOutlined,
  TrophyOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

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
}

interface TalentListResponse {
  items: Talent[]
  total: number
  page: number
  page_size: number
}

const roleTypeMap: Record<string, { color: string; text: string }> = {
  professor: { color: 'green', text: '教授' },
  student: { color: 'blue', text: '学生' },
  graduated: { color: 'orange', text: '毕业生' },
  unknown: { color: 'default', text: '未知' },
}

const SchoolDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [school, setSchool] = useState<SchoolDetail | null>(null)
  const [talents, setTalents] = useState<Talent[]>([])
  const [talentsLoading, setTalentsLoading] = useState(false)
  const [talentsTotal, setTalentsTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [roleFilter, setRoleFilter] = useState<string | undefined>()
  const pageSize = 20

  useEffect(() => {
    if (id) {
      fetchSchoolDetail(parseInt(id))
    }
  }, [id])

  useEffect(() => {
    if (school) {
      fetchTalents(1)
    }
  }, [school, roleFilter])

  const fetchSchoolDetail = async (schoolId: number) => {
    setLoading(true)
    try {
      const response = await api.schools.get(schoolId)
      setSchool(response.data)
    } catch (error) {
      console.error('Failed to fetch school detail:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTalents = async (pageNum: number) => {
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
      console.error('Failed to fetch talents:', error)
    } finally {
      setTalentsLoading(false)
    }
  }

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
        <Empty description="未找到该学校信息" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate(-1)}>返回</Button>
        </div>
      </Card>
    )
  }

  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
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
      title: '角色',
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = roleTypeMap[role] || roleTypeMap.unknown
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '职位',
      dataIndex: 'current_title',
      key: 'current_title',
      ellipsis: true,
      render: (title: string | null) => title || '-',
    },
    {
      title: '论文',
      dataIndex: 'works_count',
      key: 'works_count',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '引用',
      dataIndex: 'cited_by_count',
      key: 'cited_by_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '研究方向',
      dataIndex: 'topic_tags',
      key: 'topic_tags',
      width: 200,
      render: (tags: string[]) => (
        <Space size={4} wrap>
          {(tags || []).slice(0, 2).map(tag => (
            <Tag key={tag} style={{ margin: 0, fontSize: 11 }}>
              {tag}
            </Tag>
          ))}
          {tags && tags.length > 2 && (
            <span style={{ fontSize: 11, color: '#999' }}>+{tags.length - 2}</span>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* 返回按钮 */}
      <Button type="link" onClick={() => navigate(-1)} style={{ paddingLeft: 0, marginBottom: 16 }}>
        <ArrowLeftOutlined /> 返回
      </Button>

      {/* 学校基本信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={24}>
          <Col flex="auto">
            <Space direction="vertical" size={8}>
              <Title level={2} style={{ margin: 0 }}>
                <BankOutlined style={{ marginRight: 8, color: '#1890ff' }} />
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
                    <Tag color="green">访问官网</Tag>
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
              title="总人才数"
              value={school.talent_count}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="教授"
              value={school.professor_count}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="学生"
              value={school.student_count}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title="毕业生"
              value={school.graduate_count}
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
        </Row>
      </Card>

      {/* 人才列表 */}
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>人才列表</span>
            <Badge count={talentsTotal} showZero style={{ backgroundColor: '#1890ff' }} />
          </Space>
        }
        extra={
          <Space>
            <Text type="secondary">筛选:</Text>
            <Tag
              color={!roleFilter ? 'blue' : 'default'}
              style={{ cursor: 'pointer' }}
              onClick={() => setRoleFilter(undefined)}
            >
              全部
            </Tag>
            {Object.entries(roleTypeMap).map(([key, config]) => (
              <Tag
                key={key}
                color={roleFilter === key ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => setRoleFilter(key)}
              >
                {config.text}
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
            showTotal: (total) => `共 ${total} 位人才`,
          }}
          onChange={(pagination) => fetchTalents(pagination.current || 1)}
          locale={{
            emptyText: <Empty description="该学校暂无人才数据" />,
          }}
        />
      </Card>
    </div>
  )
}

export default SchoolDetailPage
