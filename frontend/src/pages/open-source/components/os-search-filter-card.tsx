import {
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  Row,
  Segmented,
  Select,
  Space,
  Tooltip,
} from 'antd'
import { FilterOutlined, SearchOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import '@/i18n/namespaces/open-source'
import { domainThemes } from '../../../theme'
import { TECH_ELEMENT_GROUPS } from '@/constants/tech-elements'
import type { OSSearchQuery } from '../../../types'

const LANGUAGE_OPTIONS = [
  { value: 'Python', label: 'Python' },
  { value: 'JavaScript', label: 'JavaScript' },
  { value: 'TypeScript', label: 'TypeScript' },
  { value: 'Go', label: 'Go' },
  { value: 'Rust', label: 'Rust' },
  { value: 'C++', label: 'C++' },
  { value: 'C', label: 'C' },
  { value: 'Java', label: 'Java' },
  { value: 'C#', label: 'C#' },
  { value: 'Shell', label: 'Shell' },
  { value: 'Ruby', label: 'Ruby' },
  { value: 'PHP', label: 'PHP' },
  { value: 'Swift', label: 'Swift' },
  { value: 'Kotlin', label: 'Kotlin' },
  { value: 'Scala', label: 'Scala' },
  { value: 'R', label: 'R' },
  { value: 'Julia', label: 'Julia' },
  { value: 'CUDA', label: 'CUDA' },
  { value: 'Lua', label: 'Lua' },
  { value: 'Haskell', label: 'Haskell' },
]

interface OsSearchFilterCardProps {
  query: OSSearchQuery
  filterExpanded: boolean
  repoOptions: { value: string; label: string }[]
  repoLoading: boolean
  onQueryChange: (query: OSSearchQuery) => void
  onQueryChangeAndSyncUrl: (query: OSSearchQuery) => void
  onSearch: () => void
  onToggleFilterExpanded: () => void
}

const OsSearchFilterCard: React.FC<OsSearchFilterCardProps> = ({
  query,
  filterExpanded,
  repoOptions,
  repoLoading,
  onQueryChange,
  onQueryChangeAndSyncUrl,
  onSearch,
  onToggleFilterExpanded,
}) => {
  const { t } = useTranslation(['openSource', 'common'])
  // taxonomy 命名空间翻译 TECH_ELEMENT_GROUPS 的 i18n key（域分组 + 要素标签）
  const { t: tTax } = useTranslation('taxonomy')
  const primary = domainThemes.opensource.primary

  const techElementOptions = TECH_ELEMENT_GROUPS.map(g => ({
    label: tTax(g.label),
    options: g.options.map(o => ({ ...o, label: tTax(o.label) })),
  }))

  const sortOptions = [
    { value: 'stars_desc', label: t('openSource:sort.starsDesc') },
    { value: 'stars_asc', label: t('openSource:sort.starsAsc') },
    { value: 'name_asc', label: t('openSource:sort.nameAsc') },
  ]

  return (
    <Card className="domain-card" style={{ marginBottom: 16 }} styles={{ body: { padding: 20 } }}>
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Input
          size="large"
          placeholder={t('openSource:search.placeholder')}
          prefix={<SearchOutlined />}
          value={query.q}
          onChange={e => onQueryChange({ ...query, q: e.target.value })}
          onPressEnter={onSearch}
        />
        <Button
          type="primary"
          size="large"
          onClick={onSearch}
          style={{ background: primary, borderColor: primary }}
        >
          {t('common:actions.search')}
        </Button>
      </Space.Compact>

      <Space wrap style={{ marginBottom: 8 }}>
        <Button icon={<FilterOutlined />} onClick={onToggleFilterExpanded}>
          {filterExpanded ? t('openSource:filter.collapse') : t('openSource:filter.expand')}
        </Button>
        <Segmented
          value={query.mode}
          onChange={v => onQueryChange({ ...query, mode: v as OSSearchQuery['mode'] })}
          options={[
            { label: t('openSource:filter.mode.keyword'), value: 'keyword' },
            { label: t('openSource:filter.mode.semantic'), value: 'semantic' },
            { label: t('openSource:filter.mode.hybrid'), value: 'hybrid' },
          ]}
        />
        <Select
          value={query.sort_by}
          onChange={v => onQueryChange({ ...query, sort_by: v })}
          style={{ width: 140 }}
          options={sortOptions}
        />
      </Space>

      {filterExpanded && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label={t('openSource:filter.techElements')} style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder={t('openSource:filter.techElementsPlaceholder')}
                value={query.tech_elements}
                onChange={v =>
                  onQueryChangeAndSyncUrl({
                    ...query,
                    tech_elements: v,
                    repo_full_names: [] as string[],
                    page: 1,
                  })
                }
                style={{ width: '100%' }}
                optionFilterProp="label"
                options={techElementOptions}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label={t('openSource:filter.repos')} style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder={
                  query.tech_elements?.length
                    ? t('openSource:filter.reposPlaceholder')
                    : t('openSource:filter.reposPlaceholderDisabled')
                }
                value={query.repo_full_names}
                onChange={v => onQueryChangeAndSyncUrl({ ...query, repo_full_names: v, page: 1 })}
                style={{ width: '100%' }}
                options={repoOptions}
                loading={repoLoading}
                disabled={!query.tech_elements?.length}
                allowClear
                showSearch
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label={t('openSource:filter.location')} style={{ marginBottom: 8 }}>
              <Input
                placeholder={t('openSource:filter.locationPlaceholder')}
                value={query.location}
                onChange={e => onQueryChange({ ...query, location: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label={t('openSource:filter.company')} style={{ marginBottom: 8 }}>
              <Input
                placeholder={t('openSource:filter.companyPlaceholder')}
                value={query.company}
                onChange={e => onQueryChange({ ...query, company: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label={t('openSource:filter.languages')} style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder={t('openSource:filter.languagesPlaceholder')}
                value={query.languages}
                onChange={v => onQueryChange({ ...query, languages: v })}
                style={{ width: '100%' }}
                options={LANGUAGE_OPTIONS}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={24} md={16} lg={12}>
            <Form.Item label={t('openSource:filter.group')} style={{ marginBottom: 8 }}>
              <Space size={16} style={{ whiteSpace: 'nowrap' }}>
                <Checkbox
                  checked={query.is_committer}
                  onChange={e => onQueryChange({ ...query, is_committer: e.target.checked })}
                >
                  {t('openSource:filter.committer')}
                </Checkbox>
                <Checkbox
                  checked={query.is_student}
                  onChange={e => onQueryChange({ ...query, is_student: e.target.checked })}
                >
                  {t('openSource:filter.student')}
                </Checkbox>
                <Checkbox
                  checked={query.china_related}
                  onChange={e => onQueryChange({ ...query, china_related: e.target.checked })}
                >
                  <Tooltip title={t('openSource:filter.chinaRelatedTip')}>
                    {t('openSource:filter.chinaRelated')}
                  </Tooltip>
                </Checkbox>
                <Checkbox
                  checked={query.top_org}
                  onChange={e => onQueryChange({ ...query, top_org: e.target.checked })}
                >
                  <Tooltip title={t('openSource:filter.topOrgTip')}>
                    {t('openSource:filter.topOrg')}
                  </Tooltip>
                </Checkbox>
                <Checkbox
                  checked={query.has_contact}
                  onChange={e => onQueryChange({ ...query, has_contact: e.target.checked })}
                >
                  <Tooltip title={t('openSource:filter.hasContactTip')}>
                    {t('openSource:filter.hasContact')}
                  </Tooltip>
                </Checkbox>
              </Space>
            </Form.Item>
          </Col>
        </Row>
      )}
    </Card>
  )
}

export default OsSearchFilterCard
