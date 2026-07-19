import { Card, Space, Button, Alert, Progress, Spin } from 'antd'
import { ReloadOutlined, SyncOutlined } from '@ant-design/icons'

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
  return (
    <Card>
      <Spin spinning={genealogySyncLoading}>
        <Alert
          message="学术族谱计算"
          description="从 RawWork 论文数据推断导师-学生传承关系，并计算学者影响力评分。计算过程为后台异步执行，耗时取决于论文数量。"
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
                  ? '正在启动计算任务...'
                  : `族谱计算进行中... (${genealogySyncStatus?.current_phase || ''})`
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
                    `${genealogySyncStatus.processed}/${genealogySyncStatus.total} 论文，${genealogySyncStatus.edges} 条关系`
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
              message={`族谱计算完成！处理 ${genealogySyncStatus.processed} 篇论文，推断 ${genealogySyncStatus.edges} 条关系`}
            />
          </div>
        )}
        {genealogySyncStatus?.status &&
          typeof genealogySyncStatus.status === 'string' &&
          genealogySyncStatus.status.startsWith('error') && (
            <div style={{ marginBottom: 16 }}>
              <Alert type="error" showIcon message={`计算失败: ${genealogySyncStatus.status}`} />
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
            {genealogySyncStatus?.status === 'running' ? '计算中...' : '启动族谱计算'}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={onRefresh} loading={genealogySyncLoading}>
            刷新状态
          </Button>
        </Space>
      </Spin>
    </Card>
  )
}

export default GenealogyPanel
