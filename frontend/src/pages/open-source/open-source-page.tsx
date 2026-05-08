import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Typography,
  Statistic,
  Input,
  Spin,
  Empty,
  Button,
  Tooltip,
} from 'antd'
import {
  CodeOutlined,
  GithubOutlined,
  StarOutlined,
  ForkOutlined,
  FireOutlined,
  BranchesOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { OSStats, OSDeveloper, OSRepoConfig } from '../../types'

const { Title, Text, Paragraph } = Typography
const { Search } = Input

const OpenSourcePage: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState<OSStats | null>(null)
  const [topDevelopers, setTopDevelopers] = useState<OSDeveloper[]>([])
  const [trendingRepos, setTrendingRepos] = useState<OSRepoConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  const primary = '#2D3748'
  const secondary = '#48BB78'

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [statsRes, devRes] = await Promise.all([
          api.openSource.getStats(),
          api.openSource.listDevelopers({ page_size: 6, sort_by: 'stars_desc' }),
        ])
        setStats(statsRes.data)
        setTopDevelopers(devRes.data.items || [])
        // Trending repos from config
        const repoRes = await api.openSource.listRepoConfigs({ page_size: 8, is_active: true, sort_by: 'stars', collected_only: true })
        setTrendingRepos(repoRes.data.items || [])
      } catch (e) {
        console.error('Failed to load open source overview', e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigate(`/opensource/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: '64px 0 80px' }}>
      {/* ═══════════ Hero Section ═══════════ */}
      <div
        style={{
          background: 'var(--domain-gradient)',
          padding: '72px 32px 56px',
          color: '#fff',
          position: 'relative',
          overflow: 'hidden',
          textAlign: 'center',
        }}
      >
        {/* Subtle pattern overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.06,
            backgroundImage: `radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)`,
            backgroundSize: '28px 28px',
          }}
        />
        <div style={{ position: 'relative', zIndex: 1, maxWidth: 880, margin: '0 auto' }}>
          <Title
            level={1}
            style={{
              margin: 0,
              marginBottom: 16,
              color: '#fff',
              fontWeight: 800,
              fontSize: 46,
              letterSpacing: '-0.5px',
            }}
          >
            开源生态人才库
          </Title>
          <Paragraph
            style={{
              margin: 0,
              marginBottom: 40,
              color: 'rgba(255,255,255,0.85)',
              fontSize: 16,
            }}
          >
            基于 GitHub 贡献图谱的开发者发现平台 · 挖掘全球开源社区技术领袖
          </Paragraph>
          <Search
            placeholder="搜索开发者、技术栈、公司..."
            enterButton={
              <span style={{ fontWeight: 500 }}>
                <SearchOutlined /> 搜索
              </span>
            }
            size="large"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            style={{ width: '100%', margin: '0 auto' }}
          />
          {/* Quick tags */}
          <div
            style={{
              marginTop: 20,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 8,
            }}
          >
            {['Python', 'JavaScript', 'Go', 'Rust', 'C++', 'Java'].map((tag) => (
              <Tag
                key={tag}
                onClick={() => navigate(`/opensource/search?q=${encodeURIComponent(tag)}`)}
                style={{
                  cursor: 'pointer',
                  background: 'rgba(255,255,255,0.15)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'rgba(255,255,255,0.9)',
                  borderRadius: 16,
                  padding: '2px 12px',
                  fontSize: 12,
                }}
              >
                {tag}
              </Tag>
            ))}
          </div>
        </div>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginTop: 32, marginBottom: 24, padding: '0 32px' }}>
        {[
          { title: '收录开发者', value: stats?.total_developers || 0, icon: <CodeOutlined />, color: primary, link: '/opensource/search' },
          { title: '覆盖仓库', value: stats?.total_repositories || 0, icon: <GithubOutlined />, color: secondary },
          { title: '活跃组织', value: stats?.total_organizations || 0, icon: <ForkOutlined />, color: '#38A169' },
          { title: '技术栈', value: Object.keys(stats?.language_distribution || {}).length || 0, icon: <BranchesOutlined />, color: '#2F855A' },
        ].map((s) => (
          <Col span={6} key={s.title}>
            <Card
              className="domain-card"
              size="small"
              bodyStyle={{ padding: '16px 20px' }}
              hoverable={!!s.link}
              onClick={s.link ? () => navigate(s.link!) : undefined}
              style={s.link ? { cursor: 'pointer' } : undefined}
            >
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

      {/* ═══════════ Trending Repos + Top Developers (side by side) ═══════════ */}
      <Row gutter={24} style={{ padding: '0 32px' }}>
        {/* ───── Left: Trending Repos ───── */}
        <Col span={12}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Title level={4} style={{ margin: 0 }}>
              <FireOutlined style={{ marginRight: 8, color: '#F6AD55' }} />
              Trending 仓库
            </Title>
          </div>
          {trendingRepos.length === 0 ? (
            <Empty description="暂无仓库数据" />
          ) : (
            <Row gutter={[12, 12]}>
              {trendingRepos.map((repo) => (
                <Col span={24} key={repo.repo_config_id}>
                  <Card
                    className="domain-card"
                    hoverable
                    bodyStyle={{ padding: '14px 16px' }}
                    style={{
                      borderLeft: '3px solid #F6AD55',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      const parts = repo.repo_full_name.split('/')
                      if (parts.length === 2) {
                        navigate(`/opensource/repos/${parts[0]}/${parts[1]}`)
                      }
                    }}
                  >
                    <Space style={{ marginBottom: 6 }}>
                      <GithubOutlined style={{ color: primary, fontSize: 16 }} />
                      <Text strong style={{ fontSize: 14, fontFamily: 'monospace' }}>
                        {repo.repo_full_name}
                      </Text>
                    </Space>
                    <Paragraph
                      ellipsis={{ rows: 1 }}
                      style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}
                    >
                      {repo.description || repo.display_name || '暂无描述'}
                    </Paragraph>
                    <Space size={12}>
                      <Text style={{ fontSize: 12 }}>
                        <StarOutlined style={{ color: '#F6AD55', marginRight: 4 }} />
                        {repo.stars_count || 0}
                      </Text>
                      <Tag
                        color="success"
                        style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}
                      >
                        {repo.tech_element}
                      </Tag>
                      <Tag style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>
                        {repo.language || 'N/A'}
                      </Tag>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Col>

        {/* ───── Right: Top Developers ───── */}
        <Col span={12}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Title level={4} style={{ margin: 0 }}>
              <StarOutlined style={{ marginRight: 8, color: secondary }} />
              顶尖开发者
            </Title>
            <Button
              type="link"
              onClick={() => navigate('/opensource/search')}
              style={{ fontSize: 14, padding: 0 }}
            >
              查看全部 →
            </Button>
          </div>
          {topDevelopers.length === 0 ? (
            <Empty description="暂无开发者数据，请先执行采集任务" />
          ) : (
            <Row gutter={[12, 12]}>
              {topDevelopers.map((dev) => (
                <Col span={24} key={dev.developer_id}>
                  <Card
                    hoverable
                    className="domain-card"
                    style={{
                      borderLeft: `3px solid ${secondary}`,
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                    }}
                    bodyStyle={{ padding: '14px 16px' }}
                    onClick={() => navigate(`/opensource/developers/${dev.developer_id}`)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                      <Space align="start">
                        {dev.avatar_url ? (
                          <img
                            src={`${dev.avatar_url}${dev.avatar_url.includes('?') ? '&' : '?'}s=64`}
                            alt={dev.name || dev.github_login}
                            loading="lazy"
                            style={{
                              width: 40,
                              height: 40,
                              borderRadius: 20,
                              objectFit: 'cover',
                            }}
                          />
                        ) : (
                          <div
                            style={{
                              width: 40,
                              height: 40,
                              borderRadius: 20,
                              background: primary,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: '#fff',
                              fontSize: 16,
                              fontWeight: 600,
                            }}
                          >
                            {(dev.name || dev.github_login)?.[0]?.toUpperCase()}
                          </div>
                        )}
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                            <Text strong style={{ fontSize: 14 }}>
                              {dev.name || dev.github_login}
                            </Text>
                            {dev.roles?.includes('Owner') && (
                              <Tag
                                style={{
                                  fontSize: 10,
                                  lineHeight: '16px',
                                  padding: '0 6px',
                                  borderRadius: 4,
                                  margin: 0,
                                  background: '#D69E2E',
                                  color: '#fff',
                                  border: 'none',
                                  fontWeight: 600,
                                }}
                              >
                                Owner
                              </Tag>
                            )}
                            {dev.roles?.includes('Committer') && (
                              <Tag
                                style={{
                                  fontSize: 10,
                                  lineHeight: '16px',
                                  padding: '0 6px',
                                  borderRadius: 4,
                                  margin: 0,
                                  background: '#3182CE',
                                  color: '#fff',
                                  border: 'none',
                                  fontWeight: 600,
                                }}
                              >
                                Committer
                              </Tag>
                            )}
                          </div>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            @{dev.github_login}
                          </Text>
                        </div>
                      </Space>
                    </div>

                    <Paragraph
                      ellipsis={{ rows: 1 }}
                      style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}
                    >
                      {dev.bio || '暂无简介'}
                    </Paragraph>

                    <Row gutter={16}>
                      <Col span={6}>
                        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Stars</Text>
                        <div style={{ fontWeight: 700, color: primary, fontSize: 13 }}>
                          <StarOutlined style={{ fontSize: 11, marginRight: 2 }} />
                          {(dev.total_stars_received / 1000).toFixed(1)}k
                        </div>
                      </Col>
                      <Col span={6}>
                        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>开发语言</Text>
                        <Tooltip
                          title={
                            <Space size={4} wrap>
                              {(dev.primary_languages || []).map((lang) => (
                                <Tag key={lang} style={{ fontSize: 11, borderRadius: 4, margin: 0 }}>
                                  {lang}
                                </Tag>
                              ))}
                              {(dev.primary_languages || []).length === 0 && '无'}
                            </Space>
                          }
                        >
                          <div
                            style={{
                              fontWeight: 700,
                              color: primary,
                              fontSize: 13,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {(dev.primary_languages || []).slice(0, 2).join(', ') || '-'}
                          </div>
                        </Tooltip>
                      </Col>
                      <Col span={6}>
                        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>公司</Text>
                        <div
                          style={{
                            fontWeight: 700,
                            color: primary,
                            fontSize: 13,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {dev.company || '-'}
                        </div>
                      </Col>
                      <Col span={6}>
                        <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>地区</Text>
                        <div
                          style={{
                            fontWeight: 700,
                            color: primary,
                            fontSize: 13,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {dev.location || '-'}
                        </div>
                      </Col>
                    </Row>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default OpenSourcePage
