import { Card, Space, Button, Alert, Progress, Spin, Row, Col, Statistic } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReloadOutlined, SyncOutlined, TeamOutlined } from '@ant-design/icons'
import { semanticColors } from '../../../../theme'
import { formatUTCToLocal } from '../../../../utils/datetime'
import '../../../../i18n/namespaces/system-config'

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
  const { t } = useTranslation(['systemConfig', 'common'])

  return (
    <Card>
      <Spin spinning={collabSyncLoading}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t('collectConfig.collabSync.syncedTalents')}
                value={collabDataStatus?.talents_with_collaborations || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t('collectConfig.collabSync.collaborations')}
                value={collabDataStatus?.total_collaborations || 0}
                prefix={<TeamOutlined />}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t('collectConfig.collabSync.lastSync')}
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
                collabSyncStatus?.status === 'pending'
                  ? t('collectConfig.collabSync.starting')
                  : t('collectConfig.collabSync.running')
              }
            />
            {collabSyncStatus?.status === 'running' && collabSyncStatus?.total > 0 && (
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={Math.round((collabSyncStatus.processed / collabSyncStatus.total) * 100)}
                  status="active"
                  format={() =>
                    t('collectConfig.collabSync.progressFormat', {
                      processed: collabSyncStatus.processed,
                      total: collabSyncStatus.total,
                      collaborations: collabSyncStatus.collaborations,
                    })
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
            {collabSyncStatus?.status === 'running'
              ? t('collectConfig.collabSync.syncing')
              : t('collectConfig.collabSync.syncAll')}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={collabSyncLoading}>
            {t('actions.refreshStatus')}
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default CollabSyncPanel
