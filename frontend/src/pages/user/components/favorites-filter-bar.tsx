import { Button, Card, Col, Input, Row, Select, Space, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('user')
  return (
    <Card style={{ marginBottom: 16 }} styles={{ body: { padding: '12px 24px' } }}>
      <Row gutter={16} align="middle">
        <Col>
          <Space size={8} wrap>
            <Text type="secondary">{t('filter.label')}</Text>

            <Select
              placeholder={t('filter.role')}
              value={roleFilter}
              onChange={onRoleFilterChange}
              allowClear
              style={{ width: 140 }}
              options={[
                { value: 'professor', label: t('filter.roleOptions.professor') },
                { value: 'student', label: t('filter.roleOptions.student') },
                { value: 'graduated', label: t('filter.roleOptions.graduated') },
              ]}
            />

            <Select
              placeholder={t('filter.followup')}
              value={followupFilter}
              onChange={onFollowupFilterChange}
              allowClear
              style={{ width: 120 }}
              options={followupStatuses}
            />

            <Input.Search
              placeholder={t('filter.searchPlaceholder')}
              value={keyword}
              onChange={e => onKeywordChange(e.target.value)}
              onSearch={onSearch}
              allowClear
              style={{ width: 200 }}
              enterButton={<SearchOutlined />}
            />

            {(roleFilter || keyword || followupFilter) && (
              <Button type="link" onClick={onReset}>
                {t('filter.reset')}
              </Button>
            )}
          </Space>
        </Col>
      </Row>
    </Card>
  )
}

export default FavoritesFilterBar
