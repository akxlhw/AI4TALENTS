import { Button, Card, Col, Empty, Row, Space, Spin, Tag, Typography, message } from 'antd'
import { FolderOutlined, PlusOutlined, TeamOutlined } from '@ant-design/icons'
import type { TalentPool } from '../../../types'

const { Text } = Typography

interface TalentPoolTabProps {
  pools: TalentPool[]
  poolsLoading: boolean
  onCreatePool: () => void
}

const TalentPoolTab: React.FC<TalentPoolTabProps> = ({ pools, poolsLoading, onCreatePool }) => {
  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onCreatePool}>
          创建人才池
        </Button>
      </div>

      <Spin spinning={poolsLoading}>
        {pools.length > 0 ? (
          <Row gutter={[16, 16]}>
            {pools.map(pool => (
              <Col xs={24} sm={12} lg={8} key={pool.pool_id}>
                <Card hoverable onClick={() => message.info('人才池详情页建设中，敬请期待')}>
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
                        {pool.member_count} 人
                      </Tag>
                      <Tag>{pool.pool_type === 'custom' ? '自定义' : pool.pool_type}</Tag>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty description="暂无人才池">
            <Button type="primary" onClick={onCreatePool}>
              创建人才池
            </Button>
          </Empty>
        )}
      </Spin>
    </Card>
  )
}

export default TalentPoolTab
