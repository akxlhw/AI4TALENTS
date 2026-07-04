import { Card, Row, Col, Input, Select, Button } from 'antd'
import { SearchOutlined, FilterOutlined, ReloadOutlined } from '@ant-design/icons'
import type { LabSearchState } from '../../../stores/labSearchStore'

interface LabSearchFilterProps {
  state: LabSearchState
}

const ROLE_OPTIONS = [
  { label: '全部角色', value: '' },
  { label: '教授', value: 'professor' },
  { label: '学生', value: 'student' },
  { label: '博后/研究员', value: 'graduate' },
]

const LEVEL_OPTIONS = [
  { label: '全部学位', value: '' },
  { label: '博士', value: 'phd' },
  { label: '硕士', value: 'master' },
  { label: '学士', value: 'bachelor' },
]

const SORT_OPTIONS = [
  { label: '默认排序', value: 'default' },
  { label: '姓名升序', value: 'name_asc' },
  { label: '届别降序', value: 'cohort_desc' },
  { label: '最近创建', value: 'created_desc' },
]

const LabSearchFilter: React.FC<LabSearchFilterProps> = ({ state }) => {
  return (
    <Card style={{ marginBottom: 16, borderRadius: 12 }}>
      <Row gutter={[16, 16]} align="middle">
        <Col xs={24} sm={12} md={6} lg={5}>
          <Input
            placeholder="输入姓名关键词..."
            prefix={<SearchOutlined />}
            value={state.keyword}
            onChange={(e) => state.setFilter('keyword', e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="角色"
            style={{ width: '100%' }}
            value={state.roleType || undefined}
            onChange={(v) => state.setFilter('roleType', v || '')}
            options={ROLE_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="学位层次"
            style={{ width: '100%' }}
            value={state.academicLevel || undefined}
            onChange={(v) => state.setFilter('academicLevel', v || '')}
            options={LEVEL_OPTIONS}
            allowClear
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={4}>
          <Select
            placeholder="排序"
            style={{ width: '100%' }}
            value={state.sortBy}
            onChange={(v) => state.setFilter('sortBy', v)}
            options={SORT_OPTIONS}
          />
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<FilterOutlined />} onClick={state.toggleAdvanced}>
            高级筛选
          </Button>
        </Col>
        <Col xs={12} sm={6} md={4} lg={3}>
          <Button icon={<ReloadOutlined />} onClick={state.resetFilters}>
            重置
          </Button>
        </Col>
      </Row>

      {state.advancedOpen && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="顶级实验室"
              value={state.parentLab}
              onChange={(e) => state.setFilter('parentLab', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="研究组"
              value={state.labName}
              onChange={(e) => state.setFilter('labName', e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Input
              placeholder="研究方向"
              value={state.researchArea}
              onChange={(e) => state.setFilter('researchArea', e.target.value)}
              allowClear
            />
          </Col>
        </Row>
      )}
    </Card>
  )
}

export default LabSearchFilter
