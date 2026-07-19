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
  return (
    <Card>
      <Spin spinning={osEmbeddingLoading}>
        <Alert
          message="开源人才向量嵌入"
          description={`生成开源开发者向量嵌入用于语义搜索和智能推荐。当前模型：${osEmbeddingStatus?.model_name || '未配置'}。生成过程为后台异步执行，耗时取决于开发者数量。`}
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic title="开发者总数" value={osEmbeddingStatus?.total_developers || 0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="已生成向量"
                value={osEmbeddingStatus?.embedded_count || 0}
                valueStyle={{ color: semanticColors.green }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="待生成"
                value={osEmbeddingStatus?.pending_count || 0}
                valueStyle={{ color: semanticColors.gold }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
              <Statistic
                title="覆盖率"
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
              osEmbeddingProgress?.status === 'pending'
                ? '正在启动向量生成...'
                : '向量生成进行中...'
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
                    已处理 {formatNumber(osEmbeddingProgress?.processed)} /{' '}
                    {formatNumber(osEmbeddingProgress?.total)} 位开发者
                  </Text>
                  {osEmbeddingProgress?.failed > 0 && (
                    <Text type="danger">失败 {osEmbeddingProgress.failed}</Text>
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
            message="向量生成完成"
            description={`成功处理 ${osEmbeddingProgress.processed} 位开发者`}
          />
        )}
        {osEmbeddingProgress?.status === 'error' && (
          <Alert type="error" showIcon style={{ marginBottom: 16 }} message="向量生成失败" />
        )}
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={osEmbeddingProgress?.status === 'running'} />}
            onClick={() => onGenerate(false)}
            loading={osEmbeddingProgress?.status === 'running'}
            disabled={osEmbeddingProgress?.status === 'running'}
          >
            {osEmbeddingProgress?.status === 'running' ? '生成中...' : '生成向量'}
          </Button>
          <Button
            danger
            onClick={() => onGenerate(true)}
            disabled={osEmbeddingProgress?.status === 'running'}
          >
            强制重新生成
          </Button>
          {osEmbeddingProgress?.status === 'running' && <Button onClick={onCancel}>取消</Button>}
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={osEmbeddingLoading}>
            刷新状态
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default OsEmbeddingPanel
