import { Card, Row, Col, Tag, Space, Typography, Button, Statistic, Avatar, Badge } from 'antd'
import {
  CodeOutlined,
  GithubOutlined,
  StarOutlined,
  ForkOutlined,
  FireOutlined,
  PullRequestOutlined,
  BranchesOutlined,
  ArrowLeftOutlined,
  RocketOutlined,
  LockOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

// Mock data for demo
const mockDevelopers = [
  {
    id: 1,
    name: '张伟',
    handle: '@zhangwei',
    avatar: 'Z',
    role: 'PyTorch 核心维护者',
    org: 'Meta AI',
    stars: 12500,
    commits: 3200,
    prs: 480,
    issues: 890,
    languages: ['Python', 'C++', 'CUDA'],
    contribGraph: [4, 6, 8, 10, 7, 5, 9, 11, 8, 6, 10, 12, 9, 7, 5],
    activityRank: 'Top 0.1%',
  },
  {
    id: 2,
    name: '李芳',
    handle: '@lifang',
    avatar: 'L',
    role: 'Kubernetes SIG 负责人',
    org: 'Google',
    stars: 8900,
    commits: 2100,
    prs: 320,
    issues: 650,
    languages: ['Go', 'Rust', 'Shell'],
    contribGraph: [3, 5, 7, 9, 6, 8, 10, 7, 5, 9, 11, 8, 6, 10, 7],
    activityRank: 'Top 0.5%',
  },
  {
    id: 3,
    name: '王强',
    handle: '@wangqiang',
    avatar: 'W',
    role: 'Vue.js 核心团队成员',
    org: '独立开发者',
    stars: 15600,
    commits: 1800,
    prs: 260,
    issues: 420,
    languages: ['TypeScript', 'JavaScript', 'Go'],
    contribGraph: [5, 7, 9, 11, 8, 6, 10, 12, 9, 7, 5, 8, 10, 7, 9],
    activityRank: 'Top 0.3%',
  },
]

const mockRepos = [
  { name: 'pytorch/pytorch', stars: '85.2k', forks: '22.1k', lang: 'C++', trend: '+12%' },
  { name: 'kubernetes/kubernetes', stars: '112k', forks: '38.5k', lang: 'Go', trend: '+8%' },
  { name: 'vuejs/core', stars: '48.6k', forks: '8.2k', lang: 'TypeScript', trend: '+15%' },
]

const OpenSourceDemoPage: React.FC = () => {
  const navigate = useNavigate()
  const primary = '#2D3748'
  const secondary = '#48BB78'

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #2D3748 0%, #38A169 100%)',
          padding: '48px 32px',
          color: '#fff',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.06,
            backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.3) 2px, rgba(255,255,255,0.3) 4px)`,
          }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <Space size={12} style={{ marginBottom: 12 }}>
            <CodeOutlined style={{ fontSize: 28 }} />
            <Badge
              count="即将上线"
              style={{ background: 'rgba(255,255,255,0.25)', color: '#fff', fontWeight: 600 }}
            />
          </Space>
          <Title level={2} style={{ margin: 0, marginBottom: 8, color: '#fff' }}>
            开源生态人才
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 15, maxWidth: 600 }}>
            基于 GitHub 贡献图谱的开发者发现平台 · 挖掘全球开源社区技术领袖
          </Paragraph>
        </div>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[
          { title: '收录开发者', value: 128000, icon: <CodeOutlined />, color: primary },
          { title: '覆盖仓库', value: 45000, icon: <GithubOutlined />, color: secondary },
          { title: '活跃组织', value: 3200, icon: <ForkOutlined />, color: '#38A169' },
          { title: '技术栈', value: 120, icon: <BranchesOutlined />, color: '#2F855A' },
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

      {/* Developer Cards */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <RocketOutlined style={{ marginRight: 8, color: secondary }} />
        顶尖开发者预览
      </Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {mockDevelopers.map((dev) => (
          <Col span={8} key={dev.id}>
            <Card
              className="domain-card"
              style={{ borderRadius: 12, borderTop: `3px solid ${secondary}` }}
              bodyStyle={{ padding: 20 }}
            >
              <Space align="start" style={{ marginBottom: 16 }}>
                <Avatar size={48} style={{ background: primary, fontSize: 20, fontWeight: 600 }}>
                  {dev.avatar}
                </Avatar>
                <div>
                  <Text strong style={{ fontSize: 16, display: 'block' }}>
                    {dev.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {dev.handle}
                  </Text>
                </div>
                <Badge
                  count={dev.activityRank}
                  style={{ background: secondary, fontSize: 11 }}
                />
              </Space>

              <Paragraph style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
                {dev.role} · {dev.org}
              </Paragraph>

              <Space size={4} wrap style={{ marginBottom: 16 }}>
                {dev.languages.map((lang) => (
                  <Tag key={lang} style={{ fontSize: 11, borderRadius: 4 }}>
                    {lang}
                  </Tag>
                ))}
              </Space>

              {/* Mini contribution graph */}
              <div style={{ display: 'flex', gap: 3, marginBottom: 16 }}>
                {dev.contribGraph.map((level, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      height: 28,
                      borderRadius: 3,
                      background:
                        level >= 10
                          ? secondary
                          : level >= 7
                            ? `${secondary}BB`
                            : level >= 5
                              ? `${secondary}88`
                              : `${secondary}44`,
                    }}
                  />
                ))}
              </div>

              <Row gutter={16}>
                <Col span={8}>
                  <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Stars</Text>
                  <div style={{ fontWeight: 700, color: primary }}>
                    <StarOutlined style={{ fontSize: 12, marginRight: 4 }} />
                    {(dev.stars / 1000).toFixed(1)}k
                  </div>
                </Col>
                <Col span={8}>
                  <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Commits</Text>
                  <div style={{ fontWeight: 700, color: primary }}>
                    <BranchesOutlined style={{ fontSize: 12, marginRight: 4 }} />
                    {(dev.commits / 1000).toFixed(1)}k
                  </div>
                </Col>
                <Col span={8}>
                  <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>PRs</Text>
                  <div style={{ fontWeight: 700, color: primary }}>
                    <PullRequestOutlined style={{ fontSize: 12, marginRight: 4 }} />
                    {dev.prs}
                  </div>
                </Col>
              </Row>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Trending Repos */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <FireOutlined style={{ marginRight: 8, color: secondary }} />
        Trending 仓库预览
      </Title>
      <Row gutter={16}>
        {mockRepos.map((repo) => (
          <Col span={8} key={repo.name}>
            <Card className="domain-card" style={{ borderRadius: 12 }} bodyStyle={{ padding: 16 }}>
              <Space style={{ marginBottom: 8 }}>
                <GithubOutlined style={{ color: primary }} />
                <Text strong style={{ fontSize: 14, fontFamily: 'monospace' }}>
                  {repo.name}
                </Text>
              </Space>
              <Space size={16}>
                <Text style={{ fontSize: 13 }}>
                  <StarOutlined style={{ color: '#F6AD55', marginRight: 4 }} />
                  {repo.stars}
                </Text>
                <Text style={{ fontSize: 13 }}>
                  <ForkOutlined style={{ color: 'var(--text-tertiary)', marginRight: 4 }} />
                  {repo.forks}
                </Text>
                <Tag color="success" style={{ fontSize: 11, lineHeight: '18px' }}>
                  {repo.trend}
                </Tag>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      {/* CTA */}
      <div style={{ textAlign: 'center', marginTop: 40, padding: '32px', background: '#F0FFF4', borderRadius: 12 }}>
        <LockOutlined style={{ fontSize: 24, color: secondary, marginBottom: 12 }} />
        <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
          开源生态人才系统即将上线
        </Title>
        <Paragraph type="secondary" style={{ maxWidth: 480, margin: '0 auto 20px' }}>
          基于 GitHub GraphQL API 的全栈开发者画像，覆盖代码贡献、社区影响力、技术栈匹配等多维指标
        </Paragraph>
        <Button type="primary" size="large" style={{ background: primary, borderColor: primary }} onClick={() => navigate('/')}>
          <ArrowLeftOutlined /> 返回学术人才库
        </Button>
      </div>
    </div>
  )
}

export default OpenSourceDemoPage
