import { Card, Row, Col, Tag, Space, Typography, Button, Statistic, Avatar, Badge, Progress } from 'antd'
import {
  TrophyOutlined,
  FireOutlined,
  ThunderboltOutlined,
  CrownOutlined,
  GlobalOutlined,
  ArrowLeftOutlined,
  LockOutlined,
  RiseOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

// Mock data for demo
const mockCompetitors = [
  {
    id: 1,
    name: '陈竞赛',
    school: '清华大学',
    medals: { gold: 3, silver: 1, bronze: 0 },
    rating: 2847,
    rank: '#12',
    globalPercentile: 'Top 0.01%',
    contests: 42,
    streak: 8,
    specialties: ['算法', '数据结构', '图论'],
    recentTrend: 'up',
  },
  {
    id: 2,
    name: '林选手',
    school: '北京大学',
    medals: { gold: 2, silver: 2, bronze: 1 },
    rating: 2712,
    rank: '#28',
    globalPercentile: 'Top 0.05%',
    contests: 38,
    streak: 5,
    specialties: ['动态规划', '字符串', '数论'],
    recentTrend: 'stable',
  },
  {
    id: 3,
    name: '赵算法',
    school: '上海交通大学',
    medals: { gold: 1, silver: 3, bronze: 2 },
    rating: 2589,
    rank: '#51',
    globalPercentile: 'Top 0.1%',
    contests: 35,
    streak: 3,
    specialties: ['几何', '组合数学', '博弈论'],
    recentTrend: 'up',
  },
]

const mockLeaderboard = [
  { rank: 1, name: 'Tourist', school: 'MIPT', country: '🇷🇺', rating: 3948, trend: '+23' },
  { rank: 2, name: 'Benq', school: 'MIT', country: '🇺🇸', rating: 3812, trend: '+12' },
  { rank: 3, name: 'Jiangly', school: 'ZJU', country: '🇨🇳', rating: 3756, trend: '+45' },
]

const CompetitionDemoPage: React.FC = () => {
  const navigate = useNavigate()
  const primary = '#1A202C'
  const secondary = '#F6AD55'
  const accent = '#DD6B20'

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1A202C 0%, #DD6B20 100%)',
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
            opacity: 0.08,
            backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.2) 10px, rgba(255,255,255,0.2) 20px)`,
          }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <Space size={12} style={{ marginBottom: 12 }}>
            <TrophyOutlined style={{ fontSize: 28 }} />
            <Badge
              count="即将上线"
              style={{ background: 'rgba(255,255,255,0.25)', color: '#fff', fontWeight: 600 }}
            />
          </Space>
          <Title level={2} style={{ margin: 0, marginBottom: 8, color: '#fff' }}>
            竞赛人才
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 15, maxWidth: 600 }}>
            覆盖 ACM-ICPC、CTF、Kaggle、数学建模等全球顶级赛事 · 发现顶尖竞赛选手
          </Paragraph>
        </div>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[
          { title: '收录选手', value: 56000, icon: <CrownOutlined />, color: accent },
          { title: '覆盖赛事', value: 120, icon: <TrophyOutlined />, color: secondary },
          { title: '金牌选手', value: 2300, icon: <TrophyOutlined />, color: '#F6AD55' },
          { title: '国家/地区', value: 85, icon: <GlobalOutlined />, color: '#ED8936' },
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

      {/* Competitor Cards */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <ThunderboltOutlined style={{ marginRight: 8, color: accent }} />
        顶尖选手预览
      </Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {mockCompetitors.map((c) => (
          <Col span={8} key={c.id}>
            <Card
              className="domain-card"
              style={{
                borderRadius: 12,
                borderTop: `3px solid ${c.medals.gold > 0 ? '#F6AD55' : '#A0AEC0'}`,
              }}
              bodyStyle={{ padding: 20 }}
            >
              <Space align="start" style={{ marginBottom: 14 }}>
                <Avatar
                  size={48}
                  style={{
                    background:
                      c.medals.gold >= 3
                        ? 'linear-gradient(135deg, #F6AD55, #DD6B20)'
                        : primary,
                    fontSize: 20,
                    fontWeight: 600,
                  }}
                >
                  {c.name[0]}
                </Avatar>
                <div style={{ flex: 1 }}>
                  <Space>
                    <Text strong style={{ fontSize: 16 }}>
                      {c.name}
                    </Text>
                    <Badge
                      count={c.globalPercentile}
                      style={{ background: accent, fontSize: 10 }}
                    />
                  </Space>
                  <Text type="secondary" style={{ fontSize: 13, display: 'block' }}>
                    {c.school}
                  </Text>
                </div>
              </Space>

              {/* Medals */}
              <Space size={16} style={{ marginBottom: 14 }}>
                <Space size={4}>
                  <CrownOutlined style={{ color: '#F6AD55' }} />
                  <Text strong style={{ color: '#F6AD55' }}>
                    {c.medals.gold}
                  </Text>
                </Space>
                <Space size={4}>
                  <TrophyOutlined style={{ color: '#A0AEC0' }} />
                  <Text strong style={{ color: '#A0AEC0' }}>
                    {c.medals.silver}
                  </Text>
                </Space>
                <Space size={4}>
                  <FireOutlined style={{ color: '#DD6B20' }} />
                  <Text strong style={{ color: '#DD6B20' }}>
                    {c.medals.bronze}
                  </Text>
                </Space>
              </Space>

              {/* Rating bar */}
              <div style={{ marginBottom: 14 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 4,
                  }}
                >
                  <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    竞赛积分
                  </Text>
                  <Text strong style={{ color: accent, fontSize: 16 }}>
                    {c.rating}
                  </Text>
                </div>
                <Progress
                  percent={(c.rating / 4000) * 100}
                  showInfo={false}
                  strokeColor={{
                    '0%': secondary,
                    '100%': accent,
                  }}
                  trailColor="#EDF2F7"
                  size="small"
                />
              </div>

              <Space size={4} wrap>
                {c.specialties.map((s) => (
                  <Tag
                    key={s}
                    style={{ fontSize: 11, borderRadius: 4, background: '#FFFAF0', color: accent, borderColor: '#FEEBCB' }}
                  >
                    {s}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Global Leaderboard Preview */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <RiseOutlined style={{ marginRight: 8, color: accent }} />
        全球排名榜预览
      </Title>
      <Card className="domain-card" style={{ borderRadius: 12, marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={0}>
          {mockLeaderboard.map((entry) => (
            <div
              key={entry.rank}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '14px 16px',
                borderRadius: 10,
                gap: 16,
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  background:
                    entry.rank === 1
                      ? 'linear-gradient(135deg, #F6AD55, #DD6B20)'
                      : entry.rank === 2
                        ? '#A0AEC0'
                        : '#D69E2E',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: 14,
                }}
              >
                {entry.rank}
              </div>
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 15 }}>
                  {entry.name}
                </Text>
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                  {entry.school}
                </Text>
              </div>
              <Text style={{ fontSize: 16 }}>{entry.country}</Text>
              <Text strong style={{ fontSize: 16, color: accent, minWidth: 60, textAlign: 'right' }}>
                {entry.rating}
              </Text>
              <Tag color="success" style={{ fontSize: 11 }}>
                {entry.trend}
              </Tag>
            </div>
          ))}
        </Space>
      </Card>

      {/* CTA */}
      <div
        style={{
          textAlign: 'center',
          marginTop: 40,
          padding: '32px',
          background: '#FFFAF0',
          borderRadius: 12,
        }}
      >
        <LockOutlined style={{ fontSize: 24, color: accent, marginBottom: 12 }} />
        <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
          竞赛人才系统即将上线
        </Title>
        <Paragraph type="secondary" style={{ maxWidth: 480, margin: '0 auto 20px' }}>
          覆盖 ACM-ICPC、CTF、Kaggle、数学建模等赛事数据，提供选手排名、能力画像、组队推荐等功能
        </Paragraph>
        <Button
          type="primary"
          size="large"
          style={{ background: primary, borderColor: primary }}
          onClick={() => navigate('/')}
        >
          <ArrowLeftOutlined /> 返回学术人才库
        </Button>
      </div>
    </div>
  )
}

export default CompetitionDemoPage
