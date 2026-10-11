import { Button, Col, Empty, Pagination, Row, Spin } from 'antd'
import { useTranslation } from 'react-i18next'
import '@/i18n/namespaces/open-source'
import type { OSDeveloper } from '../../../types'
import OsDeveloperCard from './os-developer-card'

interface OsSearchResultsProps {
  loading: boolean
  searchError: string | null
  developers: OSDeveloper[]
  total: number
  page: number
  pageSize: number
  favoriteIds: Set<number>
  selectedIds: Set<number>
  onRetry: () => void
  onClearFilters: () => void
  onPageChange: (page: number) => void
  onToggleFavorite: (developerId: number) => void
  onToggleSelect: (developerId: number) => void
}

const OsSearchResults: React.FC<OsSearchResultsProps> = ({
  loading,
  searchError,
  developers,
  total,
  page,
  pageSize,
  favoriteIds,
  selectedIds,
  onRetry,
  onClearFilters,
  onPageChange,
  onToggleFavorite,
  onToggleSelect,
}) => {
  const { t } = useTranslation(['openSource', 'common'])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (searchError) {
    return (
      <Empty description={searchError} image={Empty.PRESENTED_IMAGE_SIMPLE}>
        <Button type="primary" onClick={onRetry}>
          {t('common:actions.retry')}
        </Button>
      </Empty>
    )
  }

  if (developers.length === 0) {
    return (
      <Empty description={t('openSource:search.noResults')}>
        <Button type="primary" onClick={onClearFilters}>
          {t('openSource:search.clearFilters')}
        </Button>
      </Empty>
    )
  }

  return (
    <>
      <Row gutter={[16, 16]}>
        {developers.map(dev => (
          <Col xs={24} sm={12} lg={8} key={dev.developer_id}>
            <OsDeveloperCard
              developer={dev}
              selected={selectedIds.has(dev.developer_id)}
              isFavorite={favoriteIds.has(dev.developer_id)}
              onToggleFavorite={onToggleFavorite}
              onToggleSelect={onToggleSelect}
            />
          </Col>
        ))}
      </Row>

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          onChange={onPageChange}
          showSizeChanger={false}
        />
      </div>
    </>
  )
}

export default OsSearchResults
