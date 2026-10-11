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
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import type { CompOverviewOut } from '../../services/api/competition'
import { applyDomainCssVars, domainThemes } from '../../theme'
import { getErrorMessage, formatUTCToLocalDate, logger } from '../../utils'
import { useAuth } from '../../contexts/AuthContext'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import '../../i18n/namespaces/competition'

const { Title, Text, Paragraph } = Typography

const compTheme = domainThemes.competition

// 名次圈前三：金 / 银 / 铜
const RANK_CIRCLE_COLORS = ['#F6AD55', '#A0AEC0', '#D69E2E']

// 段位配色（通用，适配多赛事段位体系）
const RANK_TAG_COLORS: Record<string, string> = {
  gold: 'gold',
  silver: 'default',
  bronze: '#D69E2E',
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
}) => {
  const { t } = useTranslation('competition')
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
      <span title={t('medal.gold')}>
        <CrownOutlined style={{ color: '#F6AD55', marginRight: 2 }} />
        <Text strong style={{ color: '#B7791F', fontSize: 12 }}>
          {gold}
        </Text>
      </span>
      <span title={t('medal.silver')}>
        <TrophyOutlined style={{ color: '#A0AEC0', marginRight: 2 }} />
        <Text strong style={{ color: '#718096', fontSize: 12 }}>
          {silver}
        </Text>
      </span>
      <span title={t('medal.bronze')}>
        <FireOutlined style={{ color: '#DD6B20', marginRight: 2 }} />
        <Text strong style={{ color: '#C05621', fontSize: 12 }}>
          {bronze}
        </Text>
      </span>
    </span>
  )
}

const CompetitionOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation('competition')
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
          message.error(getErrorMessage(err, t('overview.loadError')))
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
  }, [retryTick, t])

  if (loading) return <PageSkeleton />

  if (error || !data) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title={t('common.loadFailed')}
          description={getErrorMessage(error, t('overview.loadErrorRetry'))}
          action={{ label: t('common.retry'), onClick: () => setRetryTick(t => t + 1) }}
        />
      </div>
    )
  }

  const hero = (
    <div style={{ background: compTheme.gradient, padding: '48px 24px', color: '#fff' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <TrophyOutlined style={{ fontSize: 32, marginBottom: 12 }} />
        <Title level={2} style={{ margin: 0, marginBottom: 8, color: '#fff' }}>
          {t('overview.title')}
        </Title>
        <Paragraph
          style={{ color: 'rgba(255,255,255,0.85)', fontSize: 15, margin: 0, maxWidth: 640 }}
        >
          {t('overview.subtitle')}
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
              <Title level={4}>{t('overview.emptyTitle')}</Title>
              <Paragraph type="secondary">{t('overview.adminEmptyDescription')}</Paragraph>
              <Button type="primary" onClick={() => navigate('/system-config?tab=comp-import')}>
                {t('overview.goImport')}
              </Button>
            </Card>
          ) : (
            <EmptyPlaceholder
              title={t('overview.emptyTitle')}
              description={t('overview.userEmptyDescription')}
            />
          )}
        </div>
      </div>
    )
  }

  const stats = [
    {
      title: t('overview.stats.talents'),
      value: data.total_talents,
      icon: <TeamOutlined />,
      color: compTheme.badgeBg,
    },
    {
      title: t('overview.stats.contests'),
      value: data.total_contests,
      icon: <TrophyOutlined />,
      color: compTheme.secondary,
    },
    {
      title: t('overview.stats.series'),
      value: data.total_series,
      icon: <FlagOutlined />,
      color: '#ED8936',
    },
    {
      title: t('overview.stats.medalists'),
      value: data.total_medalists,
      icon: <CrownOutlined />,
      color: '#D69E2E',
    },
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
          {/* 奖牌榜预览 */}
          <Col xs={24} lg={14}>
            <Card
              title={
                <span>
                  <TrophyOutlined style={{ color: compTheme.badgeBg, marginRight: 8 }} />
                  {t('overview.medalTop')}
                </span>
              }
              extra={
                <a onClick={() => navigate('/competition/search')}>
                  {t('overview.viewAll')} <RightOutlined style={{ fontSize: 11 }} />
                </a>
              }
              style={{ borderRadius: 12, height: '100%' }}
              styles={{ body: { padding: 8 } }}
            >
              {data.top_medalists.slice(0, 10).map((m, i) => (
                <div
                  key={m.talent_id}
                  onClick={() => navigate(`/competition/talents/${m.talent_id}`)}
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
                        {m.handle.startsWith('name:') ? (m.real_name ?? m.handle) : m.handle}
                      </Text>
                      <RankTitleTag title={m.rank_title} />
                    </div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {m.school ?? '-'} · {m.country_code ?? '-'}
                    </Text>
                  </div>
                  <MedalCounts
                    gold={m.medals_gold}
                    silver={m.medals_silver}
                    bronze={m.medals_bronze}
                  />
                  <Text
                    type="secondary"
                    style={{
                      fontSize: 12,
                      minWidth: 52,
                      textAlign: 'right',
                    }}
                  >
                    {t('overview.contestsCount', { n: m.contests_count })}
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
                  {t('overview.recentContests')}
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
                  <Tag color="orange">{t('overview.resultsCount', { n: c.results_count })}</Tag>
                </div>
              ))}
              {data.recent_contests.length === 0 && (
                <Text type="secondary" style={{ display: 'block', padding: 16 }}>
                  {t('overview.noContests')}
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
