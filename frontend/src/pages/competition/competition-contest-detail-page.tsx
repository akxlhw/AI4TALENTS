import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { TableProps } from 'antd'
import { Card, Tag, Typography, Button, Space, Table, Tooltip, message } from 'antd'
import {
  ArrowLeftOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  LinkOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type {
  CompContestDetail,
  CompLeaderboardEntry,
  CompTeamLeaderboardEntry,
} from '../../services/api/competition'
import { applyDomainCssVars, domainThemes } from '../../theme'
import { getErrorMessage, formatUTCToLocal, logger } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'

const { Title, Text } = Typography

const compTheme = domainThemes.competition

const AWARD_MAP: Record<string, { label: string; color: string }> = {
  gold: { label: '金牌', color: 'gold' },
  silver: { label: '银牌', color: 'default' },
  bronze: { label: '铜牌', color: 'volcano' },
  hm: { label: '荣誉提名', color: 'blue' },
}

// 名次前三奖牌色圆点
const RANK_DOT_COLORS = ['#F6AD55', '#A0AEC0', '#D69E2E']

const renderRank = (rank: number | null) => {
  if (rank == null) return <Text type="secondary">-</Text>
  if (rank > 3) return <Text>{rank}</Text>
  return (
    <span
      style={{
        display: 'inline-flex',
        width: 24,
        height: 24,
        borderRadius: '50%',
        background: RANK_DOT_COLORS[rank - 1],
        color: '#fff',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: 12,
      }}
    >
      {rank}
    </span>
  )
}

const renderAward = (award: string | null) => {
  if (!award) return <Text type="secondary">-</Text>
  const a = AWARD_MAP[award.toLowerCase()]
  return a ? <Tag color={a.color}>{a.label}</Tag> : <Tag>{award}</Tag>
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

const formatDuration = (seconds: number | null): string => {
  if (seconds == null) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  if (h === 0) return `${m} 分钟`
  if (m === 0) return `${h} 小时`
  return `${h} 小时 ${m} 分钟`
}

const CompetitionContestDetailPage: React.FC = () => {
  const { id: idParam } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const id = idParam ? Number(idParam) : NaN

  const [contest, setContest] = useState<CompContestDetail | null>(null)
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
    const fetchContest = async () => {
      setLoading(true)
      setError(null)
      setNotFound(false)
      try {
        const res = await api.comp.getContest(id)
        if (!cancelled) setContest(res.data)
      } catch (err) {
        if (!cancelled) {
          const status = (err as { response?: { status?: number } })?.response?.status
          logger.error('Failed to fetch competition contest:', err)
          if (status === 404) {
            setNotFound(true)
          } else {
            message.error(getErrorMessage(err, '加载赛事详情失败'))
            setError(err)
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchContest()
    return () => {
      cancelled = true
    }
  }, [id, retryTick])

  if (loading) return <PageSkeleton />

  if (notFound) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="赛事不存在或已删除"
          description="该赛事可能已被移除或链接有误"
          action={{ label: '返回竞赛首页', onClick: () => navigate('/competition') }}
        />
      </div>
    )
  }

  if (error || !contest) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="加载失败"
          description={getErrorMessage(error, '加载赛事详情失败，请稍后重试')}
          action={{ label: '重试', onClick: () => setRetryTick(t => t + 1) }}
        />
      </div>
    )
  }

  const columns: TableProps<CompLeaderboardEntry>['columns'] = [
    { title: '名次', dataIndex: 'rank', width: 70, render: renderRank },
    {
      title: '选手',
      dataIndex: 'handle',
      render: (handle: string | null, r) => {
        if (handle == null) return <Text type="secondary">-</Text>
        // 无账号源用 name: 伪 handle 作身份键，展示时回落到真实姓名
        const display = handle.startsWith('name:') ? (r.real_name ?? handle) : handle
        return (
          <div>
            {r.talent_id != null ? (
              <a onClick={() => navigate(`/competition/talents/${r.talent_id}`)}>{display}</a>
            ) : (
              <Text>{display}</Text>
            )}
            {r.team_name && (
              <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
                {r.team_name}
              </Text>
            )}
          </div>
        )
      },
    },
    {
      title: '学校',
      dataIndex: 'school',
      render: (v: string | null) => v ?? <Text type="secondary">-</Text>,
    },
    {
      title: '国家',
      dataIndex: 'country_code',
      width: 80,
      render: (v: string | null) => v ?? <Text type="secondary">-</Text>,
    },
    {
      title: '得分',
      dataIndex: 'score',
      width: 90,
      render: (v: number | null) => (v != null ? v : <Text type="secondary">-</Text>),
    },
    {
      title: '积分变动',
      width: 190,
      render: (_, r) => renderRatingChange(r.rating_before, r.rating_after),
    },
    { title: '奖项', dataIndex: 'award', width: 110, render: renderAward },
  ]

  const teamColumns: TableProps<CompTeamLeaderboardEntry>['columns'] = [
    { title: '名次', dataIndex: 'rank', width: 70, render: renderRank },
    {
      title: '队伍',
      dataIndex: 'team_name',
      render: (v: string | null) => v ?? <Text type="secondary">-</Text>,
    },
    {
      title: '学校',
      dataIndex: 'school',
      render: (v: string | null) => v ?? <Text type="secondary">-</Text>,
    },
    {
      title: '国家',
      dataIndex: 'country_code',
      width: 80,
      render: (v: string | null) => v ?? <Text type="secondary">-</Text>,
    },
    {
      title: '得分',
      dataIndex: 'score',
      width: 90,
      render: (v: number | null) => (v != null ? v : <Text type="secondary">-</Text>),
    },
    { title: '奖项', dataIndex: 'award', width: 110, render: renderAward },
    {
      title: '成员',
      dataIndex: 'team_members',
      width: 90,
      render: (members: CompTeamLeaderboardEntry['team_members']) =>
        members && members.length > 0 ? (
          <Tooltip
            title={
              <div style={{ whiteSpace: 'pre-line' }}>
                {members
                  .map(
                    m =>
                      `${m.real_name}${m.handle ? ` (${m.handle})` : ''}${m.role ? ` · ${m.role}` : ''}`
                  )
                  .join('\n')}
              </div>
            }
          >
            <a>{members.length} 人</a>
          </Tooltip>
        ) : (
          <Text type="secondary">-</Text>
        ),
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
            { label: '竞赛', path: '/competition' },
            { label: '赛事列表', path: '/competition' },
            { label: contest.name },
          ]}
        />

        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigateBack(navigate, '/competition')}
          style={{ marginBottom: 16 }}
        >
          返回
        </Button>

        {/* Header */}
        <Card style={{ borderRadius: 12, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 240 }}>
              <Space size={8} wrap>
                <Title level={4} style={{ margin: 0 }}>
                  {contest.name}
                </Title>
                <Tag color="orange">{contest.series_code}</Tag>
                {contest.season && <Tag>{contest.season}</Tag>}
              </Space>
              <Space size={16} wrap style={{ marginTop: 8 }}>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  <CalendarOutlined style={{ marginRight: 6 }} />
                  {formatUTCToLocal(contest.start_time, {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false,
                  })}
                </Text>
                {contest.duration_seconds != null && (
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    <ClockCircleOutlined style={{ marginRight: 6 }} />
                    时长 {formatDuration(contest.duration_seconds)}
                  </Text>
                )}
              </Space>
            </div>
            {contest.source_url && (
              <Button icon={<LinkOutlined />} href={contest.source_url} target="_blank">
                源站链接
              </Button>
            )}
          </div>
        </Card>

        {/* 个人榜 */}
        {contest.results.length > 0 && (
          <Card
            title={
              <span>
                <UserOutlined style={{ color: compTheme.badgeBg, marginRight: 8 }} />
                个人榜 ({contest.results.length})
              </span>
            }
            style={{ borderRadius: 12, marginBottom: 16 }}
            styles={{ body: { paddingTop: 0 } }}
          >
            <Table<CompLeaderboardEntry>
              rowKey={(_r, i) => `p-${i ?? 0}`}
              columns={columns}
              dataSource={contest.results}
              pagination={{
                pageSize: 50,
                showTotal: t => `共 ${t} 条`,
                hideOnSinglePage: true,
              }}
              size="middle"
            />
          </Card>
        )}

        {/* 团队榜：团队赛时另渲染；个人榜为空时只显示团队榜 */}
        {contest.team_results.length > 0 && (
          <Card
            title={
              <span>
                <TeamOutlined style={{ color: compTheme.badgeBg, marginRight: 8 }} />
                团队榜 ({contest.team_results.length})
              </span>
            }
            style={{ borderRadius: 12, marginBottom: 16 }}
            styles={{ body: { paddingTop: 0 } }}
          >
            <Table<CompTeamLeaderboardEntry>
              rowKey={(_r, i) => `t-${i ?? 0}`}
              columns={teamColumns}
              dataSource={contest.team_results}
              pagination={{
                pageSize: 50,
                showTotal: t => `共 ${t} 条`,
                hideOnSinglePage: true,
              }}
              size="middle"
            />
          </Card>
        )}

        {contest.results.length === 0 && contest.team_results.length === 0 && (
          <Card style={{ borderRadius: 12 }}>
            <EmptyPlaceholder title="暂无榜单数据" description="该赛事尚未导入成绩" />
          </Card>
        )}
      </div>
    </div>
  )
}

export default CompetitionContestDetailPage
