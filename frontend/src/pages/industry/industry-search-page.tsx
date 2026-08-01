import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Col, Pagination, Row, Spin, Typography } from 'antd'
import { BuildOutlined } from '@ant-design/icons'
import { useIndustryTalents } from '../../hooks/useIndustryQueries'
import { useIndustrySearchStore } from '../../stores/industrySearchStore'
import { applyDomainCssVars } from '../../theme'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import IndustrySearchFilter from './components/industry-search-filter'
import IndustryTalentCard from './components/industry-talent-card'

const { Text } = Typography

const IndustrySearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const state = useIndustrySearchStore()

  useEffect(() => {
    applyDomainCssVars('industry')
  }, [])

  useEffect(() => {
    state.syncFromUrl(searchParams)
    // Only run once on mount to avoid loops with the URL sync effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    setSearchParams(state.toQuery(), { replace: true })
    // State object is stable; list individual fields to avoid excessive re-syncs.
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

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {/* Domain banner — purple family, restrained like the lab banner */}
      <div
        style={{
          background: 'var(--domain-gradient, linear-gradient(135deg,#1A365D,#6B46C1))',
          padding: '28px 24px 56px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* subtle decorative rings, top-right */}
        <div
          style={{
            position: 'absolute',
            right: -60,
            top: -80,
            width: 260,
            height: 260,
            borderRadius: '50%',
            border: '40px solid rgba(255,255,255,0.06)',
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            right: 120,
            bottom: -100,
            width: 180,
            height: 180,
            borderRadius: '50%',
            border: '28px solid rgba(255,255,255,0.05)',
            pointerEvents: 'none',
          }}
        />
        <div style={{ maxWidth: 1200, margin: '0 auto', position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 13,
                background: 'rgba(255,255,255,0.14)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <BuildOutlined style={{ fontSize: 24, color: '#fff' }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
                <Text style={{ color: '#fff', fontSize: 24, fontWeight: 700, letterSpacing: 0.5 }}>
                  行业人才库
                </Text>
                {!isLoading && (
                  <Text style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14 }}>
                    共 {total} 位候选人
                  </Text>
                )}
              </div>
              <Text
                style={{
                  color: 'rgba(255,255,255,0.72)',
                  fontSize: 13,
                  display: 'block',
                  marginTop: 4,
                }}
              >
                面向按岗招聘的行业候选人 · 数据来自脉脉 / LinkedIn 寻猎
              </Text>
            </div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 24px 48px' }}>
        {/* Sticky filter bar — overlaps the banner bottom edge */}
        <div style={{ position: 'sticky', top: 72, zIndex: 20, marginTop: -32 }}>
          <IndustrySearchFilter state={state} />
        </div>

        <div style={{ marginTop: 20 }}>
          <Spin spinning={isLoading}>
            {items.length === 0 && !isLoading ? (
              <EmptyPlaceholder
                title="未找到匹配的候选人"
                description="试试调整关键词或放宽筛选条件；也可以先在系统配置中导入人才数据"
                action={{ label: '清除全部筛选', onClick: () => state.resetFilters() }}
              />
            ) : (
              <>
                <Row gutter={[16, 16]}>
                  {items.map(t => (
                    <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
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
        </div>
      </div>
    </div>
  )
}

export default IndustrySearchPage
