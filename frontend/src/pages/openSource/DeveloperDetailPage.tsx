import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Typography,
  Button,
  Tabs,
  Spin,
  Empty,
  Table,
  Statistic,
  } from 'antd'
import {
  ArrowLeftOutlined,
  GithubOutlined,
  StarOutlined,
  ForkOutlined,
  HeartOutlined,
  HeartFilled,
  GlobalOutlined,
  MailOutlined,
  UserOutlined,
  BranchesOutlined,
  CodeOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { OSDeveloperDetail, OSRepository, OSContribution } from '../../types'

const { Title, Text, Paragraph } = Typography

const DeveloperDetailPage: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const developerId = parseInt(id || '0')

  const [detail, setDetail] = useState<OSDeveloperDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [isFavorite, setIsFavorite] = useState(false)
  const [activeTab, setActiveTab] = useState('repositories')

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true)
        const [detailRes, favoriteRes] = await Promise.all([
          api.openSource.getDeveloper(developerId),
          api.openSource.getFavoriteIds(),
        ])
        setDetail(detailRes.data)
        setIsFavorite((favoriteRes.data.developer_ids || []).includes(developerId))
      } catch (e) {
        console.error('Failed to load developer detail', e)
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [developerId])

  const handleToggleFavorite = async () => {
    try {
      if (isFavorite) {
        await api.openSource.removeFavorite(developerId)
        setIsFavorite(false)
      } else {
        await api.openSource.addFavorite(developerId)
        setIsFavorite(true)
      }
    } catch (e) {
      console.error('Favorite toggle failed', e)
    }
  }

  const primary = '#2D3748'
  const secondary = '#48BB78'

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!detail) {
    return (
      <div style={{ padding: '88px 32px 80px' }}>
        <Empty description="开发者不存在或已被移除" />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate('/opensource')} icon={<ArrowLeftOutlined />}>
            返回开源首页
          </Button>
        </div>
      </div>
    )
  }

  const repoColumns = [
    {
      title: '仓库',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (text: string) => (
        <a href={`https://github.com/${text}`} target="_blank" rel="noopener noreferrer" style={{ fontFamily: 'monospace', fontSize: 13 }}>
          <GithubOutlined style={{ marginRight: 6 }} />
          {text}
        </a>
      ),
    },
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      render: (lang: string | null) => lang ? <Tag>{lang}</Tag> : '-',
      width: 120,
    },
    {
      title: 'Stars',
      dataIndex: 'stars_count',
      key: 'stars_count',
      render: (stars: number) => (
        <Space><StarOutlined style={{ color: '#F6AD55' }} />{stars}</Space>
      ),
      width: 120,
      sorter: (a: OSRepository, b: OSRepository) => a.stars_count - b.stars_count,
    },
    {
      title: 'Forks',
      dataIndex: 'forks_count',
      key: 'forks_count',
      render: (forks: number) => (
        <Space><ForkOutlined />{forks}</Space>
      ),
      width: 120,
    },
  ]

  const contributionColumns = [
    {
      title: '仓库',
      dataIndex: 'repo_full_name',
      key: 'repo_full_name',
      render: (text: string) => <Text style={{ fontFamily: 'monospace', fontSize: 13 }}>{text}</Text>,
    },
    {
      title: 'Commits',
      dataIndex: 'commits_count',
      key: 'commits_count',
      width: 100,
    },
    {
      title: 'PRs',
      dataIndex: 'prs_count',
      key: 'prs_count',
      width: 100,
    },
    {
      title: 'Issues',
      dataIndex: 'issues_count',
      key: 'issues_count',
      width: 100,
    },
    {
      title: '身份',
      key: 'role',
      width: 120,
      render: (_: unknown, record: OSContribution) => (
        <Space>
          {record.is_owner && <Tag color="blue">Owner</Tag>}
          {record.is_maintainer && <Tag color="green">Maintainer</Tag>}
        </Space>
      ),
    },
  ]

  const languageColumns = [
    {
      title: '语言',
      dataIndex: 'language',
      key: 'language',
      render: (lang: string) => <Tag color="processing">{lang}</Tag>,
    },
    {
      title: '仓库数',
      dataIndex: 'repo_count',
      key: 'repo_count',
      width: 100,
    },
    {
      title: '熟练度',
      dataIndex: 'proficiency_score',
      key: 'proficiency_score',
      width: 200,
      render: (score: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 8, background: '#E2E8F0', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(score * 10, 100)}%`, height: '100%', background: secondary, borderRadius: 4 }} />
          </div>
          <Text style={{ fontSize: 12, minWidth: 32 }}>{score.toFixed(1)}</Text>
        </div>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'repositories',
      label: (
        <span>
          <GithubOutlined style={{ marginRight: 6 }} />
          仓库 ({detail.repositories?.length || 0})
        </span>
      ),
      children: (
        <Table
          dataSource={detail.repositories || []}
          columns={repoColumns}
          rowKey="repo_id"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      ),
    },
    {
      key: 'contributions',
      label: (
        <span>
          <BranchesOutlined style={{ marginRight: 6 }} />
          贡献 ({detail.contributions?.length || 0})
        </span>
      ),
      children: (
        <Table
          dataSource={detail.contributions || []}
          columns={contributionColumns}
          rowKey="contribution_id"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      ),
    },
    {
      key: 'languages',
      label: (
        <span>
          <CodeOutlined style={{ marginRight: 6 }} />
          语言技能 ({detail.language_skills?.length || 0})
        </span>
      ),
      children: (
        <Table
          dataSource={detail.language_skills || []}
          columns={languageColumns}
          rowKey="skill_id"
          pagination={false}
          size="small"
        />
      ),
    },
    {
      key: 'similar',
      label: (
        <span>
          <UserOutlined style={{ marginRight: 6 }} />
          相似推荐
        </span>
      ),
      children: (
        <Row gutter={16}>
          {(detail.similar_developers || []).length === 0 ? (
            <Col span={24}><Empty description="暂无相似推荐" /></Col>
          ) : (
            (detail.similar_developers || []).map((dev) => (
              <Col span={8} key={dev.developer_id} style={{ marginBottom: 16 }}>
                <Card
                  hoverable
                  size="small"
                  onClick={() => navigate(`/opensource/developers/${dev.developer_id}`)}
                >
                  <Space>
                    <div style={{ width: 36, height: 36, borderRadius: 18, background: primary, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 14, fontWeight: 600 }}>
                      {(dev.name || dev.github_login)?.[0]?.toUpperCase()}
                    </div>
                    <div>
                      <Text strong style={{ fontSize: 14 }}>{dev.name || dev.github_login}</Text>
                      <div><Text type="secondary" style={{ fontSize: 12 }}>@{dev.github_login}</Text></div>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))
          )}
        </Row>
      ),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* Breadcrumb */}
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/opensource')} style={{ marginBottom: 16 }}>
        返回
      </Button>

      {/* Profile Header */}
      <Card className="domain-card" style={{ marginBottom: 24 }} bodyStyle={{ padding: 32 }}>
        <Row gutter={32} align="middle">
          <Col>
            {detail.avatar_url ? (
              <img src={detail.avatar_url} alt={detail.github_login} style={{ width: 96, height: 96, borderRadius: 48 }} />
            ) : (
              <div style={{ width: 96, height: 96, borderRadius: 48, background: primary, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 36, fontWeight: 600 }}>
                {(detail.name || detail.github_login)?.[0]?.toUpperCase()}
              </div>
            )}
          </Col>
          <Col flex="auto">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <Title level={3} style={{ margin: 0, marginBottom: 4 }}>
                  {detail.name || detail.github_login}
                  <a href={`https://github.com/${detail.github_login}`} target="_blank" rel="noopener noreferrer" style={{ marginLeft: 12, fontSize: 18, color: 'var(--text-tertiary)' }}>
                    <GithubOutlined />
                  </a>
                </Title>
                <Text type="secondary" style={{ fontSize: 15 }}>@{detail.github_login}</Text>
                {detail.bio && (
                  <Paragraph style={{ marginTop: 8, marginBottom: 0, maxWidth: 600 }}>
                    {detail.bio}
                  </Paragraph>
                )}
                <Space style={{ marginTop: 12 }}>
                  {detail.location && <Tag icon={<GlobalOutlined />}>{detail.location}</Tag>}
                  {detail.company && <Tag icon={<BranchesOutlined />}>{detail.company}</Tag>}
                  {detail.blog_url && (
                    <Tag icon={<GlobalOutlined />}>
                      <a href={detail.blog_url} target="_blank" rel="noopener noreferrer">Blog</a>
                    </Tag>
                  )}
                  {detail.email && <Tag icon={<MailOutlined />}>{detail.email}</Tag>}
                </Space>
              </div>
              <Space>
                <Button
                  type={isFavorite ? 'primary' : 'default'}
                  icon={isFavorite ? <HeartFilled /> : <HeartOutlined />}
                  onClick={handleToggleFavorite}
                  style={isFavorite ? { background: '#F56565', borderColor: '#F56565' } : {}}
                >
                  {isFavorite ? '已收藏' : '收藏'}
                </Button>
              </Space>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[
          { title: 'Total Stars', value: detail.total_stars_received, icon: <StarOutlined />, color: '#F6AD55' },
          { title: 'Total Forks', value: detail.total_forks_received, icon: <ForkOutlined />, color: '#38A169' },
          { title: 'Public Repos', value: detail.public_repos_count, icon: <GithubOutlined />, color: primary },
          { title: 'Followers', value: detail.followers_count, icon: <UserOutlined />, color: '#3182CE' },
        ].map((s) => (
          <Col span={6} key={s.title}>
            <Card className="domain-card" size="small" bodyStyle={{ padding: '16px 20px' }}>
              <Statistic
                title={<Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{s.title}</Text>}
                value={s.value}
                prefix={<span style={{ color: s.color }}>{s.icon}</span>}
                valueStyle={{ color: s.color, fontSize: 24, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Language Tags */}
      <Card className="domain-card" style={{ marginBottom: 24 }} size="small" bodyStyle={{ padding: 16 }}>
        <Text strong style={{ marginRight: 12 }}>技术栈:</Text>
        <Space wrap>
          {(detail.primary_languages || []).map((lang) => (
            <Tag key={lang} color="blue">{lang}</Tag>
          ))}
          {(detail.tech_tags || []).map((tag) => (
            <Tag key={tag} color="green">{tag}</Tag>
          ))}
        </Space>
      </Card>

      {/* Tabs */}
      <Card className="domain-card">
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  )
}

export default DeveloperDetailPage
