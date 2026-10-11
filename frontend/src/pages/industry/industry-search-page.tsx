import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Col, Pagination, Row, Spin, Typography, Card, Statistic, Input, Tag,
  Badge, Select, Button,
} from 'antd'
import {
  SearchOutlined, TeamOutlined, TrophyOutlined, UserOutlined,
  ClearOutlined, FireOutlined, StarOutlined,
} from '@ant-design/icons'
import { useIndustryTalents, useIndustryPositions, useTechDirectionOptions } from '../../hooks/useIndustryQueries'
import { useIndustrySearchStore } from '../../stores/industrySearchStore'
import type { IndustrySearchState } from '../../stores/industrySearchStore'
import { applyDomainCssVars } from '../../theme'
import '../../i18n/namespaces/industry'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import IndustryTalentCard from './components/industry-talent-card'
import {
  candidateStatusOptions, minScoreOptions, sourcePlatformOptions, industrySortOptions,
  formatScore,
} from './constants/industry-config'

const { Text, Title, Paragraph } = Typography

const IndustrySearchPage: React.FC = () => {
  const { t } = useTranslation(['industry', 'common'])
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const state = useIndustrySearchStore()
  const [kw, setKw] = useState(state.keyword)

  useEffect(() => { applyDomainCssVars('industry') }, [])

  useEffect(() => {
    state.syncFromUrl(searchParams)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setSearchParams(state.toQuery(), { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.keyword, state.positionId, state.minScore, state.status,
      state.sourcePlatform, state.techDirection, state.sortBy,
      state.page, state.pageSize, setSearchParams])

  const { data, isLoading, error, refetch } = useIndustryTalents({
    keyword: state.keyword || undefined,
    position_id: state.positionId ?? undefined,
    min_score: state.minScore ?? undefined,
    status: state.status || undefined,
    source_platform: state.sourcePlatform || undefined,
    tech_direction: state.techDirection || undefined,
    sort_by: state.sortBy, page: state.page, page_size: state.pageSize,
  })

  const { data: positions } = useIndustryPositions('open')
  const { data: directions } = useTechDirectionOptions()
  const directionOptionsForFilter = (directions || []).map(d => ({ value: d.code, label: d.name }))

  if (error) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder title={t('industry:detail.loadFailed')} description={error.message || t('industry:detail.loadFailedDescription')}
          action={{ label: t('common:actions.retry'), onClick: () => refetch() }} />
      </div>
    )
  }

  const items = data?.items || []
  const total = data?.total || 0
  const openPositions = positions || []
  const totalCandidates = openPositions.reduce((s, p) => s + (p.candidate_count || 0), 0)
  // Only include positions that actually have candidates when computing the average —
  // empty positions return avg_match_score=null, which would drag the average down to 0
  const scoredPositions = openPositions.filter(p => p.candidate_count > 0 && p.avg_match_score != null)
  const avgScore = scoredPositions.length > 0
    ? Math.round(scoredPositions.reduce((s, p) => s + (p.avg_match_score || 0), 0) / scoredPositions.length) : 0

  const handlePositionClick = (positionId: number | null) => {
    state.setFilter('positionId', positionId)
    state.setFilter('page', 1)
    if (!browseMode && positionId !== null) navigate('/industry/search')
  }

  const hasFilters = state.keyword || state.positionId || state.minScore ||
    state.status || state.sourcePlatform || state.techDirection

  // Browse mode is route-driven: /industry/search = full search page,
  // /industry = clean homepage. This matches the open-source domain pattern.
  const browseMode = window.location.pathname === '/industry/search'

  const enterBrowse = () => {
    navigate('/industry/search')
  }
  const exitBrowse = () => {
    setKw('')
    state.resetFilters()
    navigate('/industry')
  }

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {/* ═══ Hero Section — homepage only ═══ */}
      {!browseMode && (
      <div style={{
        background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
        padding: '64px 32px 48px', color: '#fff', position: 'relative', overflow: 'hidden', textAlign: 'center',
      }}>
        {/* Dot pattern overlay */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.06,
          backgroundImage: 'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }} />
        <div style={{ position: 'relative', zIndex: 1, maxWidth: 880, margin: '0 auto' }}>
          <Title style={{
            margin: 0, marginBottom: 12, color: '#fff', fontWeight: 800,
            fontSize: 'clamp(26px, 4vw, 40px)', letterSpacing: '-0.5px',
          }}>
            {t('industry:home.title')}
          </Title>
          <Paragraph style={{
            margin: 0, marginBottom: 32, color: 'rgba(255,255,255,0.85)', fontSize: 15,
          }}>
            {t('industry:home.subtitle')}
          </Paragraph>
          <Input.Search
            placeholder={t('industry:search.keywordPlaceholder')}
            size="large"
            value={kw}
            onChange={e => { setKw(e.target.value); if (!e.target.value) state.setFilter('keyword', '') }}
            onSearch={v => {
              state.setFilter('keyword', v.trim())
              if (!browseMode && v.trim()) navigate('/industry/search')
            }}
            enterButton={<span style={{ fontWeight: 500 }}><SearchOutlined /> {t('industry:search.searchButton')}</span>}
            style={{ width: '100%', margin: '0 auto' }}
            allowClear
          />
          {/* Quick position tags */}
          {openPositions.length > 0 && (
            <div style={{ marginTop: 20, display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 8 }}>
              {openPositions.slice(0, 5).map(p => (
                <Tag key={p.position_id} onClick={() => handlePositionClick(p.position_id)} style={{
                  cursor: 'pointer', background: 'rgba(255,255,255,0.15)',
                  border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.9)',
                  borderRadius: 16, padding: '2px 12px', fontSize: 12,
                }}>
                  {p.title}
                </Tag>
              ))}
            </div>
          )}
        </div>
      </div>
      )}

      {/* ═══ Stats — homepage only ═══ */}
      {!browseMode && (
      <Row gutter={[16, 16]} style={{ maxWidth: 1200, margin: '24px auto 24px', padding: '0 32px' }}>
        {[
          { title: t('industry:stats.openPositions'), value: openPositions.length, icon: <TrophyOutlined />, link: undefined },
          { title: t('industry:stats.totalCandidates'), value: totalCandidates, icon: <TeamOutlined />, link: undefined },
          { title: t('industry:stats.currentResults'), value: total, icon: <UserOutlined />, link: undefined },
          { title: t('industry:stats.avgMatch'), value: avgScore ? formatScore(avgScore) : '—', icon: <StarOutlined />, link: undefined },
        ].map(s => (
          <Col xs={12} sm={6} key={s.title}>
            <Card className="domain-card" size="small" styles={{ body: { padding: '16px 20px' } }}>
              <Statistic
                title={<Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{s.title}</Text>}
                value={s.value}
                prefix={<span style={{ color: 'var(--domain-badge-bg, #6B46C1)' }}>{s.icon}</span>}
                valueStyle={{ color: 'var(--domain-badge-bg, #6B46C1)', fontSize: 24, fontWeight: 700 }}
              />
            </Card>
          </Col>
        ))}
      </Row>
      )}

      {/* ═══ Main ═══ */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: browseMode ? '88px 32px 80px' : '0 32px 64px' }}>

      {browseMode ? (
        /* ── Search page: single-column full-width (matches open-source pattern) ── */
        <>
          {/* Title bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Title level={3} style={{ margin: 0 }}>{t('industry:search.title')}</Title>
            <Button type="link" onClick={exitBrowse} style={{ fontSize: 14, padding: 0 }}>
              {t('industry:search.backToHome')}
            </Button>
          </div>

          {/* Search + Filter card (full width, top) */}
          <Card className="domain-card" style={{ marginBottom: 16, borderRadius: 12 }} styles={{ body: { padding: 20 } }}>
            <Input.Search
              placeholder={t('industry:search.keywordPlaceholder')}
              size="large"
              value={kw}
              onChange={e => { setKw(e.target.value); if (!e.target.value) state.setFilter('keyword', '') }}
              onSearch={v => state.setFilter('keyword', v.trim())}
              enterButton={<span style={{ fontWeight: 500 }}><SearchOutlined /> {t('industry:search.searchButton')}</span>}
              style={{ width: '100%', marginBottom: 16 }}
              allowClear
            />
            <Row gutter={[12, 12]}>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select placeholder={t('industry:filter.position')} style={{ width: '100%' }}
                  value={state.positionId ?? undefined}
                  onChange={v => { state.setFilter('positionId', v ?? null); state.setFilter('page', 1) }}
                  options={openPositions.map(p => ({ value: p.position_id, label: `${p.title} (${p.candidate_count})` }))}
                  allowClear showSearch optionFilterProp="label" />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select placeholder={t('industry:filter.minScore')} style={{ width: '100%' }}
                  value={state.minScore ?? 0}
                  onChange={v => { state.setFilter('minScore', v === 0 ? null : v); state.setFilter('page', 1) }}
                  options={minScoreOptions()} />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select placeholder={t('industry:filter.status')} style={{ width: '100%' }}
                  value={state.status || undefined}
                  onChange={v => { state.setFilter('status', v || ''); state.setFilter('page', 1) }}
                  options={candidateStatusOptions()} allowClear />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select placeholder={t('industry:filter.sourcePlatform')} style={{ width: '100%' }}
                  value={state.sourcePlatform || undefined}
                  onChange={v => { state.setFilter('sourcePlatform', v || ''); state.setFilter('page', 1) }}
                  options={sourcePlatformOptions()} allowClear />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select placeholder={t('industry:filter.techDirection')} style={{ width: '100%' }}
                  value={state.techDirection || undefined}
                  onChange={v => { state.setFilter('techDirection', v || ''); state.setFilter('page', 1) }}
                  options={directionOptionsForFilter} allowClear showSearch optionFilterProp="label" />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Select style={{ width: '100%' }}
                  value={state.sortBy}
                  onChange={v => state.setFilter('sortBy', v)}
                  options={industrySortOptions()} />
              </Col>
              <Col xs={24} sm={12} md={8} lg={6}>
                <Button icon={<ClearOutlined />} onClick={() => { setKw(''); state.resetFilters() }} block>
                  {t('industry:filter.clearAll')}
                </Button>
              </Col>
            </Row>
          </Card>

          {/* Results toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Text style={{ fontSize: 14 }}>
              {t('industry:results.totalBefore')}<Text strong>{total}</Text>{t('industry:results.totalAfter')}
              {hasFilters && t('industry:results.filtered')}
            </Text>
          </div>

          {/* Results grid */}
          <Spin spinning={isLoading}>
            {items.length === 0 && !isLoading ? (
              <Card className="domain-card" style={{ borderRadius: 12 }}>
                <EmptyPlaceholder
                  title={t('industry:results.emptyTitle')}
                  description={t('industry:results.emptyDescription')}
                  action={{ label: t('industry:results.clearAllFilters'), onClick: () => { setKw(''); state.resetFilters() } }}
                />
              </Card>
            ) : (
              <>
                <Row gutter={[16, 16]}>
                  {items.map(item => (
                    <Col xs={24} sm={12} lg={8} key={item.talent_id}>
                      <IndustryTalentCard talent={item} />
                    </Col>
                  ))}
                </Row>
                <div style={{ textAlign: 'center', marginTop: 24 }}>
                  <Pagination
                    current={state.page} total={total} pageSize={state.pageSize}
                    onChange={p => state.setFilter('page', p)}
                    showTotal={count => t('industry:results.paginationTotal', { count })}
                  />
                </div>
              </>
            )}
          </Spin>
        </>
      ) : (
        /* ── Homepage: sidebar + recommended cards ── */
        <Row gutter={[24, 24]}>
          {/* Left: Position sidebar */}
          <Col xs={24} sm={8} md={7} lg={6}>
            <PositionSidebar
              positions={openPositions}
              activePositionId={state.positionId}
              onPositionClick={handlePositionClick}
              state={state}
              showFilters={false}
            />
          </Col>

          {/* Right: Recommended candidates */}
          <Col xs={24} sm={16} md={17} lg={18}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Title level={4} style={{ margin: 0 }}>
                <FireOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
                {t('industry:home.recommended')}
              </Title>
              <Button type="link" onClick={enterBrowse} style={{ fontSize: 14, padding: 0 }}>
                {t('industry:home.viewAll')}
              </Button>
            </div>

            <Spin spinning={isLoading}>
              <Row gutter={[16, 16]}>
                {items.map(item => (
                  <Col xs={24} sm={12} lg={8} key={item.talent_id}>
                    <IndustryTalentCard talent={item} />
                  </Col>
                ))}
              </Row>
            </Spin>
          </Col>
        </Row>
      )}
      </div>
    </div>
  )
}

