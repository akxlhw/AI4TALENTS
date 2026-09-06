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

const SORT_OPTIONS = [
  { value: 'stars_desc', label: 'Stars 降序' },
  { value: 'stars_asc', label: 'Stars 升序' },
  { value: 'name_asc', label: '名称升序' },
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
  const primary = domainThemes.opensource.primary

  return (
    <Card className="domain-card" style={{ marginBottom: 16 }} styles={{ body: { padding: 20 } }}>
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Input
          size="large"
          placeholder="搜索开发者、技术栈、公司..."
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
          搜索
        </Button>
      </Space.Compact>

      <Space wrap style={{ marginBottom: 8 }}>
        <Button icon={<FilterOutlined />} onClick={onToggleFilterExpanded}>
          {filterExpanded ? '收起筛选' : '展开筛选'}
        </Button>
        <Segmented
          value={query.mode}
          onChange={v => onQueryChange({ ...query, mode: v as OSSearchQuery['mode'] })}
          options={[
            { label: '关键词', value: 'keyword' },
            { label: '语义', value: 'semantic' },
            { label: '混合', value: 'hybrid' },
          ]}
        />
        <Select
          value={query.sort_by}
          onChange={v => onQueryChange({ ...query, sort_by: v })}
          style={{ width: 140 }}
          options={SORT_OPTIONS}
        />
      </Space>

      {filterExpanded && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="技术领域（要素）" style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder="选择技术要素"
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
                options={TECH_ELEMENT_GROUPS}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="关联仓库" style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder={query.tech_elements?.length ? '选择仓库' : '请先选择技术领域'}
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
            <Form.Item label="地区" style={{ marginBottom: 8 }}>
              <Input
                placeholder="如: Beijing"
                value={query.location}
                onChange={e => onQueryChange({ ...query, location: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="公司" style={{ marginBottom: 8 }}>
              <Input
                placeholder="如: Microsoft"
                value={query.company}
                onChange={e => onQueryChange({ ...query, company: e.target.value })}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item label="编程语言" style={{ marginBottom: 8 }}>
              <Select
                mode="multiple"
                placeholder="选择编程语言"
                value={query.languages}
                onChange={v => onQueryChange({ ...query, languages: v })}
                style={{ width: '100%' }}
                options={LANGUAGE_OPTIONS}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={24} md={16} lg={12}>
            <Form.Item label="筛选" style={{ marginBottom: 8 }}>
              <Space size={16} style={{ whiteSpace: 'nowrap' }}>
                <Checkbox
                  checked={query.is_committer}
                  onChange={e => onQueryChange({ ...query, is_committer: e.target.checked })}
                >
                  Committer
                </Checkbox>
                <Checkbox
                  checked={query.is_student}
                  onChange={e => onQueryChange({ ...query, is_student: e.target.checked })}
                >
                  在校生
                </Checkbox>
                <Checkbox
                  checked={query.china_related}
                  onChange={e => onQueryChange({ ...query, china_related: e.target.checked })}
                >
                  <Tooltip title="姓名含中文或命中百家姓拼音，或地区位于中国">中国背景</Tooltip>
                </Checkbox>
                <Checkbox
                  checked={query.top_org}
                  onChange={e => onQueryChange({ ...query, top_org: e.target.checked })}
                >
                  <Tooltip title="全球头部大厂 / 国内头部互联网 / 知名 AI 初创 / 知名院校（按公司字段匹配）">
                    名企/名校
                  </Tooltip>
                </Checkbox>
                <Checkbox
                  checked={query.has_contact}
                  onChange={e => onQueryChange({ ...query, has_contact: e.target.checked })}
                >
                  <Tooltip title="主页 / 邮箱 / 社媒，任一即算有联系方式">有联系方式</Tooltip>
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
