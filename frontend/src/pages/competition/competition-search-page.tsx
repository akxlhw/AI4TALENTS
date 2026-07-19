import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Row,
  Col,
  Card,
  Tag,
  Typography,
  Input,
  InputNumber,
  Select,
  Button,
  Pagination,
  Avatar,
  Progress,
  Skeleton,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  CrownOutlined,
  TrophyOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { api } from '../../services/api'
import type { CompTalentSummary } from '../../services/api/competition'
import type { PaginatedResponse } from '../../types'
import { applyDomainCssVars, domainThemes } from '../../theme'
import { getErrorMessage, logger } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'

const { Text } = Typography

const compTheme = domainThemes.competition

const PAGE_SIZE = 12

// Codeforces 段位列表（值为后端存储的原始字符串）
const RANK_OPTIONS = [
  { label: 'Newbie', value: 'newbie' },
  { label: 'Pupil', value: 'pupil' },
  { label: 'Specialist', value: 'specialist' },
  { label: 'Expert', value: 'expert' },
  { label: 'Candidate Master', value: 'candidate master' },
  { label: 'Master', value: 'master' },
  { label: 'International Master', value: 'international master' },
  { label: 'Grandmaster', value: 'grandmaster' },
  { label: 'International Grandmaster', value: 'international grandmaster' },
  { label: 'Legendary Grandmaster', value: 'legendary grandmaster' },
]

const SORT_OPTIONS = [
  { label: '积分降序', value: 'rating_desc' },
  { label: '积分升序', value: 'rating_asc' },
  { label: '参赛场次多', value: 'contests_desc' },
  { label: '奖牌数多', value: 'medals_desc' },
  { label: '最近参赛', value: 'recent_desc' },
]

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

const TalentCard: React.FC<{ talent: CompTalentSummary; onClick: () => void }> = ({
  talent: t,
  onClick,
}) => {
  const ratingPercent =
    t.current_rating != null ? Math.min((t.current_rating / 4000) * 100, 100) : 0
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{ borderRadius: 12, height: '100%' }}
      styles={{ body: { padding: 16 } }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <Avatar
          size={48}
          src={t.avatar_url}
          style={{ background: compTheme.gradient, fontSize: 18, fontWeight: 600, flexShrink: 0 }}
        >
          {t.handle.charAt(0).toUpperCase()}
        </Avatar>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text strong ellipsis style={{ fontSize: 15, display: 'block' }}>
            {t.handle}
          </Text>
          <RankTitleTag title={t.rank_title} />
        </div>
      </div>
      <Text type="secondary" ellipsis style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
        {t.school ?? '-'} · {t.country_code ?? '-'}
      </Text>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <Text style={{ fontSize: 12, color: '#A0AEC0' }}>竞赛积分</Text>
        <Text strong style={{ color: compTheme.badgeBg, fontSize: 15 }}>
          {t.current_rating ?? '-'}
        </Text>
      </div>
      <Progress
        percent={Number(ratingPercent.toFixed(1))}
        showInfo={false}
        strokeColor={{ '0%': compTheme.secondary, '100%': compTheme.badgeBg }}
        trailColor="#EDF2F7"
        size="small"
        style={{ marginBottom: 12 }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <MedalCounts gold={t.medals_gold} silver={t.medals_silver} bronze={t.medals_bronze} />
        <Text type="secondary" style={{ fontSize: 12 }}>
          参赛 {t.contests_count} 场
        </Text>
      </div>
    </Card>
  )
}

const CompetitionSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    applyDomainCssVars('competition')
  }, [])

  // URL 是筛选条件的单一事实源（浏览器前进/后退自动跟随）
  const urlKeyword = searchParams.get('keyword') ?? ''
  const urlCountry = searchParams.get('country_code') ?? ''
  const urlSchool = searchParams.get('school') ?? ''
  const minRatingStr = searchParams.get('min_rating') ?? ''
  const rankTitle = searchParams.get('rank_title') ?? ''
  const sortBy = searchParams.get('sort_by') ?? 'rating_desc'
  const page = Math.max(1, Number(searchParams.get('page') ?? '1') || 1)

  // 文本类筛选的本地输入态，400ms 防抖后写回 URL，避免逐键触发请求
  const [text, setText] = useState({ keyword: urlKeyword, country: urlCountry, school: urlSchool })

  // URL 外部变化（前进/后退/重置）→ 同步本地输入态
  useEffect(() => {
    setText({ keyword: urlKeyword, country: urlCountry, school: urlSchool })
  }, [urlKeyword, urlCountry, urlSchool])

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>, resetPage = true) => {
      const next = new URLSearchParams(searchParams)
      Object.entries(updates).forEach(([k, v]) => {
        if (v === undefined || v === '') next.delete(k)
        else next.set(k, v)
      })
      if (resetPage) next.delete('page')
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams]
  )

  // 本地输入态 → 防抖写回 URL
  useEffect(() => {
    if (text.keyword === urlKeyword && text.country === urlCountry && text.school === urlSchool) {
      return
    }
    const timer = setTimeout(() => {
      updateParams({
        keyword: text.keyword || undefined,
        country_code: text.country || undefined,
        school: text.school || undefined,
      })
    }, 400)
    return () => clearTimeout(timer)
  }, [text, urlKeyword, urlCountry, urlSchool, updateParams])

  const [data, setData] = useState<PaginatedResponse<CompTalentSummary> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [retryTick, setRetryTick] = useState(0)
  const paramsKey = searchParams.toString()

  useEffect(() => {
    let cancelled = false
    const fetchTalents = async () => {
      setLoading(true)
      setError(null)
      try {
        const sp = new URLSearchParams(paramsKey)
        const minRating = sp.get('min_rating')
        const res = await api.comp.listTalents({
          keyword: sp.get('keyword') || undefined,
          country_code: sp.get('country_code') || undefined,
          school: sp.get('school') || undefined,
          min_rating: minRating ? Number(minRating) : undefined,
          rank_title: sp.get('rank_title') || undefined,
          sort_by: sp.get('sort_by') || 'rating_desc',
          page: Math.max(1, Number(sp.get('page') ?? '1') || 1),
          page_size: PAGE_SIZE,
        })
        if (!cancelled) setData(res.data)
      } catch (err) {
        if (!cancelled) {
          logger.error('Failed to fetch competition talents:', err)
          message.error(getErrorMessage(err, '加载选手列表失败'))
          setError(err)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchTalents()
    return () => {
      cancelled = true
    }
  }, [paramsKey, retryTick])

  const resetFilters = () => {
    setText({ keyword: '', country: '', school: '' })
    setSearchParams(new URLSearchParams(), { replace: true })
  }

  const commitMinRating = (raw: string) => {
    const trimmed = raw.trim()
    const n = Number(trimmed)
    const next = trimmed !== '' && !Number.isNaN(n) && n >= 0 ? String(Math.floor(n)) : undefined
    if ((next ?? '') !== minRatingStr) updateParams({ min_rating: next })
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '12px 24px 0' }}>
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigateBack(navigate, '/competition')}
          style={{
            color: 'var(--domain-primary, #1A202C)',
            fontWeight: 500,
            marginBottom: 4,
            paddingLeft: 0,
          }}
        >
          返回
        </Button>
        <BreadcrumbNav items={[{ label: '竞赛', path: '/competition' }, { label: '选手搜索' }]} />
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px 48px' }}>
        {/* 筛选器 */}
        <Card style={{ marginBottom: 16, borderRadius: 12 }}>
          <Row gutter={[12, 12]} align="middle">
            <Col xs={24} sm={12} md={8} lg={5}>
              <Input.Search
                placeholder="搜索 handle / 真名..."
                value={text.keyword}
                onChange={e => setText(t => ({ ...t, keyword: e.target.value }))}
                onSearch={v => updateParams({ keyword: v || undefined })}
                allowClear
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={3}>
              <Input
                placeholder="国家代码"
                value={text.country}
                onChange={e => setText(t => ({ ...t, country: e.target.value }))}
                allowClear
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={4}>
              <Input
                placeholder="学校"
                value={text.school}
                onChange={e => setText(t => ({ ...t, school: e.target.value }))}
                allowClear
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={3}>
              <InputNumber
                key={minRatingStr}
                defaultValue={minRatingStr ? Number(minRatingStr) : undefined}
                placeholder="最低积分"
                min={0}
                style={{ width: '100%' }}
                onBlur={e => commitMinRating(e.target.value)}
                onPressEnter={e => commitMinRating((e.target as HTMLInputElement).value)}
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={4}>
              <Select
                placeholder="段位"
                style={{ width: '100%' }}
                value={rankTitle || undefined}
                onChange={(v?: string) => updateParams({ rank_title: v || undefined })}
                options={RANK_OPTIONS}
                allowClear
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={3}>
              <Select
                style={{ width: '100%' }}
                value={sortBy}
                onChange={(v: string) => updateParams({ sort_by: v })}
                options={SORT_OPTIONS}
              />
            </Col>
            <Col xs={12} sm={6} md={4} lg={2}>
              <Button icon={<ReloadOutlined />} onClick={resetFilters} block>
                重置
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 结果区 */}
        {error && !data ? (
          <EmptyPlaceholder
            title="加载失败"
            description={getErrorMessage(error, '加载选手列表失败，请稍后重试')}
            action={{ label: '重试', onClick: () => setRetryTick(t => t + 1) }}
          />
        ) : loading ? (
          <Row gutter={[16, 16]}>
            {Array.from({ length: 8 }).map((_, i) => (
              <Col xs={24} sm={12} md={8} lg={6} key={i}>
                <Card style={{ borderRadius: 12 }}>
                  <Skeleton active avatar paragraph={{ rows: 2 }} />
                </Card>
              </Col>
            ))}
          </Row>
        ) : items.length === 0 ? (
          <EmptyPlaceholder
            title="未找到匹配的选手"
            description="尝试调整筛选条件"
            action={{ label: '清除筛选', onClick: resetFilters }}
          />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {items.map(t => (
                <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
                  <TalentCard
                    talent={t}
                    onClick={() => navigate(`/competition/talents/${t.talent_id}`)}
                  />
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'center', marginTop: 32 }}>
              <Pagination
                current={page}
                total={total}
                pageSize={PAGE_SIZE}
                onChange={p => updateParams({ page: String(p) }, false)}
                showTotal={t => `共 ${t} 人`}
                showSizeChanger={false}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default CompetitionSearchPage
