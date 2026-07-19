import {
  Card,
  Typography,
  Space,
  Button,
  Alert,
  Progress,
  Spin,
  Row,
  Col,
  Statistic,
} from 'antd'
import { ReloadOutlined, SyncOutlined, CheckCircleOutlined } from '@ant-design/icons'
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
  return (
    <Card>
      <Spin spinning={embeddingLoading}>
        <Alert
          message="学术人才向量嵌入"
          description="生成学术人才向量嵌入用于语义搜索和智能推荐。需要先配置 LLM API。生成过程为后台异步执行，耗时取决于人才数量。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic title="人才总数" value={embeddingStatus?.total_talents || 0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="已生成向量"
                value={embeddingStatus?.embedded_talents || 0}
                valueStyle={{ color: semanticColors.green }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="待生成"
                value={embeddingStatus?.pending_talents || 0}
                valueStyle={{ color: semanticColors.gold }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic title="覆盖率" value={embeddingStatus?.progress_percent || 0} suffix="%" />
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
              embeddingProgress?.status === 'pending' ? '正在启动向量生成...' : '向量生成进行中...'
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
                    已处理 {formatNumber(embeddingProgress?.processed)} /{' '}
                    {formatNumber(embeddingProgress?.total)} 位人才
                  </Text>
                  {embeddingProgress?.failed > 0 && (
                    <Text type="danger">失败 {embeddingProgress.failed}</Text>
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
            message="向量生成完成"
            description={`成功处理 ${embeddingProgress.processed} 位人才`}
          />
        )}
        {embeddingProgress?.status === 'error' && (
          <Alert type="error" showIcon style={{ marginBottom: 16 }} message="向量生成失败" />
        )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={embeddingProgress?.status === 'running'} />}
            onClick={() => onGenerate(false)}
            loading={embeddingProgress?.status === 'running'}
            disabled={embeddingProgress?.status === 'running'}
          >
            {embeddingProgress?.status === 'running' ? '生成中...' : '生成向量'}
          </Button>
          <Button
            danger
            onClick={() => onGenerate(true)}
            disabled={embeddingProgress?.status === 'running'}
          >
            强制重新生成
          </Button>
          {embeddingProgress?.status === 'running' && <Button onClick={onCancel}>取消</Button>}
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={embeddingLoading}>
            刷新状态
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default AcademicEmbeddingPanel
