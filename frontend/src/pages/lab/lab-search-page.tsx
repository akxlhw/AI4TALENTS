import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Row, Col, Card, Pagination, Typography, Spin } from 'antd'
import { useLabTalents } from '../../hooks/useLabQueries'
import { useLabSearchStore } from '../../stores/labSearchStore'
import { applyDomainCssVars } from '../../theme'
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
    <div style={{ padding: 24, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <BreadcrumbNav items={[{ label: '实验室', path: '/lab' }, { label: '搜索' }]} />
      <LabSearchFilter state={state} />

      <Spin spinning={isLoading}>
        <Card style={{ borderRadius: 12 }}>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text type="secondary">共 {total} 人</Text>
          </div>

          {items.length === 0 && !isLoading ? (
            <EmptyPlaceholder
              title="未找到匹配的人才"
              description="尝试调整筛选条件"
              action={{ label: '清除筛选', onClick: () => state.resetFilters() }}
            />
          ) : (
            <>
              <Row gutter={[16, 16]}>
                {items.map((t) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
                    <LabTalentCard talent={t} />
                  </Col>
                ))}
              </Row>
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <Pagination
                  current={state.page}
                  total={total}
                  pageSize={state.pageSize}
                  onChange={(p) => state.setFilter('page', p)}
                  showTotal={(t) => `共 ${t} 人`}
                />
              </div>
            </>
          )}
        </Card>
      </Spin>
    </div>
  )
}

export default LabSearchPage
