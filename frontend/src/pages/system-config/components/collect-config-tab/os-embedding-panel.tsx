import { Card, Typography, Space, Button, Alert, Progress, Spin, Row, Col, Statistic } from 'antd'
import { ReloadOutlined, SyncOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import '../../../../i18n/namespaces/system-config'
import { semanticColors } from '../../../../theme'
import { formatNumber } from '../../../../utils/format'

const { Text } = Typography

export interface OsEmbeddingPanelProps {
  osEmbeddingStatus: {
    total_developers: number
    embedded_count: number
    pending_count: number
    progress_percent: number
    dimension: number
    model_name: string
  } | null
  osEmbeddingProgress: {
    status: string
    processed: number
    total: number
    failed: number
  } | null
  osEmbeddingLoading: boolean
  onGenerate: (force: boolean) => void
  onCancel: () => void
  onRefresh: () => void
}

const OsEmbeddingPanel: React.FC<OsEmbeddingPanelProps> = ({
  osEmbeddingStatus,
  osEmbeddingProgress,
  osEmbeddingLoading,
  onGenerate,
  onCancel,
  onRefresh,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const K = 'collectConfig.embeddings.os'

  return (
    <Card>
      <Spin spinning={osEmbeddingLoading}>
        <Alert
          message={t(`${K}.title`)}
          description={t(`${K}.description`, {
            model: osEmbeddingStatus?.model_name || t(`${K}.notConfigured`),
          })}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.totalDevelopers`)}
                value={osEmbeddingStatus?.total_developers || 0}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.embedded`)}
                value={osEmbeddingStatus?.embedded_count || 0}
                valueStyle={{ color: semanticColors.green }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.pending`)}
                value={osEmbeddingStatus?.pending_count || 0}
                valueStyle={{ color: semanticColors.gold }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.coverage`)}
                value={osEmbeddingStatus?.progress_percent || 0}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
        {(osEmbeddingProgress?.status === 'running' ||
          osEmbeddingProgress?.status === 'pending') && (
          <Alert
            type="info"
            showIcon
            icon={<SyncOutlined spin />}
            style={{ marginBottom: 16 }}
            message={
              osEmbeddingProgress?.status === 'pending' ? t(`${K}.starting`) : t(`${K}.running`)
            }
            description={
              <div>
                <Progress
                  percent={
                    osEmbeddingProgress?.total > 0
                      ? Math.round(
                          (osEmbeddingProgress.processed / osEmbeddingProgress.total) * 100
                        )
                      : 0
                  }
                  status="active"
                />
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text type="secondary">
                    {t(`${K}.processedOf`, {
                      processed: formatNumber(osEmbeddingProgress?.processed),
                      total: formatNumber(osEmbeddingProgress?.total),
                    })}
                  </Text>
                  {osEmbeddingProgress?.failed > 0 && (
                    <Text type="danger">
                      {t(`${K}.failedCount`, { n: osEmbeddingProgress.failed })}
                    </Text>
                  )}
                </Space>
              </div>
            }
          />
        )}
        {osEmbeddingProgress?.status === 'completed' && (
          <Alert
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            style={{ marginBottom: 16 }}
            message={t(`${K}.completed`)}
            description={t(`${K}.completedDesc`, { n: osEmbeddingProgress.processed })}
          />
        )}
        {osEmbeddingProgress?.status === 'error' && (
          <Alert type="error" showIcon style={{ marginBottom: 16 }} message={t(`${K}.error`)} />
        )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={osEmbeddingProgress?.status === 'running'} />}
            onClick={() => onGenerate(false)}
            loading={osEmbeddingProgress?.status === 'running'}
            disabled={osEmbeddingProgress?.status === 'running'}
          >
            {osEmbeddingProgress?.status === 'running' ? t(`${K}.generating`) : t(`${K}.generate`)}
          </Button>
          <Button
            danger
            onClick={() => onGenerate(true)}
            disabled={osEmbeddingProgress?.status === 'running'}
          >
            {t(`${K}.forceRegenerate`)}
          </Button>
          {osEmbeddingProgress?.status === 'running' && (
            <Button onClick={onCancel}>{t('common:actions.cancel')}</Button>
          )}
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={osEmbeddingLoading}>
            {t('actions.refreshStatus')}
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default OsEmbeddingPanel
