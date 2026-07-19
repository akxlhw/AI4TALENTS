import { Card, Space, Button, Alert, Progress, Spin, Row, Col, Statistic } from 'antd'
import { ReloadOutlined, SyncOutlined, TeamOutlined } from '@ant-design/icons'
import { semanticColors } from '../../../../theme'
import { formatUTCToLocal } from '../../../../utils/datetime'

interface CollabSyncPanelProps {
  collabSyncStatus: {
    status: string
    processed: number
    total: number
    collaborations: number
  } | null
  collabDataStatus: {
    total_collaborations: number
    talents_with_collaborations: number
    last_sync: string | null
  } | null
  collabSyncLoading: boolean
  onSyncAll: () => void
  onRefresh: () => void
}

const CollabSyncPanel: React.FC<CollabSyncPanelProps> = ({
  collabSyncStatus,
  collabDataStatus,
  collabSyncLoading,
  onSyncAll,
  onRefresh,
}) => {
  return (
    <Card>
      <Spin spinning={collabSyncLoading}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="已同步学者数"
                value={collabDataStatus?.talents_with_collaborations || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="合作关系数"
                value={collabDataStatus?.total_collaborations || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="最后同步时间"
                value={formatUTCToLocal(collabDataStatus?.last_sync)}
                valueStyle={{ fontSize: 16 }}
              />
            </Card>
          </Col>
        </Row>
        {(collabSyncStatus?.status === 'running' || collabSyncStatus?.status === 'pending') && (
          <div style={{ marginBottom: 16 }}>
            <Alert
              type="info"
              showIcon
              icon={<SyncOutlined spin />}
              style={{ marginBottom: 8 }}
              message={
                collabSyncStatus?.status === 'pending' ? '正在启动同步任务...' : '同步进行中...'
              }
            />
            {collabSyncStatus?.status === 'running' && collabSyncStatus?.total > 0 && (
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={Math.round((collabSyncStatus.processed / collabSyncStatus.total) * 100)}
                  status="active"
                  format={() =>
                    `${collabSyncStatus.processed}/${collabSyncStatus.total} 论文，${collabSyncStatus.collaborations} 条合作关系`
                  }
                />
              </div>
            )}
          </div>
        )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={collabSyncStatus?.status === 'running'} />}
            onClick={onSyncAll}
            loading={collabSyncStatus?.status === 'running'}
            disabled={collabSyncStatus?.status === 'running'}
          >
            {collabSyncStatus?.status === 'running' ? '同步中...' : '批量同步所有学者'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={collabSyncLoading}>
            刷新状态
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default CollabSyncPanel
