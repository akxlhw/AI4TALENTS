/**
 * TalentPoolSection - 人才池区域组件
 *
 * 职责：
 * - 显示人才池列表
 * - 支持创建新人才池
 * - 点击人才池跳转详情
 */
import { Card, Row, Col, Typography, Tag, Space, Button, Empty, Spin } from 'antd'
import { PlusOutlined, FolderOutlined, TeamOutlined } from '@ant-design/icons'
import type { TalentPool } from '../../types'

const { Text } = Typography

export interface TalentPoolSectionProps {
  pools: TalentPool[]
  loading: boolean
  onCreatePool: () => void
  onPoolClick: (poolId: number) => void
}

const TalentPoolSection: React.FC<TalentPoolSectionProps> = ({
  pools,
  loading,
  onCreatePool,
  onPoolClick,
}) => {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={onCreatePool}
        >
          创建人才池
        </Button>
      </div>

      <Spin spinning={loading}>
        {pools.length > 0 ? (
          <Row gutter={[16, 16]}>
            {pools.map(pool => (
              <Col span={8} key={pool.pool_id}>
                <Card
                  hoverable
                  onClick={() => onPoolClick(pool.pool_id)}
                >
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
    </div>
  )
}

export default TalentPoolSection
