import { Card, Space, Button, Alert, Progress, Spin } from 'antd'
import { useTranslation } from 'react-i18next'
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons'
import '../../../../i18n/namespaces/system-config'

interface GenealogyPanelProps {
  genealogySyncStatus: {
    status: string
    processed: number
    total: number
    edges: number
    current_phase?: string
  } | null
  genealogySyncLoading: boolean
  onSync: () => void
  onRefresh: () => void
}

const GenealogyPanel: React.FC<GenealogyPanelProps> = ({
  genealogySyncStatus,
  genealogySyncLoading,
  onSync,
  onRefresh,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  return (
    <Card>
      <Spin spinning={genealogySyncLoading}>
        <Alert
          message={t('collectConfig.genealogy.title')}
          description={t('collectConfig.genealogy.description')}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        {(genealogySyncStatus?.status === 'running' ||
          genealogySyncStatus?.status === 'pending') && (
          <div style={{ marginBottom: 16 }}>
            <Alert
              type="info"
              showIcon
              icon={<SyncOutlined spin />}
              style={{ marginBottom: 8 }}
              message={
                genealogySyncStatus?.status === 'pending'
                  ? t('collectConfig.genealogy.starting')
                  : t('collectConfig.genealogy.running', {
                      phase: genealogySyncStatus?.current_phase || '',
                    })
              }
            />
            {genealogySyncStatus?.status === 'running' && genealogySyncStatus?.total > 0 && (
              <div style={{ marginTop: 8 }}>
                <Progress
                  percent={Math.min(
                    100,
                    Math.round((genealogySyncStatus.processed / genealogySyncStatus.total) * 100)
                  )}
                  status="active"
                  format={() =>
                    t('collectConfig.genealogy.progressFormat', {
                      processed: genealogySyncStatus.processed,
                      total: genealogySyncStatus.total,
                      edges: genealogySyncStatus.edges,
                    })
                  }
                />
              </div>
            )}
          </div>
        )}
        {genealogySyncStatus?.status === 'completed' && (
          <div style={{ marginBottom: 16 }}>
            <Alert
              type="success"
              showIcon
              message={t('collectConfig.genealogy.completed', {
                processed: genealogySyncStatus.processed,
                edges: genealogySyncStatus.edges,
              })}
            />
          </div>
        )}
        {genealogySyncStatus?.status &&
          typeof genealogySyncStatus.status === 'string' &&
          genealogySyncStatus.status.startsWith('error') && (
            <div style={{ marginBottom: 16 }}>
              <Alert
                type="error"
                showIcon
                message={t('collectConfig.genealogy.failed', {
                  status: genealogySyncStatus.status,
                })}
              />
            </div>
          )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={genealogySyncStatus?.status === 'running'} />}
            onClick={onSync}
            loading={genealogySyncStatus?.status === 'running'}
            disabled={genealogySyncStatus?.status === 'running'}
          >
            {genealogySyncStatus?.status === 'running'
              ? t('collectConfig.genealogy.computing')
              : t('collectConfig.genealogy.start')}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={genealogySyncLoading}>
            {t('actions.refreshStatus')}
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default GenealogyPanel
