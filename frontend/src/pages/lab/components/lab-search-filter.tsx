import { Card, Row, Col, Input, Select, Button } from 'antd'
import { SearchOutlined, FilterOutlined, ReloadOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { LabSearchState } from '../../../stores/labSearchStore'
import { useRoleFilterOptions, LEVEL_KEYS } from '../constants/lab-role'
import '../../../i18n/namespaces/lab'

interface LabSearchFilterProps {
  state: LabSearchState
}

const SORT_OPTIONS = [
  { labelKey: 'search.sort.default', value: 'default' },
  { labelKey: 'search.sort.nameAsc', value: 'name_asc' },
  { labelKey: 'search.sort.cohortDesc', value: 'cohort_desc' },
  { labelKey: 'search.sort.createdDesc', value: 'created_desc' },
]

const LabSearchFilter: React.FC<LabSearchFilterProps> = ({ state }) => {
  const { t } = useTranslation('lab')
  const roleOptions = useRoleFilterOptions()
  const levelOptions = [
    { label: t('search.allLevels'), value: '' },
    ...LEVEL_KEYS.map(value => ({
      label: t(`level.${value}`),
      value,
    })),
  ]
  const sortOptions = SORT_OPTIONS.map(o => ({ label: t(o.labelKey), value: o.value }))

  return (
    <Card style={{ marginBottom: 16, borderRadius: 12 }}>
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} sm={12} md={6} lg={5}>
          <Input
            placeholder={t('search.keywordPlaceholder')}
            prefix={<SearchOutlined />}
            value={state.keyword}
            onChange={e => state.setFilter('keyword', e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder={t('search.rolePlaceholder')}
            style={{ width: '100%' }}
            value={state.roleType || undefined}
            onChange={v => state.setFilter('roleType', v || '')}
            options={roleOptions}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder={t('search.levelPlaceholder')}
            style={{ width: '100%' }}
            value={state.academicLevel || undefined}
            onChange={v => state.setFilter('academicLevel', v || '')}
            options={levelOptions}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder={t('search.sortPlaceholder')}
            style={{ width: '100%' }}
            value={state.sortBy}
            onChange={v => state.setFilter('sortBy', v)}
            options={sortOptions}
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<FilterOutlined />} onClick={state.toggleAdvanced}>
            {t('search.advanced')}
          </Button>
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<ReloadOutlined />} onClick={state.resetFilters}>
            {t('common.reset')}
          </Button>
        </Col>
      </Row>

      {state.advancedOpen && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder={t('search.parentLabPlaceholder')}
              value={state.parentLab}
              onChange={e => state.setFilter('parentLab', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder={t('search.labGroupPlaceholder')}
              value={state.labName}
              onChange={e => state.setFilter('labName', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder={t('search.researchAreaPlaceholder')}
              value={state.researchArea}
              onChange={e => state.setFilter('researchArea', e.target.value)}
              allowClear
            />
          </Col>
        </Row>
      )}
    </Card>
  )
}

export default LabSearchFilter
