import { useEffect, useState } from 'react'
import { Button, Card, Col, Input, Row, Select } from 'antd'
import { ClearOutlined, SearchOutlined } from '@ant-design/icons'
import type { IndustrySearchState } from '../../../stores/industrySearchStore'
import { useIndustryPositions, useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import {
  CANDIDATE_STATUS_OPTIONS,
  INDUSTRY_SORT_OPTIONS,
  MIN_SCORE_OPTIONS,
  SOURCE_PLATFORM_OPTIONS,
} from '../constants/industry-config'

interface IndustrySearchFilterProps {
  state: IndustrySearchState
}

/**
 * Multi-dimension filter bar for /industry.
 * The parent page wraps it in a sticky container.
 */
const IndustrySearchFilter: React.FC<IndustrySearchFilterProps> = ({ state }) => {
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
            placeholder="搜索姓名 / 公司 / 职位..."
            prefix={<SearchOutlined style={{ color: '#b6c2d2' }} />}
            value={kw}
            onChange={e => {
              setKw(e.target.value)
              if (!e.target.value) state.setFilter('keyword', '')
            }}
            onSearch={v => state.setFilter('keyword', v.trim())}
            enterButton="搜索"
            allowClear
          />
        </Col>
      </Row>

      {/* Row 2: dimension filters + sort + reset */}
      <Row gutter={[12, 12]} align="middle" style={{ marginTop: 12 }}>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder="在招岗位"
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
            placeholder="最低匹配分"
            style={{ width: '100%' }}
            value={state.minScore ?? 0}
            onChange={v => state.setFilter('minScore', v === 0 ? null : v)}
            options={MIN_SCORE_OPTIONS}
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder="候选人状态"
            style={{ width: '100%' }}
            value={state.status || undefined}
            onChange={v => state.setFilter('status', v || '')}
            options={CANDIDATE_STATUS_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder="来源平台"
            style={{ width: '100%' }}
            value={state.sourcePlatform || undefined}
            onChange={v => state.setFilter('sourcePlatform', v || '')}
            options={SOURCE_PLATFORM_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Select
            placeholder="技术方向"
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
                options={INDUSTRY_SORT_OPTIONS}
              />
            </Col>
            <Col flex="none">
              <Button
                icon={<ClearOutlined />}
                onClick={() => {
                  setKw('')
                  state.resetFilters()
                }}
                title="清除全部筛选"
              >
                清除
              </Button>
            </Col>
          </Row>
        </Col>
      </Row>
    </Card>
  )
}

export default IndustrySearchFilter
