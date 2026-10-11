import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { TabsProps, TableProps } from 'antd'
import {
  Row,
  Col,
  Card,
  Tag,
  Typography,
  Button,
  Space,
  Divider,
  Avatar,
  Table,
  Tabs,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  BankOutlined,
  GlobalOutlined,
  LinkOutlined,
  CrownOutlined,
  TrophyOutlined,
  FireOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import type { CompResultItem, CompTalentDetail } from '../../services/api/competition'
import { applyDomainCssVars, domainThemes } from '../../theme'
import { getErrorMessage, formatNumber, formatUTCToLocalDate, logger } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import '../../i18n/namespaces/competition'

const { Title, Text } = Typography

const compTheme = domainThemes.competition

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

// Award tag colors — labels are translated via competition:medal.* at render time
const AWARD_COLORS: Record<string, string> = {
  gold: 'gold',
  silver: 'default',
  bronze: 'volcano',
  hm: 'blue',
}

// rating_before → rating_after，涨绿跌红
const renderRatingChange = (before: number | null, after: number | null) => {
  if (before == null || after == null) return <Text type="secondary">-</Text>
  const delta = after - before
  const color = delta > 0 ? '#52c41a' : delta < 0 ? '#ff4d4f' : '#718096'
  return (
    <Space size={4}>
      <Text type="secondary">{before}</Text>
      <Text type="secondary">→</Text>
      <Text strong style={{ color }}>
        {after}
      </Text>
      {delta !== 0 && (
        <Text style={{ color, fontSize: 12 }}>({delta > 0 ? `+${delta}` : delta})</Text>
      )}
    </Space>
  )
}

const CompetitionTalentDetailPage: React.FC = () => {
  const { t } = useTranslation('competition')
  const { id: idParam } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const id = idParam ? Number(idParam) : NaN

  const renderAward = (award: string | null) => {
    if (!award) return <Text type="secondary">-</Text>
    const color = AWARD_COLORS[award.toLowerCase()]
    if (!color) return <Tag>{award}</Tag>
    return <Tag color={color}>{t(`medal.${award.toLowerCase()}`, { defaultValue: award })}</Tag>
  }

  const [talent, setTalent] = useState<CompTalentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [notFound, setNotFound] = useState(false)
  const [retryTick, setRetryTick] = useState(0)

  useEffect(() => {
    applyDomainCssVars('competition')
  }, [])

  useEffect(() => {
    if (Number.isNaN(id)) {
      setLoading(false)
      setNotFound(true)
      return
    }
    let cancelled = false
    const fetchTalent = async () => {
      setLoading(true)
      setError(null)
      setNotFound(false)
      try {
        const res = await api.comp.getTalent(id)
        if (!cancelled) setTalent(res.data)
      } catch (err) {
        if (!cancelled) {
          const status = (err as { response?: { status?: number } })?.response?.status
          logger.error('Failed to fetch competition talent:', err)
          if (status === 404) {
            setNotFound(true)
          } else {
            message.error(getErrorMessage(err, t('talent.loadError')))
            setError(err)
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchTalent()
    return () => {
      cancelled = true
    }
  }, [id, retryTick, t])

  if (loading) return <PageSkeleton />

  if (notFound) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title={t('talent.notFoundTitle')}
          description={t('talent.notFoundDescription')}
          action={{
            label: t('talent.backToSearch'),
            onClick: () => navigate('/competition/search'),
          }}
        />
      </div>
    )
  }

  if (error || !talent) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title={t('common.loadFailed')}
          description={getErrorMessage(error, t('talent.loadErrorRetry'))}
          action={{ label: t('common.retry'), onClick: () => setRetryTick(t => t + 1) }}
        />
      </div>
    )
  }

  // 积分趋势点：rating_after 非空且有时间，按时间升序
  const trendPoints = talent.results
    .filter(
      (r): r is CompResultItem & { rating_after: number; start_time: string } =>
        r.rating_after != null && r.start_time != null
    )
    .slice()
    .sort((a, b) => (a.start_time < b.start_time ? -1 : 1))

  const trendOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: trendPoints.map(p => formatUTCToLocalDate(p.start_time)),
      boundaryGap: false,
    },
    yAxis: { type: 'value', scale: true },
    series: [
      {
        type: 'line',
        data: trendPoints.map(p => p.rating_after),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        // ECharts 渲染到 canvas，CSS 变量不生效，用 hex 色值
        lineStyle: { color: compTheme.badgeBg, width: 2 },
        itemStyle: { color: compTheme.badgeBg },
        areaStyle: { color: 'rgba(221, 107, 32, 0.12)' },
      },
    ],
  }

  const resultColumns: TableProps<CompResultItem>['columns'] = [
    {
      title: t('talent.columns.contest'),
      dataIndex: 'contest_name',
      render: (name: string, r) => (
        <a onClick={() => navigate(`/competition/contests/${r.contest_id}`)}>{name}</a>
      ),
    },
    {
      title: t('talent.columns.time'),
      dataIndex: 'start_time',
      width: 120,
      render: (v: string | null) => formatUTCToLocalDate(v),
    },
    {
      title: t('talent.columns.rank'),
      dataIndex: 'rank',
      width: 80,
      render: (v: number | null) => (v != null ? `#${v}` : '-'),
    },
    { title: t('talent.columns.award'), dataIndex: 'award', width: 110, render: renderAward },
    {
      title: t('talent.columns.ratingChange'),
      width: 200,
      render: (_, r) => renderRatingChange(r.rating_before, r.rating_after),
    },
  ]

  const tabItems: TabsProps['items'] = [
    {
      key: 'results',
      label: t('talent.resultsTab', { n: talent.results.length }),
      children: (
        <Table<CompResultItem>
          rowKey={r => String(r.contest_id)}
          columns={resultColumns}
          dataSource={talent.results}
          pagination={
            talent.results.length > 20
              ? { pageSize: 20, showTotal: count => t('talent.contestsTotal', { n: count }) }
              : false
          }
          size="middle"
        />
      ),
    },
  ]

  // 趋势点不足 2 个时隐藏「积分趋势」Tab
  if (trendPoints.length >= 2) {
    tabItems.push({
      key: 'trend',
      label: t('talent.trendTab'),
      children: <ReactECharts option={trendOption} style={{ height: 320 }} />,
    })
  }

  const medalStats = [
    {
      icon: <CrownOutlined />,
      color: '#F6AD55',
      label: t('medal.gold'),
      value: talent.medals_gold,
    },
    {
      icon: <TrophyOutlined />,
      color: '#A0AEC0',
      label: t('medal.silver'),
      value: talent.medals_silver,
    },
    {
      icon: <FireOutlined />,
      color: '#DD6B20',
      label: t('medal.bronze'),
      value: talent.medals_bronze,
    },
  ]

  return (
    <div
      style={{
        padding: '80px 24px 24px',
        background: 'var(--color-bg-gray-light)',
        minHeight: '100vh',
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <BreadcrumbNav
          items={[
            { label: t('common.domain'), path: '/competition' },
            { label: t('talent.breadcrumbSearch'), path: '/competition/search' },
            { label: talent.handle },
          ]}
        />

        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigateBack(navigate, '/competition/search')}
          style={{ marginBottom: 16 }}
        >
          {t('common.back')}
        </Button>

        <Row gutter={[24, 24]}>
          {/* 左：sticky 身份卡 */}
          <Col xs={24} md={8} lg={7} xl={6}>
            <Card style={{ borderRadius: 12, position: 'sticky', top: 24 }}>
              <div style={{ textAlign: 'center' }}>
                <Avatar
                  size={80}
                  src={talent.avatar_url}
                  style={{ background: compTheme.gradient, fontSize: 32, fontWeight: 700 }}
                >
                  {(talent.handle.startsWith('name:')
                    ? (talent.real_name ?? talent.handle)
                    : talent.handle
                  )
                    .charAt(0)
                    .toUpperCase()}
                </Avatar>
                <Title level={4} style={{ marginTop: 12, marginBottom: 4 }}>
                  {talent.handle.startsWith('name:')
                    ? (talent.real_name ?? talent.handle)
                    : talent.handle}
                </Title>
                {talent.real_name && !talent.handle.startsWith('name:') && (
                  <Text type="secondary" style={{ display: 'block' }}>
                    {talent.real_name}
                  </Text>
                )}
                {talent.rank_title && (
                  <div style={{ marginTop: 8 }}>
                    <Tag color={RANK_TAG_COLORS[talent.rank_title.toLowerCase()] ?? 'default'}>
                      {talent.rank_title}
                    </Tag>
                  </div>
                )}
              </div>

              <Divider />

              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  <BankOutlined style={{ marginRight: 8 }} />
                  {talent.school ?? '-'}
                </Text>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  <GlobalOutlined style={{ marginRight: 8 }} />
                  {talent.country_code ?? '-'}
                </Text>
                {talent.global_rank != null && (
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    <TrophyOutlined style={{ marginRight: 8 }} />
                    {t('talent.globalRank', { rank: formatNumber(talent.global_rank) })}
                  </Text>
                )}
              </Space>

              <Divider />

              <div style={{ textAlign: 'center' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('talent.currentRating')}
                </Text>
                <div
                  style={{
                    fontSize: 34,
                    fontWeight: 700,
                    color: compTheme.badgeBg,
                    lineHeight: 1.2,
                  }}
                >
                  {formatNumber(talent.current_rating)}
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {t('talent.maxRating', { rating: formatNumber(talent.max_rating) })}
                </Text>
              </div>

              <Divider />

              <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
                {medalStats.map(m => (
                  <div key={m.label}>
                    <div style={{ color: m.color, fontSize: 18 }}>{m.icon}</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{m.value}</div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {m.label}
                    </Text>
                  </div>
                ))}
              </div>

              <div style={{ textAlign: 'center', marginTop: 12 }}>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {t('talent.contestsCount', { n: talent.contests_count })}
                </Text>
              </div>

              {talent.specialties && talent.specialties.length > 0 && (
                <>
                  <Divider />
                  <Space size={4} wrap>
                    {talent.specialties.map(s => (
                      <Tag key={s} color="orange">
                        {s}
                      </Tag>
                    ))}
                  </Space>
                </>
              )}

              {talent.profile_url && (
                <Button
                  type="primary"
                  block
                  icon={<LinkOutlined />}
                  href={talent.profile_url}
                  target="_blank"
                  style={{ marginTop: 16 }}
                >
                  {t('talent.profile')}
                </Button>
              )}
            </Card>
          </Col>

          {/* 右：Tabs 内容 */}
          <Col xs={24} md={16} lg={17} xl={18}>
            <Card style={{ borderRadius: 12 }}>
              <Tabs items={tabItems} destroyInactiveTabPane={false} />
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default CompetitionTalentDetailPage
