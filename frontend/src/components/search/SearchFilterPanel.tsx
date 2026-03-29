/**
 * SearchFilterPanel - 搜索筛选面板组件
 *
 * 职责：
 * - 渲染所有筛选项（角色、学校、国家、技术要素等）
 * - 提供重置功能
 * - 列设置和模板按钮
 */
import { Row, Col, Select, Button, Space, Typography } from 'antd'
import { ReloadOutlined, BookOutlined, SettingOutlined } from '@ant-design/icons'
import type { DropdownOption } from '../../types'

const { Text } = Typography

export interface SearchFilterValues {
  role?: string
  school_id?: number
  country_id?: number
  tech_element_id?: number
  tech_direction_id?: number
  min_works?: number
  min_citations?: number
  is_graduated?: string
  confirm_status?: string
}

export interface SearchFilterPanelProps {
  // 筛选状态
  filters: SearchFilterValues
  // 下拉选项
  schoolOptions: DropdownOption[]
  countryOptions: DropdownOption[]
  techElementOptions: DropdownOption[]
  directionOptions: DropdownOption[]
  // 回调
  onFilterChange: (key: keyof SearchFilterValues, value: any) => void
  onResetFilters: () => void
  onOpenColumnSettings: () => void
  onOpenTemplateMenu: () => void
  templateCount: number
  hasActiveFilters: boolean
}

const isGraduatedOptions = [
  { value: 'yes', label: '已毕业' },
  { value: 'no', label: '在读' },
]

const confirmStatusOptions = [
  { value: 'confirmed', label: '已确认' },
  { value: 'pending', label: '待确认' },
]

const roleOptions = [
  { value: 'professor', label: '教授/研究员' },
  { value: 'student', label: '学生' },
  { value: 'graduated', label: '毕业生' },
]

const minWorksOptions = [
  { value: 10, label: '10篇以上' },
  { value: 50, label: '50篇以上' },
  { value: 100, label: '100篇以上' },
]

const minCitationsOptions = [
  { value: 100, label: '100次以上' },
  { value: 500, label: '500次以上' },
  { value: 1000, label: '1000次以上' },
]

const SearchFilterPanel: React.FC<SearchFilterPanelProps> = ({
  filters,
  schoolOptions,
  countryOptions,
  techElementOptions,
  directionOptions,
  onFilterChange,
  onResetFilters,
  onOpenColumnSettings,
  onOpenTemplateMenu,
  templateCount,
  hasActiveFilters,
}) => {
  return (
    <Row gutter={[16, 8]}>
      <Col span={24}>
        <Space size={8} wrap>
          <Text type="secondary">筛选:</Text>

          {/* 技术要素 */}
          <Select
            placeholder="技术要素"
            value={filters.tech_element_id}
            onChange={(val) => {
              onFilterChange('tech_element_id', val)
              // 清空技术方向
              if (val !== filters.tech_element_id) {
                onFilterChange('tech_direction_id', undefined)
              }
            }}
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 140 }}
            options={techElementOptions}
          />

          {/* 技术方向 */}
          <Select
            placeholder="技术方向"
            value={filters.tech_direction_id}
            onChange={(val) => onFilterChange('tech_direction_id', val)}
            allowClear
            style={{ width: 140 }}
            options={directionOptions}
            disabled={!filters.tech_element_id}
          />

          {/* 国家 */}
          <Select
            placeholder="国家"
            value={filters.country_id}
            onChange={(val) => onFilterChange('country_id', val)}
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 120 }}
            options={countryOptions}
          />

          {/* 学校 */}
          <Select
            placeholder="学校"
            value={filters.school_id}
            onChange={(val) => onFilterChange('school_id', val)}
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 180 }}
            options={schoolOptions}
          />

          {/* 角色 */}
          <Select
            placeholder="角色"
            value={filters.role}
            onChange={(val) => onFilterChange('role', val)}
            allowClear
            style={{ width: 140 }}
            options={roleOptions}
          />

          {/* 是否已毕业 */}
          <Select
            placeholder="毕业状态"
            value={filters.is_graduated}
            onChange={(val) => onFilterChange('is_graduated', val)}
            allowClear
            style={{ width: 100 }}
            options={isGraduatedOptions}
          />

          {/* 待确认状态 */}
          <Select
            placeholder="确认状态"
            value={filters.confirm_status}
            onChange={(val) => onFilterChange('confirm_status', val)}
            allowClear
            style={{ width: 100 }}
            options={confirmStatusOptions}
          />
        </Space>
      </Col>
      <Col span={24}>
        <Space size={8}>
          {/* 最少论文 */}
          <Select
            placeholder="最少论文"
            value={filters.min_works}
            onChange={(val) => onFilterChange('min_works', val)}
            allowClear
            style={{ width: 120 }}
            options={minWorksOptions}
          />

          {/* 最少引用 */}
          <Select
            placeholder="最少引用"
            value={filters.min_citations}
            onChange={(val) => onFilterChange('min_citations', val)}
            allowClear
            style={{ width: 120 }}
            options={minCitationsOptions}
          />

          {hasActiveFilters && (
            <Button type="link" icon={<ReloadOutlined />} onClick={onResetFilters}>
              重置筛选
            </Button>
          )}

          <Button size="small" icon={<BookOutlined />} onClick={onOpenTemplateMenu}>
            模板 {templateCount > 0 && `(${templateCount})`}
          </Button>

          <Button
            size="small"
            icon={<SettingOutlined />}
            onClick={onOpenColumnSettings}
          >
            列设置
          </Button>
        </Space>
      </Col>
    </Row>
  )
}

export default SearchFilterPanel
