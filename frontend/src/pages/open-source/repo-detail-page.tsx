import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { navigateBack } from '../../utils/navigation'
import { logger } from '../../utils/logger'
import '@/i18n/namespaces/open-source'
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
  Descriptions,
  Tooltip,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  GithubOutlined,
  StarOutlined,
  ForkOutlined,
  TeamOutlined,
  CodeOutlined,
  CrownOutlined,
  SafetyCertificateOutlined,
  TrophyOutlined,
  MedicineBoxOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import { domainThemes, semanticColors } from '../../theme'
import { getTechElementColor, useTechElements } from '@/constants/tech-elements'
import type { OSRepositoryDetail, OSRepositoryContributor } from '../../types'

const { Title, Text, Paragraph, Link } = Typography

const RepoDetailPage: React.FC = () => {
  const { t } = useTranslation('openSource')
  const { fullLabel } = useTechElements()
  const navigate = useNavigate()
  const { owner, name } = useParams<{ owner: string; name: string }>()

  const [detail, setDetail] = useState<OSRepositoryDetail | null>(null)
  const [contributors, setContributors] = useState<OSRepositoryContributor[]>([])
  const [contributorTotal, setContributorTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [contribLoading, setContribLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('team')
  const [contribPage, setContribPage] = useState(1)
  const [contribPageSize] = useState(20)

  useEffect(() => {
    const fetchDetail = async () => {
      if (!owner || !name) return
      try {
        setLoading(true)
        const res = await api.openSource.getRepository(owner, name)
        setDetail(res.data)
      } catch (e) {
        logger.error('Failed to load repository detail', e)
        message.error(getErrorMessage(e, t('errors.loadRepoFailed')))
      } finally {
        setLoading(false)
      }
    }
    fetchDetail()
  }, [owner, name, t])

  useEffect(() => {
    const fetchContributors = async () => {
      if (!owner || !name) return
      try {
        setContribLoading(true)
        const res = await api.openSource.getRepositoryContributors(owner, name, {
          page: contribPage,
          page_size: contribPageSize,
        })
        setContributors(res.data.items || [])
        setContributorTotal(res.data.total || 0)
      } catch (e) {
        logger.error('Failed to load contributors', e)
        message.error(getErrorMessage(e, t('errors.loadContributorsFailed')))
      } finally {
        setContribLoading(false)
      }
    }
    fetchContributors()
  }, [owner, name, contribPage, contribPageSize, t])

  const primary = domainThemes.opensource.primary
  const secondary = domainThemes.opensource.secondary

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
        <Empty description={t('repo.detail.notFound')} />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => navigate('/opensource')} icon={<ArrowLeftOutlined />}>
            {t('repo.detail.backToHome')}
          </Button>
        </div>
      </div>
    )
  }

  const techCodes: string[] = detail.tech_element ?? []
  const techInfos = techCodes.map(code => ({
    code,
    label: fullLabel(code),
    color: getTechElementColor(code),
  }))
  const ownerOrCommitters = contributors.filter((c) => c.is_owner || c.is_committer)
  const displayName = detail.display_name || detail.full_name.split('/')[1] || detail.full_name

  const renderRoleTag = (roles: string[]) => {
    return roles.map((role) => {
      if (role === 'Owner') {
        return (
          <Tag key={role} icon={<CrownOutlined />} color={semanticColors.gold} style={{ fontSize: 11, marginRight: 4 }}>
            Owner
          </Tag>
        )
      }
      if (role === 'Committer') {
        return (
          <Tag key={role} icon={<SafetyCertificateOutlined />} color={semanticColors.blue} style={{ fontSize: 11, marginRight: 4 }}>
            Committer
          </Tag>
        )
      }
      return (
        <Tag key={role} style={{ fontSize: 11, marginRight: 4 }}>
          {role}
        </Tag>
      )
    })
  }

  const teamCards = (
    <Row gutter={[16, 16]}>
      {ownerOrCommitters.length === 0 ? (
        <Col span={24}>
          <Empty description={t('repo.detail.noTeam')} />
        </Col>
      ) : (
        ownerOrCommitters.map((c) => (
          <Col xs={24} sm={12} lg={8} key={c.developer_id}>
            <Card
              hoverable
              className="domain-card"
              style={{ borderLeft: `3px solid ${semanticColors.osGreenLight}` }}
              styles={{ body: { padding: '14px 16px' } }}
              onClick={() => navigate(`/opensource/developers/${c.developer_id}`)}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                {c.avatar_url ? (
                  <img
                    src={`${c.avatar_url}${c.avatar_url.includes('?') ? '&' : '?'}s=64`}
                    alt={c.name || c.github_login}
                    loading="lazy"
                    style={{ width: 44, height: 44, borderRadius: 22, objectFit: 'cover', flexShrink: 0 }}
                  />
                ) : (
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 22,
                      background: primary,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                      fontSize: 16,
                      fontWeight: 600,
                      flexShrink: 0,
                    }}
                  >
                    {(c.name || c.github_login)?.[0]?.toUpperCase()}
                  </div>
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <Text strong style={{ fontSize: 14 }}>{c.name || c.github_login}</Text>
                    {renderRoleTag(c.roles)}
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>@{c.github_login}</Text>
                  <div style={{ marginTop: 6, display: 'flex', gap: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <CodeOutlined style={{ marginRight: 4 }} />
                      {c.commits_count} commits
                    </Text>
                    {c.company && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {c.company}
                      </Text>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        ))
      )}
    </Row>
  )

  const rankMedal = (index: number) => {
    if (index === 0) return <TrophyOutlined style={{ color: semanticColors.gold, fontSize: 16 }} />
    if (index === 1) return <MedicineBoxOutlined style={{ color: semanticColors.borderGray, fontSize: 16 }} />
    if (index === 2) return <MedicineBoxOutlined style={{ color: semanticColors.orange, fontSize: 16 }} />
    return <Text type="secondary" style={{ fontSize: 12 }}>{index + 1}</Text>
  }

  const contributorColumns = [
    {
      title: t('repo.detail.columns.rank'),
      width: 60,
      render: (_: unknown, __: unknown, index: number) => rankMedal(index),
    },
    {
      title: t('repo.detail.columns.developer'),
      render: (_: unknown, record: OSRepositoryContributor) => (
        <Space>
          {record.avatar_url ? (
            <img
              src={`${record.avatar_url}${record.avatar_url.includes('?') ? '&' : '?'}s=32`}
              alt={record.name || record.github_login}
              style={{ width: 24, height: 24, borderRadius: 12, objectFit: 'cover' }}
            />
          ) : (
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: 12,
                background: primary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: 10,
              }}
            >
              {(record.name || record.github_login)?.[0]?.toUpperCase()}
            </div>
          )}
          <span>{record.name || record.github_login}</span>
        </Space>
      ),
    },
    {
      title: t('repo.detail.columns.role'),
      render: (_: unknown, record: OSRepositoryContributor) => renderRoleTag(record.roles),
    },
    {
      title: 'Commits',
      dataIndex: 'commits_count',
      sorter: (a: OSRepositoryContributor, b: OSRepositoryContributor) => a.commits_count - b.commits_count,
    },
    {
      title: 'PRs',
      dataIndex: 'prs_count',
    },
    {
      title: 'Issues',
      dataIndex: 'issues_count',
    },
    {
      title: t('repo.detail.columns.company'),
      dataIndex: 'company',
      render: (v: string | null) => v || '-',
    },
  ]

  const contributorTable = (
    <Table
      dataSource={contributors}
      columns={contributorColumns}
      rowKey="developer_id"
      loading={contribLoading}
      pagination={{
        current: contribPage,
        pageSize: contribPageSize,
        total: contributorTotal,
        showSizeChanger: false,
        showTotal: count => t('repo.detail.contributorTotal', { n: count }),
        onChange: (p) => setContribPage(p),
      }}
      onRow={(record) => ({
        onClick: () => navigate(`/opensource/developers/${record.developer_id}`),
        style: { cursor: 'pointer' },
      })}
    />
  )

  const projectInfo = (
    <Card className="domain-card" style={{ borderLeft: `3px solid ${semanticColors.osGreenLight}` }}>
      <Descriptions column={1} labelStyle={{ fontWeight: 600, width: 120 }}>
        <Descriptions.Item label={t('repo.detail.info.fullName')}>
          {detail.full_name}
        </Descriptions.Item>
        <Descriptions.Item label={t('repo.detail.info.techElements')}>
          <Space size={4} wrap>
            {techInfos.length ? (
              techInfos.map(t => (
                <Tag key={t.code} color={t.color}>
                  {t.label}
                </Tag>
              ))
            ) : (
              <span>-</span>
            )}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label={t('repo.detail.info.mainLanguage')}>
          {detail.language ? <Tag>{detail.language}</Tag> : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="Topics">
          {detail.topics?.length ? (
            <Space wrap>
              {detail.topics.map((t) => (
                <Tag key={t} style={{ fontSize: 12 }}>{t}</Tag>
              ))}
            </Space>
          ) : (
            '-'
          )}
        </Descriptions.Item>
        <Descriptions.Item label="GitHub">
          <Link href={`https://github.com/${detail.full_name}`} target="_blank">
            <GithubOutlined style={{ marginRight: 4 }} />
            {t('repo.detail.viewRepo')}
          </Link>
        </Descriptions.Item>
      </Descriptions>
    </Card>
  )

  return (
    <div style={{ padding: '88px 32px 80px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Back button */}
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigateBack(navigate, '/opensource/repos')}
        style={{ marginBottom: 16 }}
      >
        {t('repo.detail.back')}
      </Button>

      {/* Header Card */}
      <Card className="domain-card" style={{ borderLeft: `3px solid ${semanticColors.osGreenLight}`, marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col>
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: 16,
                background: secondary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: 28,
                fontWeight: 700,
              }}
            >
              {displayName[0]?.toUpperCase()}
            </div>
          </Col>
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Space align="center">
                  <Title level={3} style={{ margin: 0 }}>{displayName}</Title>
                  {techInfos.map(t => (
                    <Tag key={t.code} color={t.color}>
                      {t.label}
                    </Tag>
                  ))}
                </Space>
              </div>
              <Text type="secondary" style={{ fontSize: 14 }}>{detail.full_name}</Text>
              {detail.description && (
                <Paragraph type="secondary" style={{ margin: '4px 0 0', maxWidth: 800 }}>
                  {detail.description}
                </Paragraph>
              )}
              <div style={{ marginTop: 4 }}>
                {detail.language && <Tag style={{ marginRight: 8 }}>{detail.language}</Tag>}
                {detail.topics?.slice(0, 6).map((t) => (
                  <Tooltip key={t} title={t}>
                    <Tag style={{ marginRight: 4, fontSize: 11 }}>{t.length > 16 ? t.slice(0, 16) + '...' : t}</Tag>
                  </Tooltip>
                ))}
                {detail.topics && detail.topics.length > 6 && (
                  <Tag style={{ fontSize: 11 }}>+{detail.topics.length - 6}</Tag>
                )}
              </div>
              <div style={{ marginTop: 4 }}>
                <Link href={`https://github.com/${detail.full_name}`} target="_blank" style={{ fontSize: 13 }}>
                  <GithubOutlined style={{ marginRight: 4 }} />
                  {t('repo.detail.viewOnGithub')}
                </Link>
              </div>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Stats Row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="domain-card">
            <Statistic
              title="Stars"
              value={detail.stars_count}
              prefix={<StarOutlined style={{ color: semanticColors.gold }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="domain-card">
            <Statistic
              title="Forks"
              value={detail.forks_count}
              prefix={<ForkOutlined style={{ color: semanticColors.purple }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="domain-card">
            <Statistic
              title={t('repo.detail.stats.contributors')}
              value={detail.contributor_count}
              prefix={<TeamOutlined style={{ color: semanticColors.cyan }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="domain-card">
            <Statistic
              title={t('repo.detail.stats.mainLanguage')}
              value={detail.language || 'Unknown'}
              prefix={<CodeOutlined style={{ color: semanticColors.blue }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card className="domain-card">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'team',
              label: t('repo.detail.tabs.team'),
              children: teamCards,
            },
            {
              key: 'contributors',
              label: t('repo.detail.tabs.contributors', { n: contributorTotal }),
              children: contributorTable,
            },
            {
              key: 'info',
              label: t('repo.detail.tabs.info'),
              children: projectInfo,
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default RepoDetailPage
