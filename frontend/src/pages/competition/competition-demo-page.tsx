import { Tag, Statistic, Avatar, Badge, Progress } from 'antd'
import {
  TrophyOutlined,
  FireOutlined,
  ThunderboltOutlined,
  CrownOutlined,
  GlobalOutlined,
  LockOutlined,
  RiseOutlined,
} from '@ant-design/icons'
import { DemoPlaceholderPage } from '../../components/DemoPlaceholderPage'

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

export default function CompetitionDemoPage() {
  return (
    <DemoPlaceholderPage
      title="竞赛人才库"
      description="汇聚 ICPC、数学建模、信息学奥赛等顶尖竞赛的获奖选手"
      icon={<TrophyOutlined />}
      features={[
        '竞赛成绩搜索与排名',
        '多维度能力评估',
        '竞赛经历与项目匹配',
        '选手发展趋势分析',
        '院校竞赛实力对比',
      ]}
    >
      <div style={{ marginTop: 24 }}>
        {mockCompetitors.map((c) => (
          <div
            key={c.id}
            style={{
              background: '#fff',
              borderRadius: 8,
              padding: 20,
              marginBottom: 16,
              border: '1px solid #f0f0f0',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <Avatar size={56} style={{ background: '#722ed1' }}>
                  {c.name[0]}
                </Avatar>
                <div>
                  <h3 style={{ margin: 0 }}>{c.name}</h3>
                  <p style={{ margin: '4px 0', color: '#666' }}>
                    <GlobalOutlined /> {c.school}
                  </p>
                  <Tag color="gold">{c.rank}</Tag>
                  <Tag color="purple">{c.globalPercentile}</Tag>
                </div>
              </div>
              <Statistic
                title="Rating"
                value={c.rating}
                prefix={<FireOutlined />}
              />
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
                <Badge count={c.medals.gold} style={{ backgroundColor: '#ffd700', color: '#000' }}>
                  <TrophyOutlined style={{ fontSize: 24, color: '#ffd700' }} />
                </Badge>
                <Badge count={c.medals.silver} style={{ backgroundColor: '#c0c0c0', color: '#000' }}>
                  <TrophyOutlined style={{ fontSize: 24, color: '#c0c0c0' }} />
                </Badge>
                <Badge count={c.medals.bronze} style={{ backgroundColor: '#cd7f32', color: '#fff' }}>
                  <TrophyOutlined style={{ fontSize: 24, color: '#cd7f32' }} />
                </Badge>
              </div>
              <Progress
                percent={Math.min((c.rating / 3000) * 100, 100)}
                status="active"
                strokeColor={{ from: '#108ee9', to: '#87d068' }}
              />
              <div style={{ marginTop: 8 }}>
                {c.specialties.map((s) => (
                  <Tag key={s} style={{ marginRight: 8 }}>{s}</Tag>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </DemoPlaceholderPage>
  )
}
