import { useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Row, Col, Pagination, Typography, Spin, Breadcrumb, Tag } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import { useLabTalents, useLabProfile } from '../../hooks/useLabQueries'
import { useLabSearchStore } from '../../stores/labSearchStore'
import { applyDomainCssVars } from '../../theme'
import LabIcon from '../../components/lab-icon'
import LabSearchFilter from './components/lab-search-filter'
import LabTalentCard from './components/lab-talent-card'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'

const { Text } = Typography

const LabSearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const state = useLabSearchStore()

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  useEffect(() => {
    state.syncFromUrl(searchParams)
    // Only run once on mount to avoid loops with the URL sync effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const query = state.toQuery()
    setSearchParams(query, { replace: true })
    // State object is stable; list individual fields to avoid excessive re-syncs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    state.keyword,
    state.parentLab,
    state.labName,
    state.roleType,
    state.academicLevel,
    state.researchArea,
    state.sortBy,
    state.page,
    state.pageSize,
    state.advancedOpen,
    setSearchParams,
  ])

  const { data: profile } = useLabProfile(state.parentLab || undefined)

  const { data, isLoading, error, refetch } = useLabTalents({
    keyword: state.keyword || undefined,
    parent_lab: state.parentLab || undefined,
    lab_name: state.labName || undefined,
    role_type: state.roleType || undefined,
    academic_level: state.academicLevel || undefined,
    research_area: state.researchArea || undefined,
    sort_by: state.sortBy === 'default' ? undefined : state.sortBy,
    page: state.page,
    page_size: state.pageSize,
  })

  if (error) {
    return (
      <EmptyPlaceholder
        title="加载失败"
        description={error.message || '请稍后重试'}
        action={{ label: '重试', onClick: () => refetch() }}
      />
    )
  }

  const items = data?.items || []
  const total = data?.total || 0

  return (
    <div style={{ paddingTop: 64, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      {/* Context header — show lab profile when browsing a specific lab */}
      {state.parentLab && (
        <div
          style={{
            background: 'var(--domain-gradient, linear-gradient(135deg,#0D2B4E,#0EA5E9))',
            padding: '20px 24px 20px',
          }}
        >
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <Breadcrumb style={{ marginBottom: 12 }}>
              <Breadcrumb.Item>
                <Link to="/lab" style={{ color: 'rgba(255,255,255,0.7)' }}>
                  AI Native
                </Link>
              </Breadcrumb.Item>
              <Breadcrumb.Item>
                <span style={{ color: '#fff' }}>{state.parentLab}</span>
              </Breadcrumb.Item>
            </Breadcrumb>

            {/* Lab identity row */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 14,
                  background: 'rgba(255,255,255,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  overflow: 'hidden',
                }}
              >
                {profile?.logo_url ? (
                  <img
                    src={profile.logo_url}
                    alt=""
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <LabIcon style={{ fontSize: 28, color: '#fff' }} />
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
                  <Text style={{ color: '#fff', fontSize: 24, fontWeight: 700 }}>
                    {state.parentLab}
                  </Text>
                  {!isLoading && (
                    <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 14 }}>
                      共 {total} 人
                    </Text>
                  )}
                  {profile?.homepage && (
                    <a
                      href={profile.homepage}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        color: 'rgba(255,255,255,0.8)',
                        fontSize: 13,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      <HomeOutlined /> 官网
                    </a>
                  )}
                </div>

                {/* Description */}
                {profile?.description && (
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.85)',
                      fontSize: 13,
                      display: 'block',
                      marginTop: 6,
                      lineHeight: 1.6,
                    }}
                  >
                    {profile.description}
                  </Text>
                )}

                {/* Research focus */}
                {profile?.research_focus && (
                  <Text
                    style={{
                      color: 'rgba(255,255,255,0.65)',
                      fontSize: 12,
                      display: 'block',
                      marginTop: 4,
                    }}
                  >
                    研究领域：{profile.research_focus}
                  </Text>
                )}
              </div>
            </div>

            {/* Research directions as tags */}
            {profile?.research_directions && profile.research_directions.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 14 }}>
                {profile.research_directions.slice(0, 10).map(dir => (
                  <Tag
                    key={dir}
                    style={{
                      background: 'rgba(255,255,255,0.15)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      borderRadius: 12,
                      color: 'rgba(255,255,255,0.9)',
                      fontSize: 11,
                      margin: 0,
                      padding: '2px 10px',
                    }}
                  >
                    {dir}
                  </Tag>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      {!state.parentLab && (
        <div style={{ padding: '20px 24px 0' }}>
          <BreadcrumbNav items={[{ label: 'AI Native', path: '/lab' }, { label: '全部人才' }]} />
        </div>
      )}

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '16px 24px 48px' }}>
        <LabSearchFilter state={state} />

        <Spin spinning={isLoading}>
          {items.length === 0 && !isLoading ? (
            <EmptyPlaceholder
              title="未找到匹配的人才"
              description="尝试调整筛选条件"
              action={{ label: '清除筛选', onClick: () => state.resetFilters() }}
            />
          ) : (
            <>
              {!state.parentLab && (
                <div style={{ marginBottom: 12 }}>
                  <Text type="secondary">共 {total} 人</Text>
                </div>
              )}
              <Row gutter={[16, 16]}>
                {items.map(t => (
                  <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
                    <LabTalentCard talent={t} />
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
  )
}

export default LabSearchPage
