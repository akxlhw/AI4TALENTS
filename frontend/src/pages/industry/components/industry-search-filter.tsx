import { useEffect, useState } from 'react'
import { Button, Card, Col, Input, Row, Select } from 'antd'
import { ClearOutlined, SearchOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { IndustrySearchState } from '../../../stores/industrySearchStore'
import { useIndustryPositions, useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import {
  candidateStatusOptions,
  industrySortOptions,
  minScoreOptions,
  sourcePlatformOptions,
} from '../constants/industry-config'

interface IndustrySearchFilterProps {
  state: IndustrySearchState
}

/**
 * Multi-dimension filter bar for /industry.
 * The parent page wraps it in a sticky container.
 */
const IndustrySearchFilter: React.FC<IndustrySearchFilterProps> = ({ state }) => {
  const { t } = useTranslation('industry')
  const { data: positions } = useIndustryPositions('open')
  const { data: directions } = useTechDirectionOptions()

  // Keyword is applied on search-submit only (not per keystroke)
  const [kw, setKw] = useState(state.keyword)
  useEffect(() => {
    setKw(state.keyword)
  }, [state.keyword])

  const positionOptions = (positions || []).map(p => ({
    value: p.position_id,
    label: p.title,
  }))

  const directionOptions = (directions || []).map(d => ({
    value: d.code,
    label: d.name,
  }))

  return (
    <Card
      style={{ borderRadius: 12, boxShadow: '0 2px 10px rgba(26,54,93,0.05)' }}
      styles={{ body: { padding: '14px 16px' } }}
    >
      {/* Row 1: keyword search */}
      <Row gutter={[12, 12]} align="middle">
        <Col flex="auto">
          <Input.Search
            placeholder={t('search.keywordPlaceholder')}
            prefix={<SearchOutlined style={{ color: '#b6c2d2' }} />}
            value={kw}
            onChange={e => {
              setKw(e.target.value)
              if (!e.target.value) state.setFilter('keyword', '')
            }}
            onSearch={v => state.setFilter('keyword', v.trim())}
            enterButton={t('search.searchButton')}
            allowClear
          />
        </Col>
      </Row>

      {/* Row 2: dimension filters + sort + reset */}
      <Row gutter={[12, 12]} align="middle" style={{ marginTop: 12 }}>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder={t('filter.position')}
            style={{ width: '100%' }}
            value={state.positionId ?? undefined}
            onChange={v => state.setFilter('positionId', v ?? null)}
            options={positionOptions}
            allowClear
            showSearch
            optionFilterProp="label"
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder={t('filter.minScore')}
            style={{ width: '100%' }}
            value={state.minScore ?? 0}
            onChange={v => state.setFilter('minScore', v === 0 ? null : v)}
            options={minScoreOptions()}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder={t('filter.status')}
            style={{ width: '100%' }}
            value={state.status || undefined}
            onChange={v => state.setFilter('status', v || '')}
            options={candidateStatusOptions()}
            allowClear
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder={t('filter.sourcePlatform')}
            style={{ width: '100%' }}
            value={state.sourcePlatform || undefined}
            onChange={v => state.setFilter('sourcePlatform', v || '')}
            options={sourcePlatformOptions()}
            allowClear
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder={t('filter.techDirection')}
            style={{ width: '100%' }}
            value={state.techDirection || undefined}
            onChange={v => state.setFilter('techDirection', v || '')}
            options={directionOptions}
            allowClear
            showSearch
            optionFilterProp="label"
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Row gutter={8}>
            <Col flex="auto">
              <Select
                style={{ width: '100%' }}
                value={state.sortBy}
                onChange={v => state.setFilter('sortBy', v)}
                options={industrySortOptions()}
              />
            </Col>
            <Col flex="none">
              <Button
                icon={<ClearOutlined />}
                onClick={() => {
                  setKw('')
                  state.resetFilters()
                }}
                title={t('results.clearAllFilters')}
              >
                {t('filter.clearAll')}
              </Button>
            </Col>
          </Row>
        </Col>
      </Row>
    </Card>
  )
}

export default IndustrySearchFilter
