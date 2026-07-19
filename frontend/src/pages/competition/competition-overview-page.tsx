import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Card, Tag, Typography, Statistic, Button, message } from 'antd'
import {
  TrophyOutlined,
  TeamOutlined,
  FlagOutlined,
  CrownOutlined,
  FireOutlined,
  CalendarOutlined,
  RightOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { CompOverviewOut } from '../../services/api/competition'
import { applyDomainCssVars, domainThemes } from '../../theme'
import { getErrorMessage, formatUTCToLocalDate, logger } from '../../utils'
import { useAuth } from '../../contexts/AuthContext'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'

const { Title, Text, Paragraph } = Typography

const compTheme = domainThemes.competition

// 名次圈前三：金 / 银 / 铜
const RANK_CIRCLE_COLORS = ['#F6AD55', '#A0AEC0', '#D69E2E']

// Codeforces 段位配色（newbie 灰 → legendary grandmaster 深红）
const RANK_TAG_COLORS: Record<string, string> = {
  newbie: 'default',
  pupil: 'green',
  specialist: 'cyan',
  expert: 'blue',
  'candidate master': 'purple',
  master: 'orange',
  'international master': 'volcano',
  grandmaster: 'red',
  'international grandmaster': 'red',
  'legendary grandmaster': '#cf1322',
}

const rankCircleStyle = (rank: number): React.CSSProperties => ({
  width: 32,
  height: 32,
  borderRadius: '50%',
  flexShrink: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  fontSize: 13,
  background: rank <= 3 ? RANK_CIRCLE_COLORS[rank - 1] : '#EDF2F7',
  color: rank <= 3 ? '#fff' : '#4A5568',
})

const RankTitleTag: React.FC<{ title: string | null }> = ({ title }) => {
  if (!title) return null
  return <Tag color={RANK_TAG_COLORS[title.toLowerCase()] ?? 'default'}>{title}</Tag>
}

const MedalCounts: React.FC<{ gold: number; silver: number; bronze: number }> = ({
  gold,
  silver,
  bronze,
}) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
    <span title="金牌">
      <CrownOutlined style={{ color: '#F6AD55', marginRight: 2 }} />
      <Text strong style={{ color: '#B7791F', fontSize: 12 }}>
        {gold}
      </Text>
    </span>
    <span title="银牌">
      <TrophyOutlined style={{ color: '#A0AEC0', marginRight: 2 }} />
      <Text strong style={{ color: '#718096', fontSize: 12 }}>
        {silver}
      </Text>
    </span>
    <span title="铜牌">
      <FireOutlined style={{ color: '#DD6B20', marginRight: 2 }} />
      <Text strong style={{ color: '#C05621', fontSize: 12 }}>
        {bronze}
      </Text>
    </span>
  </span>
)

const CompetitionOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [data, setData] = useState<CompOverviewOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [retryTick, setRetryTick] = useState(0)

  useEffect(() => {
    applyDomainCssVars('competition')
  }, [])

  useEffect(() => {
    let cancelled = false
    const fetchOverview = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await api.comp.getOverview()
        if (!cancelled) setData(res.data)
      } catch (err) {
        if (!cancelled) {
          logger.error('Failed to fetch competition overview:', err)
          message.error(getErrorMessage(err, '加载竞赛概览失败'))
          setError(err)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchOverview()
    return () => {
      cancelled = true
    }
  }, [retryTick])

  if (loading) return <PageSkeleton />

  if (error || !data) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="加载失败"
          description={getErrorMessage(error, '加载竞赛概览失败，请稍后重试')}
          action={{ label: '重试', onClick: () => setRetryTick(t => t + 1) }}
        />
      </div>
    )
  }

  const hero = (
    <div style={{ background: compTheme.gradient, padding: '48px 24px', color: '#fff' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <TrophyOutlined style={{ fontSize: 32, marginBottom: 12 }} />
        <Title level={2} style={{ margin: 0, marginBottom: 8, color: '#fff' }}>
          竞赛人才
        </Title>
        <Paragraph
          style={{ color: 'rgba(255,255,255,0.85)', fontSize: 15, margin: 0, maxWidth: 640 }}
        >
          覆盖 Codeforces 等全球顶级赛事 · 发现顶尖竞赛选手
        </Paragraph>
      </div>
    </div>
  )

  // 空库：管理员显示导入引导，普通用户显示空态
  if (data.total_talents === 0) {
    return (
      <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
        {hero}
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '48px 24px' }}>
          {isAdmin ? (
            <Card
              style={{ maxWidth: 560, margin: '0 auto', textAlign: 'center', borderRadius: 12 }}
            >
              <TrophyOutlined
                style={{ fontSize: 32, color: compTheme.badgeBg, marginBottom: 12 }}
              />
              <Title level={4}>暂无竞赛人才数据</Title>
              <Paragraph type="secondary">
                数据库中还没有竞赛人才，请先在系统配置中导入 Codeforces 赛事榜单数据
              </Paragraph>
              <Button
                type="primary"
                onClick={() => navigate('/system-config?tab=comp-import')}
              >
                去系统配置导入
              </Button>
            </Card>
          ) : (
            <EmptyPlaceholder
              title="暂无竞赛人才数据"
              description="管理员尚未导入竞赛数据，请稍后再来"
            />
          )}
        </div>
      </div>
    )
  }

  const stats = [
    {
      title: '收录选手',
      value: data.total_talents,
      icon: <TeamOutlined />,
      color: compTheme.badgeBg,
    },
    {
      title: '覆盖赛事',
      value: data.total_contests,
      icon: <TrophyOutlined />,
      color: compTheme.secondary,
    },
    { title: '赛事系列', value: data.total_series, icon: <FlagOutlined />, color: '#ED8936' },
    { title: '金牌选手', value: data.total_medalists, icon: <CrownOutlined />, color: '#D69E2E' },
  ]

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {hero}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 24px 48px' }}>
        {/* 统计卡 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {stats.map(s => (
            <Col xs={24} sm={12} lg={6} key={s.title}>
              <Card style={{ borderRadius: 12 }} styles={{ body: { padding: '16px 20px' } }}>
                <Statistic
                  title={<Text style={{ color: '#718096', fontSize: 13 }}>{s.title}</Text>}
                  value={s.value}
                  prefix={<span style={{ color: s.color }}>{s.icon}</span>}
                  valueStyle={{ color: s.color, fontSize: 24, fontWeight: 700 }}
                />
              </Card>
            </Col>
          ))}
        </Row>

        <Row gutter={[16, 16]}>
          {/* 积分榜预览 */}
          <Col xs={24} lg={14}>
            <Card
              title={
                <span>
                  <TrophyOutlined style={{ color: compTheme.badgeBg, marginRight: 8 }} />
                  积分榜 Top 10
                </span>
              }
              extra={
                <a onClick={() => navigate('/competition/search')}>
                  查看全部 <RightOutlined style={{ fontSize: 11 }} />
                </a>
              }
              style={{ borderRadius: 12, height: '100%' }}
              styles={{ body: { padding: 8 } }}
            >
              {data.top_talents.slice(0, 10).map((t, i) => (
                <div
                  key={t.talent_id}
                  onClick={() => navigate(`/competition/talents/${t.talent_id}`)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px 12px',
                    borderRadius: 10,
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--domain-light-bg)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <span style={rankCircleStyle(i + 1)}>{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Text strong ellipsis style={{ fontSize: 14 }}>
                        {t.handle}
                      </Text>
                      <RankTitleTag title={t.rank_title} />
                    </div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {t.school ?? '-'} · {t.country_code ?? '-'}
                    </Text>
                  </div>
                  <MedalCounts
                    gold={t.medals_gold}
                    silver={t.medals_silver}
                    bronze={t.medals_bronze}
                  />
                  <Text
                    strong
                    style={{
                      color: compTheme.badgeBg,
                      fontSize: 15,
                      minWidth: 52,
                      textAlign: 'right',
                    }}
                  >
                    {t.current_rating ?? '-'}
                  </Text>
                </div>
              ))}
            </Card>
          </Col>

          {/* 最近赛事 */}
          <Col xs={24} lg={10}>
            <Card
              title={
                <span>
                  <CalendarOutlined style={{ color: compTheme.badgeBg, marginRight: 8 }} />
                  最近赛事
                </span>
              }
              style={{ borderRadius: 12, height: '100%' }}
              styles={{ body: { padding: 8 } }}
            >
              {data.recent_contests.map(c => (
                <div
                  key={c.contest_id}
                  onClick={() => navigate(`/competition/contests/${c.contest_id}`)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px 12px',
                    borderRadius: 10,
                    cursor: 'pointer',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--domain-light-bg)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong ellipsis style={{ display: 'block', fontSize: 14 }}>
                      {c.name}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <CalendarOutlined style={{ marginRight: 4 }} />
                      {formatUTCToLocalDate(c.start_time)}
                    </Text>
                  </div>
                  <Tag color="orange">{c.results_count} 条成绩</Tag>
                </div>
              ))}
              {data.recent_contests.length === 0 && (
                <Text type="secondary" style={{ display: 'block', padding: 16 }}>
                  暂无赛事数据
                </Text>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default CompetitionOverviewPage
