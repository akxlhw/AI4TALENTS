import { Tag, Statistic, Avatar, Badge, Timeline } from 'antd'
import {
  BuildOutlined,
  RocketOutlined,
  ApartmentOutlined,
  TeamOutlined,
  ProjectOutlined,
  LockOutlined,
  RiseOutlined,
  StarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { DemoPlaceholderPage } from '../../components/DemoPlaceholderPage'

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
    projects: ['城市NGP', '端到端大模型', '多模态感知'],
    skills: ['自动驾驶', '计算机视觉', '强化学习'],
    influence: 92,
    availability: 'open',
  },
]

export default function IndustryDemoPage() {
  return (
    <DemoPlaceholderPage
      title="行业人才库"
      description="汇聚各行业的顶尖技术人才，涵盖互联网、芯片、自动驾驶、金融科技等热门领域"
      icon={<BuildOutlined />}
      features={[
        '行业人才搜索与筛选',
        '企业技术影响力评估',
        '项目经验与技能匹配',
        '人才流动趋势分析',
        '企业技术竞争力对比',
      ]}
    >
      <div style={{ marginTop: 24 }}>
        {mockExperts.map((expert) => (
          <div
            key={expert.id}
            style={{
              background: '#fff',
              borderRadius: 8,
              padding: 20,
              marginBottom: 16,
              border: '1px solid #f0f0f0',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', gap: 16 }}>
                <Avatar size={64} style={{ background: '#1890ff' }}>
                  {expert.name[0]}
                </Avatar>
                <div>
                  <h3 style={{ margin: 0 }}>{expert.name}</h3>
                  <p style={{ margin: '4px 0', color: '#666' }}>
                    {expert.title} · {expert.company}
                  </p>
                  <Tag color="blue">{expert.industry}</Tag>
                  {expert.availability === 'open' ? (
                    <Badge status="success" text="开放机会" />
                  ) : (
                    <Badge status="error" text="暂不看机会" />
                  )}
                </div>
              </div>
              <Statistic title="影响力指数" value={expert.influence} suffix="/100" />
            </div>
            <div style={{ marginTop: 16 }}>
              <p style={{ color: '#666', marginBottom: 8 }}>
                <TeamOutlined /> 团队规模: {expert.teamSize}人 ·
                <ClockCircleOutlined /> 经验: {expert.experience}年
              </p>
              <div style={{ marginBottom: 8 }}>
                {expert.skills.map((skill) => (
                  <Tag key={skill} style={{ marginRight: 8 }}>
                    {skill}
                  </Tag>
                ))}
              </div>
              <Timeline
                items={expert.projects.map((project) => ({
                  dot: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
                  children: project,
                }))}
              />
            </div>
          </div>
        ))}
      </div>
    </DemoPlaceholderPage>
  )
}
