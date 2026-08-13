import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import IndustryTalentCard from './components/industry-talent-card'
import {
  CANDIDATE_STATUS_OPTIONS, MIN_SCORE_OPTIONS, SOURCE_PLATFORM_OPTIONS, INDUSTRY_SORT_OPTIONS,
  formatScore,
} from './constants/industry-config'

const { Text, Title, Paragraph } = Typography

const IndustrySearchPage: React.FC = () => {
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

  if (error) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder title="加载失败" description={error.message || '请稍后重试'}
          action={{ label: '重试', onClick: () => refetch() }} />
      </div>
    )
  }

  const items = data?.items || []
  const total = data?.total || 0
  const openPositions = positions || []
  const totalCandidates = openPositions.reduce((s, p) => s + (p.candidate_count || 0), 0)
  const avgScore = openPositions.length > 0
    ? Math.round(openPositions.reduce((s, p) => s + (p.avg_match_score || 0), 0) / openPositions.length) : 0

  const handlePositionClick = (positionId: number | null) => {
    state.setFilter('positionId', positionId)
    state.setFilter('page', 1)
  }

  const hasFilters = state.keyword || state.positionId || state.minScore ||
    state.status || state.sourcePlatform || state.techDirection

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {/* ═══ Hero Section ═══ */}
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
            全球行业顶尖人才库
          </Title>
          <Paragraph style={{
            margin: 0, marginBottom: 32, color: 'rgba(255,255,255,0.85)', fontSize: 15,
          }}>
            对准高端精英、关键稀缺岗位，智能发现行业优秀顶尖人才，加速全球人才供应
          </Paragraph>
          <Input.Search
            placeholder="搜索姓名 / 公司 / 职位..."
            size="large"
            value={kw}
            onChange={e => { setKw(e.target.value); if (!e.target.value) state.setFilter('keyword', '') }}
            onSearch={v => state.setFilter('keyword', v.trim())}
            enterButton={<span style={{ fontWeight: 500 }}><SearchOutlined /> 搜索</span>}
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

      {/* ═══ Stats ═══ */}
      <Row gutter={[16, 16]} style={{ maxWidth: 1200, margin: '24px auto 24px', padding: '0 32px' }}>
        {[
          { title: '在招岗位', value: openPositions.length, icon: <TrophyOutlined />, link: undefined },
          { title: '候选人总数', value: totalCandidates, icon: <TeamOutlined />, link: undefined },
          { title: '当前结果', value: total, icon: <UserOutlined />, link: undefined },
          { title: '平均匹配', value: avgScore ? formatScore(avgScore) : '—', icon: <StarOutlined />, link: undefined },
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

      {/* ═══ Main: Position sidebar + Talent list ═══ */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 32px 64px' }}>
        <Row gutter={[24, 24]}>
          {/* Left: Position sidebar + filters */}
          <Col xs={24} sm={8} md={7} lg={6}>
            <PositionSidebar
              positions={openPositions}
              activePositionId={state.positionId}
              onPositionClick={handlePositionClick}
              state={state}
            />
          </Col>

          {/* Right: Talent cards */}
          <Col xs={24} sm={16} md={17} lg={18}>
            {/* Section header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Title level={4} style={{ margin: 0 }}>
                <FireOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
                {hasFilters ? `搜索结果（${total} 人）` : '推荐候选人'}
              </Title>
              <Button type="link" onClick={() => state.resetFilters()}
                style={{ fontSize: 14, padding: 0, display: hasFilters ? 'inline-block' : 'none' }}>
                清除筛选，查看全部 ↓
              </Button>
            </div>

            <Spin spinning={isLoading}>
              {items.length === 0 && !isLoading ? (
                <Card className="domain-card" style={{ borderRadius: 12 }}>
                  <EmptyPlaceholder
                    title="未找到匹配的候选人"
                    description="试试调整关键词或放宽筛选条件；也可以先在系统配置中导入人才数据"
                    action={{ label: '清除全部筛选', onClick: () => { setKw(''); state.resetFilters() } }}
                  />
                </Card>
              ) : (
                <>
                  <Row gutter={[16, 16]}>
                    {items.map(t => (
                      <Col xs={24} sm={12} lg={8} key={t.talent_id}>
                        <IndustryTalentCard talent={t} />
                      </Col>
                    ))}
                  </Row>
                  <div style={{ textAlign: 'center', marginTop: 32 }}>
                    <Pagination
                      current={state.page} total={total} pageSize={state.pageSize}
                      onChange={p => state.setFilter('page', p)}
                      showTotal={t => `共 ${t} 人`}
                    />
                  </div>
                </>
              )}
            </Spin>
          </Col>
        </Row>
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
}> = ({ positions, activePositionId, onPositionClick, state }) => {
  const { data: directions } = useTechDirectionOptions()
  const directionOptions = (directions || []).map(d => ({ value: d.code, label: d.name }))

  return (
    <div style={{ position: 'sticky', top: 80, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Positions */}
      <Card className="domain-card" size="small" style={{ borderRadius: 12 }} title={
        <span style={{ fontSize: 14, fontWeight: 600 }}>
          <TrophyOutlined style={{ marginRight: 6, color: 'var(--domain-badge-bg, #6B46C1)' }} />
          在招岗位
        </span>
      }>
        {positions.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 13 }}>暂无在招岗位</Text>
        ) : (
          <>
            <PositionItem
              title="全部候选人" count={positions.reduce((s, p) => s + p.candidate_count, 0)}
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

      {/* Filters */}
      <Card className="domain-card" size="small" style={{ borderRadius: 12 }} title={
        <span style={{ fontSize: 14, fontWeight: 600 }}>筛选条件</span>
      }>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Select placeholder="最低匹配分" size="small" style={{ width: '100%' }}
            value={state.minScore ?? 0}
            onChange={v => state.setFilter('minScore', v === 0 ? null : v)}
            options={MIN_SCORE_OPTIONS} />
          <Select placeholder="候选人状态" size="small" style={{ width: '100%' }}
            value={state.status || undefined}
            onChange={v => state.setFilter('status', v || '')}
            options={CANDIDATE_STATUS_OPTIONS} allowClear />
          <Select placeholder="来源平台" size="small" style={{ width: '100%' }}
            value={state.sourcePlatform || undefined}
            onChange={v => state.setFilter('sourcePlatform', v || '')}
            options={SOURCE_PLATFORM_OPTIONS} allowClear />
          <Select placeholder="技术方向" size="small" style={{ width: '100%' }}
            value={state.techDirection || undefined}
            onChange={v => state.setFilter('techDirection', v || '')}
            options={directionOptions} allowClear showSearch optionFilterProp="label" />
          <Select size="small" style={{ width: '100%' }}
            value={state.sortBy} onChange={v => state.setFilter('sortBy', v)}
            options={INDUSTRY_SORT_OPTIONS} />
          <Button size="small" icon={<ClearOutlined />} onClick={() => state.resetFilters()}>
            清除全部
          </Button>
        </div>
      </Card>
    </div>
  )
}

const PositionItem: React.FC<{
  title: string; department?: string | null; count: number
  avgScore?: number | null; active: boolean; onClick: () => void
}> = ({ title, department, count, avgScore, active, onClick }) => (
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
        {avgScore != null && <span>均匹配 {formatScore(avgScore)}</span>}
      </div>
    )}
  </div>
)

export default IndustrySearchPage