// ═══ Position Sidebar Component ═══

const PositionSidebar: React.FC<{
  positions: Array<{
    position_id: number; title: string; department: string | null
    candidate_count: number; avg_match_score: number | null; status: string
  }>
  activePositionId: number | null
  onPositionClick: (id: number | null) => void
  state: IndustrySearchState
  showFilters?: boolean
}> = ({ positions, activePositionId, onPositionClick, state, showFilters = true }) => {
  const { t } = useTranslation('industry')
  const { data: directions } = useTechDirectionOptions()
  const directionOptions = (directions || []).map(d => ({ value: d.code, label: d.name }))

  return (
    <div style={{ position: 'sticky', top: 80, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Positions */}
      <Card className="domain-card" size="small" style={{ borderRadius: 12 }} title={
        <span style={{ fontSize: 14, fontWeight: 600 }}>
          <TrophyOutlined style={{ marginRight: 6, color: 'var(--domain-badge-bg, #6B46C1)' }} />
          {t('sidebar.positionsTitle')}
        </span>
      }>
        {positions.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 13 }}>{t('sidebar.noPositions')}</Text>
        ) : (
          <>
            <PositionItem
              title={t('sidebar.allCandidates')} count={positions.reduce((s, p) => s + p.candidate_count, 0)}
              active={activePositionId === null} onClick={() => onPositionClick(null)}
            />
            {positions.map(p => (
              <PositionItem
                key={p.position_id} title={p.title} department={p.department}
                count={p.candidate_count} avgScore={p.avg_match_score}
                active={activePositionId === p.position_id}
                onClick={() => onPositionClick(p.position_id)}
              />
            ))}
          </>
        )}
      </Card>

      {/* Filters — only in browse mode */}
      {showFilters && (
        <Card className="domain-card" size="small" style={{ borderRadius: 12 }} title={
          <span style={{ fontSize: 14, fontWeight: 600 }}>{t('sidebar.filters')}</span>
        }>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Select placeholder={t('filter.minScore')} size="small" style={{ width: '100%' }}
              value={state.minScore ?? 0}
              onChange={v => state.setFilter('minScore', v === 0 ? null : v)}
              options={minScoreOptions()} />
            <Select placeholder={t('filter.status')} size="small" style={{ width: '100%' }}
              value={state.status || undefined}
              onChange={v => state.setFilter('status', v || '')}
              options={candidateStatusOptions()} allowClear />
            <Select placeholder={t('filter.sourcePlatform')} size="small" style={{ width: '100%' }}
              value={state.sourcePlatform || undefined}
              onChange={v => state.setFilter('sourcePlatform', v || '')}
              options={sourcePlatformOptions()} allowClear />
            <Select placeholder={t('filter.techDirection')} size="small" style={{ width: '100%' }}
              value={state.techDirection || undefined}
              onChange={v => state.setFilter('techDirection', v || '')}
              options={directionOptions} allowClear showSearch optionFilterProp="label" />
            <Select size="small" style={{ width: '100%' }}
              value={state.sortBy} onChange={v => state.setFilter('sortBy', v)}
              options={industrySortOptions()} />
            <Button size="small" icon={<ClearOutlined />} onClick={() => state.resetFilters()}>
              {t('filter.clearAll')}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}

const PositionItem: React.FC<{
  title: string; department?: string | null; count: number
  avgScore?: number | null; active: boolean; onClick: () => void
}> = ({ title, department, count, avgScore, active, onClick }) => {
  const { t } = useTranslation('industry')
  return (
  <div onClick={onClick} style={{
    padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
    background: active ? 'var(--domain-light-bg, #FAF5FF)' : 'transparent',
    borderLeft: active ? '3px solid var(--domain-badge-bg, #6B46C1)' : '3px solid transparent',
    transition: 'all 0.15s',
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Text style={{
        fontSize: 13, fontWeight: active ? 600 : 400,
        color: active ? 'var(--domain-badge-bg, #6B46C1)' : '#333',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
      }}>
        {title}
      </Text>
      <Badge count={count} style={{
        backgroundColor: 'var(--domain-badge-bg, #6B46C1)', marginLeft: 6,
      }} />
    </div>
    {(department || avgScore != null) && (
      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
        {department && <span>{department}</span>}
        {department && avgScore != null && <span> · </span>}
        {avgScore != null && <span>{t('sidebar.avgMatch', { score: formatScore(avgScore) })}</span>}
      </div>
    )}
  </div>
  )
}

export default IndustrySearchPage
