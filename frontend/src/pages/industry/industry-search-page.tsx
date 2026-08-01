import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Col, Pagination, Row, Spin, Typography, Card, Statistic, Input, Badge, Select, Button } from 'antd'
import { BuildOutlined, SearchOutlined, TeamOutlined, TrophyOutlined, UserOutlined, ClearOutlined } from '@ant-design/icons'
import { useIndustryTalents, useIndustryPositions, useTechDirectionOptions } from '../../hooks/useIndustryQueries'
import { useIndustrySearchStore } from '../../stores/industrySearchStore'
import type { IndustrySearchState } from '../../stores/industrySearchStore'
import { applyDomainCssVars } from '../../theme'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import IndustryTalentCard from './components/industry-talent-card'
import {
  CANDIDATE_STATUS_OPTIONS,
  MIN_SCORE_OPTIONS,
  SOURCE_PLATFORM_OPTIONS,
  INDUSTRY_SORT_OPTIONS,
} from './constants/industry-config'

const { Text, Title } = Typography

const IndustrySearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const state = useIndustrySearchStore()
  const [kw, setKw] = useState(state.keyword)

  useEffect(() => {
    applyDomainCssVars('industry')
  }, [])

  useEffect(() => {
    state.syncFromUrl(searchParams)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setSearchParams(state.toQuery(), { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    state.keyword,
    state.positionId,
    state.minScore,
    state.status,
    state.sourcePlatform,
    state.techDirection,
    state.sortBy,
    state.page,
    state.pageSize,
    setSearchParams,
  ])

  const { data, isLoading, error, refetch } = useIndustryTalents({
    keyword: state.keyword || undefined,
    position_id: state.positionId ?? undefined,
    min_score: state.minScore ?? undefined,
    status: state.status || undefined,
    source_platform: state.sourcePlatform || undefined,
    tech_direction: state.techDirection || undefined,
    sort_by: state.sortBy,
    page: state.page,
    page_size: state.pageSize,
  })

  const { data: positions } = useIndustryPositions('open')

  if (error) {
    return (
      <div style={{ paddingTop: 64 }}>
        <EmptyPlaceholder
          title="加载失败"
          description={error.message || '请稍后重试'}
          action={{ label: '重试', onClick: () => refetch() }}
        />
      </div>
    )
  }

  const items = data?.items || []
  const total = data?.total || 0
  const openPositions = positions || []
  const totalCandidates = openPositions.reduce((s, p) => s + (p.candidate_count || 0), 0)
  const avgScore = openPositions.length > 0
    ? Math.round(openPositions.reduce((s, p) => s + (p.avg_match_score || 0), 0) / openPositions.length)
    : 0

  // Position sidebar click → filter by position
  const handlePositionClick = (positionId: number | null) => {
    state.setFilter('positionId', positionId)
    state.setFilter('page', 1)
  }

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {/* ========= Hero: Big Search Engine ========= */}
      <div
        style={{
          background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
          padding: '40px 24px 32px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative rings */}
        <div style={{
          position: 'absolute', right: -60, top: -80, width: 260, height: 260,
          borderRadius: '50%', border: '40px solid rgba(255,255,255,0.06)', pointerEvents: 'none',
        }} />
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center', position: 'relative' }}>
          <Title style={{ color: '#fff', fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
            <BuildOutlined style={{ marginRight: 10 }} />
            行业人才库
          </Title>
          <Text style={{ color: 'rgba(255,255,255,0.72)', fontSize: 14, display: 'block', marginBottom: 24 }}>
            面向按岗招聘的行业候选人 · 数据来自脉脉 / LinkedIn 寻猎
          </Text>
          {/* Big search bar */}
          <Input.Search
            size="large"
            placeholder="搜索姓名 / 公司 / 职位..."
            value={kw}
            onChange={e => {
              setKw(e.target.value)
              if (!e.target.value) state.setFilter('keyword', '')
            }}
            onSearch={v => state.setFilter('keyword', v.trim())}
            enterButton={<span><SearchOutlined /> 搜索</span>}
            allowClear
            style={{ maxWidth: 600 }}
          />
        </div>
      </div>

      {/* ========= Summary Stats ========= */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 24px 0' }}>
        <Row gutter={[12, 12]}>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic title="在招岗位" value={openPositions.length} prefix={<TrophyOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic title="候选人总数" value={totalCandidates} prefix={<TeamOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic title="当前结果" value={total} prefix={<UserOutlined />} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small" style={{ borderRadius: 10 }}>
              <Statistic title="平均匹配分" value={avgScore || '—'} suffix={avgScore ? '分' : ''} />
            </Card>
          </Col>
        </Row>
      </div>

      {/* ========= Main: Position sidebar + Talent list ========= */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 24px 48px' }}>
        <Row gutter={[16, 16]}>
          {/* Left: Position list */}
          <Col xs={24} sm={8} md={6} lg={5}>
            <PositionSidebar
              positions={openPositions}
              activePositionId={state.positionId}
              onPositionClick={handlePositionClick}
              state={state}
            />
          </Col>

          {/* Right: Talent cards */}
          <Col xs={24} sm={16} md={18} lg={19}>
            <Spin spinning={isLoading}>
              {items.length === 0 && !isLoading ? (
                <EmptyPlaceholder
                  title="未找到匹配的候选人"
                  description="试试调整关键词或放宽筛选条件；也可以先在系统配置中导入人才数据"
                  action={{ label: '清除全部筛选', onClick: () => { setKw(''); state.resetFilters() }}}
                />
              ) : (
                <>
                  <Row gutter={[16, 16]}>
                    {items.map(t => (
                      <Col xs={24} sm={12} md={8} key={t.talent_id}>
                        <IndustryTalentCard talent={t} />
                      </Col>
                    ))}
                  </Row>
                  <div style={{ textAlign: 'center', marginTop: 32 }}>
                    <Pagination
                      current={state.page}
                      total={total}
                      pageSize={state.pageSize}
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

// ========= Position Sidebar Component =========

const PositionSidebar: React.FC<{
  positions: Array<{
    position_id: number
    title: string
    department: string | null
    candidate_count: number
    avg_match_score: number | null
    status: string
  }>
  activePositionId: number | null
  onPositionClick: (id: number | null) => void
  state: IndustrySearchState
}> = ({ positions, activePositionId, onPositionClick, state }) => {
  const { data: directions } = useTechDirectionOptions()
  const directionOptions = (directions || []).map(d => ({ value: d.code, label: d.name }))

  return (
    <div style={{ position: 'sticky', top: 80 }}>
      {/* Position list */}
      <Card
        size="small"
        style={{ borderRadius: 10, marginBottom: 12 }}
        title={<span style={{ fontSize: 13 }}>岗位</span>}
      >
        {positions.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 12 }}>暂无在招岗位</Text>
        ) : (
          <>
            {/* "All positions" option */}
            <div
              onClick={() => onPositionClick(null)}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                cursor: 'pointer',
                marginBottom: 4,
                background: activePositionId === null ? 'var(--domain-light-bg, #FAF5FF)' : 'transparent',
                fontWeight: activePositionId === null ? 600 : 400,
                color: activePositionId === null ? 'var(--domain-badge-bg, #6B46C1)' : '#333',
                fontSize: 13,
                transition: 'background 0.15s',
              }}
            >
              全部候选人
            </div>
            {positions.map(p => (
              <div
                key={p.position_id}
                onClick={() => onPositionClick(p.position_id)}
                style={{
                  padding: '6px 10px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  marginBottom: 4,
                  background: activePositionId === p.position_id ? 'var(--domain-light-bg, #FAF5FF)' : 'transparent',
                  fontWeight: activePositionId === p.position_id ? 600 : 400,
                  color: activePositionId === p.position_id ? 'var(--domain-badge-bg, #6B46C1)' : '#333',
                  fontSize: 13,
                  transition: 'background 0.15s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                    {p.title}
                  </span>
                  <Badge count={p.candidate_count} style={{ backgroundColor: 'var(--domain-badge-bg, #6B46C1)', marginLeft: 6 }} />
                </div>
                {p.avg_match_score != null && (
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    均分 {Math.round(p.avg_match_score)}
                  </Text>
                )}
              </div>
            ))}
          </>
        )}
      </Card>

      {/* Compact filters */}
      <Card size="small" style={{ borderRadius: 10 }} title={<span style={{ fontSize: 13 }}>筛选</span>}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Select
            placeholder="最低匹配分"
            size="small"
            style={{ width: '100%' }}
            value={state.minScore ?? 0}
            onChange={v => state.setFilter('minScore', v === 0 ? null : v)}
            options={MIN_SCORE_OPTIONS}
          />
          <Select
            placeholder="候选人状态"
            size="small"
            style={{ width: '100%' }}
            value={state.status || undefined}
            onChange={v => state.setFilter('status', v || '')}
            options={CANDIDATE_STATUS_OPTIONS}
            allowClear
          />
          <Select
            placeholder="来源平台"
            size="small"
            style={{ width: '100%' }}
            value={state.sourcePlatform || undefined}
            onChange={v => state.setFilter('sourcePlatform', v || '')}
            options={SOURCE_PLATFORM_OPTIONS}
            allowClear
          />
          <Select
            placeholder="技术方向"
            size="small"
            style={{ width: '100%' }}
            value={state.techDirection || undefined}
            onChange={v => state.setFilter('techDirection', v || '')}
            options={directionOptions}
            allowClear
            showSearch
            optionFilterProp="label"
          />
          <Select
            size="small"
            style={{ width: '100%' }}
            value={state.sortBy}
            onChange={v => state.setFilter('sortBy', v)}
            options={INDUSTRY_SORT_OPTIONS}
          />
          <Button
            size="small"
            icon={<ClearOutlined />}
            onClick={() => state.resetFilters()}
          >
            清除全部
          </Button>
        </div>
      </Card>
    </div>
  )
}

export default IndustrySearchPage
