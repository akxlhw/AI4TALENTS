import { Button, Card, Col, Empty, Row, Space, Spin, Tag, Typography, message } from 'antd'
import { FolderOutlined, PlusOutlined, TeamOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import type { TalentPool } from '../../../types'

const { Text } = Typography

interface TalentPoolTabProps {
  pools: TalentPool[]
  poolsLoading: boolean
  onCreatePool: () => void
}

const TalentPoolTab: React.FC<TalentPoolTabProps> = ({ pools, poolsLoading, onCreatePool }) => {
  const { t } = useTranslation('user')
  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onCreatePool}>
          {t('pools.create')}
        </Button>
      </div>

      <Spin spinning={poolsLoading}>
        {pools.length > 0 ? (
          <Row gutter={[16, 16]}>
            {pools.map(pool => (
              <Col xs={24} sm={12} lg={8} key={pool.pool_id}>
                <Card hoverable onClick={() => message.info(t('pools.detailComingSoon'))}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong style={{ fontSize: 16 }}>
                      <FolderOutlined style={{ marginRight: 8 }} />
                      {pool.pool_name}
                    </Text>
                    {pool.scope_desc && (
                      <Text type="secondary" ellipsis>
                        {pool.scope_desc}
                      </Text>
                    )}
                    <div>
                      <Tag color="blue">
                        <TeamOutlined style={{ marginRight: 4 }} />
                        {t('pools.memberCount', { count: pool.member_count })}
                      </Tag>
                      <Tag>{pool.pool_type === 'custom' ? t('pools.typeCustom') : pool.pool_type}</Tag>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description={t('pools.empty')}>
            <Button type="primary" onClick={onCreatePool}>
              {t('pools.create')}
            </Button>
          </Empty>
        )}
      </Spin>
    </Card>
  )
}

export default TalentPoolTab
