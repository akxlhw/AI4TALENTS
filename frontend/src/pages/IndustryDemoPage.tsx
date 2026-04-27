import { Card, Row, Col, Tag, Space, Typography, Button, Statistic, Avatar, Badge, Timeline } from 'antd'
import {
  BuildOutlined,
  RocketOutlined,
  ApartmentOutlined,
  TeamOutlined,
  ProjectOutlined,
  ArrowLeftOutlined,
  LockOutlined,
  RiseOutlined,
  StarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

// Mock data for demo
const mockExperts = [
  {
    id: 1,
    name: '刘专家',
    title: '技术总监',
    company: '字节跳动',
    industry: '互联网 / 大模型',
    experience: 15,
    teamSize: 80,
    projects: ['推荐系统3.0', '火山引擎ML平台', '豆包大模型'],
    skills: ['大模型', '推荐系统', '分布式架构'],
    influence: 98,
    availability: 'open',
  },
  {
    id: 2,
    name: '周架构',
    title: '首席架构师',
    company: '华为',
    industry: '芯片 / 云计算',
    experience: 18,
    teamSize: 120,
    projects: ['昇腾AI芯片', '鸿蒙内核', '云原生平台'],
    skills: ['芯片设计', '操作系统', '云原生'],
    influence: 95,
    availability: 'busy',
  },
  {
    id: 3,
    name: '吴研究员',
    title: '自动驾驶负责人',
    company: '小鹏汽车',
    industry: '自动驾驶 / AI',
    experience: 12,
    teamSize: 60,
    projects: ['XNGP城市导航', '感知算法平台', '端到端大模型'],
    skills: ['自动驾驶', '计算机视觉', 'ROS'],
    influence: 92,
    availability: 'open',
  },
]

const mockIndustries = [
  { name: '大模型 / AIGC', count: 12500, growth: '+45%', color: '#805AD5' },
  { name: '芯片 / 半导体', count: 8200, growth: '+32%', color: '#6B46C1' },
  { name: '自动驾驶', count: 5600, growth: '+28%', color: '#553C9A' },
  { name: '云原生 / 基础设施', count: 9800, growth: '+18%', color: '#44337A' },
]

const IndustryDemoPage: React.FC = () => {
  const navigate = useNavigate()
  const primary = '#1A365D'
  const secondary = '#805AD5'
  const accent = '#6B46C1'

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      {/* Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1A365D 0%, #6B46C1 100%)',
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
            backgroundImage: `radial-gradient(circle at 30% 70%, rgba(128,90,213,0.4) 0%, transparent 50%),
                               radial-gradient(circle at 70% 30%, rgba(107,70,193,0.3) 0%, transparent 50%)`,
          }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <Space size={12} style={{ marginBottom: 12 }}>
            <BuildOutlined style={{ fontSize: 28 }} />
            <Badge
              count="即将上线"
              style={{ background: 'rgba(255,255,255,0.25)', color: '#fff', fontWeight: 600 }}
            />
          </Space>
          <Title level={2} style={{ margin: 0, marginBottom: 8, color: '#fff' }}>
            行业专家
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 15, maxWidth: 600 }}>
            覆盖互联网、芯片、自动驾驶等核心产业 · 连接行业技术领袖与产业需求
          </Paragraph>
        </div>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {[
          { title: '收录专家', value: 45000, icon: <TeamOutlined />, color: primary },
          { title: '覆盖企业', value: 3200, icon: <ApartmentOutlined />, color: accent },
          { title: '热门岗位', value: 280, icon: <RocketOutlined />, color: secondary },
          { title: '技术方向', value: 65, icon: <ProjectOutlined />, color: '#553C9A' },
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

      {/* Industry Distribution */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <RiseOutlined style={{ marginRight: 8, color: secondary }} />
        热门产业方向
      </Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {mockIndustries.map((ind) => (
          <Col span={6} key={ind.name}>
            <Card
              className="domain-card"
              style={{ borderRadius: 12, borderLeft: `4px solid ${ind.color}` }}
              bodyStyle={{ padding: '18px 20px' }}
            >
              <Text strong style={{ fontSize: 15, display: 'block', marginBottom: 4 }}>
                {ind.name}
              </Text>
              <Space style={{ marginBottom: 8 }}>
                <Text style={{ fontSize: 22, fontWeight: 700, color: ind.color }}>
                  {ind.count.toLocaleString()}
                </Text>
                <Text style={{ fontSize: 12, color: '#48BB78', fontWeight: 500 }}>
                  {ind.growth}
                </Text>
              </Space>
              <div
                style={{
                  height: 4,
                  borderRadius: 2,
                  background: '#EDF2F7',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min((ind.count / 15000) * 100, 100)}%`,
                    height: '100%',
                    background: ind.color,
                    borderRadius: 2,
                  }}
                />
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Expert Cards */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <StarOutlined style={{ marginRight: 8, color: accent }} />
        顶尖专家预览
      </Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {mockExperts.map((exp) => (
          <Col span={8} key={exp.id}>
            <Card
              className="domain-card"
              style={{
                borderRadius: 12,
                borderTop: `3px solid ${exp.availability === 'open' ? secondary : '#A0AEC0'}`,
              }}
              bodyStyle={{ padding: 20 }}
            >
              <Space align="start" style={{ marginBottom: 14 }}>
                <Avatar
                  size={48}
                  style={{
                    background: `linear-gradient(135deg, ${primary}, ${accent})`,
                    fontSize: 20,
                    fontWeight: 600,
                  }}
                >
                  {exp.name[0]}
                </Avatar>
                <div style={{ flex: 1 }}>
                  <Space>
                    <Text strong style={{ fontSize: 16 }}>
                      {exp.name}
                    </Text>
                    <Badge
                      count={exp.availability === 'open' ? '可联系' : '忙碌'}
                      style={{
                        background: exp.availability === 'open' ? secondary : '#A0AEC0',
                        fontSize: 10,
                      }}
                    />
                  </Space>
                  <Text type="secondary" style={{ fontSize: 13, display: 'block' }}>
                    {exp.title} · {exp.company}
                  </Text>
                </div>
              </Space>

              <Paragraph style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
                {exp.industry} · {exp.experience}年经验 · 管理{exp.teamSize}人团队
              </Paragraph>

              {/* Influence score */}
              <div style={{ marginBottom: 14 }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 4,
                  }}
                >
                  <Text style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    行业影响力
                  </Text>
                  <Text strong style={{ color: accent, fontSize: 14 }}>
                    {exp.influence}/100
                  </Text>
                </div>
                <div
                  style={{
                    height: 6,
                    borderRadius: 3,
                    background: '#EDF2F7',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${exp.influence}%`,
                      height: '100%',
                      background: `linear-gradient(90deg, ${secondary}, ${accent})`,
                      borderRadius: 3,
                    }}
                  />
                </div>
              </div>

              {/* Projects */}
              <div style={{ marginBottom: 14 }}>
                <Text style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'block', marginBottom: 6 }}>
                  主导项目
                </Text>
                <Space size={4} wrap>
                  {exp.projects.map((p) => (
                    <Tag
                      key={p}
                      style={{
                        fontSize: 11,
                        borderRadius: 4,
                        background: '#FAF5FF',
                        color: accent,
                        borderColor: '#E9D8FD',
                      }}
                    >
                      {p}
                    </Tag>
                  ))}
                </Space>
              </div>

              <Space size={4} wrap>
                {exp.skills.map((s) => (
                  <Tag key={s} style={{ fontSize: 11, borderRadius: 4 }}>
                    {s}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Career Timeline Preview */}
      <Title level={4} style={{ marginBottom: 16 }}>
        <ClockCircleOutlined style={{ marginRight: 8, color: accent }} />
        职业轨迹预览
      </Title>
      <Card className="domain-card" style={{ borderRadius: 12, marginBottom: 24 }} bodyStyle={{ padding: 24 }}>
        <Timeline
          items={[
            {
              dot: <CheckCircleOutlined style={{ color: secondary }} />,
              children: (
                <div>
                  <Text strong>2024 — 技术总监</Text>
                  <div>
                    <Text type="secondary">字节跳动 · 大模型研发团队</Text>
                  </div>
                </div>
              ),
            },
            {
              dot: <CheckCircleOutlined style={{ color: accent }} />,
              children: (
                <div>
                  <Text strong>2021 — 高级技术专家</Text>
                  <div>
                    <Text type="secondary">阿里巴巴 · 达摩院</Text>
                  </div>
                </div>
              ),
            },
            {
              dot: <CheckCircleOutlined style={{ color: primary }} />,
              children: (
                <div>
                  <Text strong>2018 — 技术负责人</Text>
                  <div>
                    <Text type="secondary">百度 · 深度学习实验室</Text>
                  </div>
                </div>
              ),
            },
            {
              dot: <CheckCircleOutlined style={{ color: 'var(--text-tertiary)' }} />,
              children: (
                <div>
                  <Text strong>2015 — 算法工程师</Text>
                  <div>
                    <Text type="secondary">腾讯 · AI Lab</Text>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* CTA */}
      <div
        style={{
          textAlign: 'center',
          marginTop: 40,
          padding: '32px',
          background: '#FAF5FF',
          borderRadius: 12,
        }}
      >
        <LockOutlined style={{ fontSize: 24, color: accent, marginBottom: 12 }} />
        <Title level={4} style={{ margin: 0, marginBottom: 8 }}>
          行业专家系统即将上线
        </Title>
        <Paragraph type="secondary" style={{ maxWidth: 480, margin: '0 auto 20px' }}>
          基于公开职业数据与企业技术影响力评估，提供专家画像、产业人才地图、技术顾问匹配等功能
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

export default IndustryDemoPage
