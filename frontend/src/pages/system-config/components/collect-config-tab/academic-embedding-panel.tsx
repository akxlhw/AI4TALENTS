import { Card, Typography, Space, Button, Alert, Progress, Spin, Row, Col, Statistic } from 'antd'
import { ReloadOutlined, SyncOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import '../../../../i18n/namespaces/system-config'
import { semanticColors } from '../../../../theme'
import { formatNumber } from '../../../../utils/format'

const { Text } = Typography

export interface AcademicEmbeddingPanelProps {
  embeddingStatus: {
    total_talents: number
    embedded_talents: number
    pending_talents: number
    last_generated: string | null
    progress_percent: number
  } | null
  embeddingProgress: {
    status: string
    processed: number
    total: number
    failed: number
  } | null
  embeddingLoading: boolean
  onGenerate: (force: boolean) => void
  onCancel: () => void
  onRefresh: () => void
}

const AcademicEmbeddingPanel: React.FC<AcademicEmbeddingPanelProps> = ({
  embeddingStatus,
  embeddingProgress,
  embeddingLoading,
  onGenerate,
  onCancel,
  onRefresh,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const K = 'collectConfig.embeddings.academic'

  return (
    <Card>
      <Spin spinning={embeddingLoading}>
        <Alert
          message={t(`${K}.title`)}
          description={t(`${K}.description`)}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.totalTalents`)}
                value={embeddingStatus?.total_talents || 0}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.embedded`)}
                value={embeddingStatus?.embedded_talents || 0}
                valueStyle={{ color: semanticColors.green }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.pending`)}
                value={embeddingStatus?.pending_talents || 0}
                valueStyle={{ color: semanticColors.gold }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title={t(`${K}.coverage`)}
                value={embeddingStatus?.progress_percent || 0}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
        {(embeddingProgress?.status === 'running' || embeddingProgress?.status === 'pending') && (
          <Alert
            type="info"
            showIcon
            icon={<SyncOutlined spin />}
            style={{ marginBottom: 16 }}
            message={
              embeddingProgress?.status === 'pending' ? t(`${K}.starting`) : t(`${K}.running`)
            }
            description={
              <div>
                <Progress
                  percent={
                    embeddingProgress?.total > 0
                      ? Math.round((embeddingProgress.processed / embeddingProgress.total) * 100)
                      : 0
                  }
                  status="active"
                />
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text type="secondary">
                    {t(`${K}.processedOf`, {
                      processed: formatNumber(embeddingProgress?.processed),
                      total: formatNumber(embeddingProgress?.total),
                    })}
                  </Text>
                  {embeddingProgress?.failed > 0 && (
                    <Text type="danger">
                      {t(`${K}.failedCount`, { n: embeddingProgress.failed })}
                    </Text>
                  )}
                </Space>
              </div>
            }
          />
        )}
        {embeddingProgress?.status === 'completed' && (
          <Alert
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            style={{ marginBottom: 16 }}
            message={t(`${K}.completed`)}
            description={t(`${K}.completedDesc`, { n: embeddingProgress.processed })}
          />
        )}
        {embeddingProgress?.status === 'error' && (
          <Alert type="error" showIcon style={{ marginBottom: 16 }} message={t(`${K}.error`)} />
        )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={embeddingProgress?.status === 'running'} />}
            onClick={() => onGenerate(false)}
            loading={embeddingProgress?.status === 'running'}
            disabled={embeddingProgress?.status === 'running'}
          >
            {embeddingProgress?.status === 'running' ? t(`${K}.generating`) : t(`${K}.generate`)}
          </Button>
          <Button
            danger
            onClick={() => onGenerate(true)}
            disabled={embeddingProgress?.status === 'running'}
          >
            {t(`${K}.forceRegenerate`)}
          </Button>
          {embeddingProgress?.status === 'running' && (
            <Button onClick={onCancel}>{t('common:actions.cancel')}</Button>
          )}
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={embeddingLoading}>
            {t('actions.refreshStatus')}
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default AcademicEmbeddingPanel
