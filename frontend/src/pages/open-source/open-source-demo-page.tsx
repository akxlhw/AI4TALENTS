import { Tag, Statistic, Avatar } from 'antd'
import {
  GithubOutlined,
  StarOutlined,
  FireOutlined,
  PullRequestOutlined,
  BranchesOutlined,
} from '@ant-design/icons'
import { DemoPlaceholderPage } from '../../components/DemoPlaceholderPage'
import { useTranslation } from 'react-i18next'

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
    activityRank: 'Top 0.1%',
  },
  {
    id: 2,
    name: '李芳',
    handle: '@lifang',
    avatar: 'L',
    role: 'Kubernetes SIG 负责人',
    org: 'Google',
    stars: 9800,
    commits: 2800,
    prs: 350,
    issues: 620,
    languages: ['Go', 'Rust', 'Shell'],
    activityRank: 'Top 0.2%',
  },
  {
    id: 3,
    name: '王开源',
    handle: '@wangkaiyuan',
    avatar: 'W',
    role: 'React Core Team',
    org: 'Vercel',
    stars: 15600,
    commits: 4100,
    prs: 520,
    issues: 1100,
    languages: ['TypeScript', 'JavaScript', 'Rust'],
    activityRank: 'Top 0.05%',
  },
]

export default function OpenSourceDemoPage() {
  const { t } = useTranslation('common')
  return (
    <DemoPlaceholderPage
      title={t('demoOpenSource.title')}
      description={t('demoOpenSource.description')}
      icon={<GithubOutlined />}
      features={t('demoOpenSource.features', { returnObjects: true }) as string[]}
    >
      <div style={{ marginTop: 24 }}>
        {mockDevelopers.map((dev) => (
          <div
            key={dev.id}
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
                  {dev.avatar}
                </Avatar>
                <div>
                  <h3 style={{ margin: 0 }}>
                    {dev.name} <span style={{ color: '#999', fontSize: 14 }}>{dev.handle}</span>
                  </h3>
                  <p style={{ margin: '4px 0', color: '#666' }}>
                    {dev.role} · {dev.org}
                  </p>
                  <Tag color="blue">{dev.activityRank}</Tag>
                </div>
              </div>
              <Statistic
                title="Stars"
                value={dev.stars}
                prefix={<StarOutlined />}
              />
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 24 }}>
              <Statistic title="Commits" value={dev.commits} prefix={<BranchesOutlined />} />
              <Statistic title="PRs" value={dev.prs} prefix={<PullRequestOutlined />} />
              <Statistic title="Issues" value={dev.issues} prefix={<FireOutlined />} />
            </div>
            <div style={{ marginTop: 12 }}>
              {dev.languages.map((lang) => (
                <Tag key={lang} style={{ marginRight: 8 }}>{lang}</Tag>
              ))}
            </div>
          </div>
        ))}
      </div>
    </DemoPlaceholderPage>
  )
}
