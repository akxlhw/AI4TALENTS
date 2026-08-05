import { Button, Card, Col, Input, Row, Select, Space, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { FollowupStatus } from '../../../types'

const { Text } = Typography

interface FavoritesFilterBarProps {
  roleFilter: string | undefined
  keyword: string
  followupFilter: string | undefined
  followupStatuses: FollowupStatus[]
  onRoleFilterChange: (val: string | undefined) => void
  onFollowupFilterChange: (val: string | undefined) => void
  onKeywordChange: (val: string) => void
  onSearch: () => void
  onReset: () => void
}

const FavoritesFilterBar: React.FC<FavoritesFilterBarProps> = ({
  roleFilter,
  keyword,
  followupFilter,
  followupStatuses,
  onRoleFilterChange,
  onFollowupFilterChange,
  onKeywordChange,
  onSearch,
  onReset,
}) => {
  return (
    <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '12px 24px' } }}>
      <Row gutter={16} align="middle">
        <Col>
          <Space size={8} wrap>
            <Text type="secondary">筛选:</Text>

            <Select
              placeholder="角色"
              value={roleFilter}
              onChange={onRoleFilterChange}
              allowClear
              style={{ width: 140 }}
              options={[
                { value: 'professor', label: '教授/研究员' },
                { value: 'student', label: '学生' },
                { value: 'graduated', label: '毕业生' },
              ]}
            />

            <Select
              placeholder="跟进状态"
              value={followupFilter}
              onChange={onFollowupFilterChange}
              allowClear
              style={{ width: 120 }}
              options={followupStatuses}
            />

            <Input.Search
              placeholder="搜索姓名..."
              value={keyword}
              onChange={e => onKeywordChange(e.target.value)}
              onSearch={onSearch}
              allowClear
              style={{ width: 200 }}
              enterButton={<SearchOutlined />}
            />

            {(roleFilter || keyword || followupFilter) && (
              <Button type="link" onClick={onReset}>
                重置筛选
              </Button>
            )}
          </Space>
        </Col>
      </Row>
    </Card>
  )
}

export default FavoritesFilterBar
