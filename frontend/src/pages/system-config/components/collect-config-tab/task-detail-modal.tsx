import {
  Modal,
  Typography,
  Button,
  Alert,
  Badge,
  Card,
  Table,
  Progress,
  Descriptions,
  Tooltip,
  Row,
  Col,
  Statistic,
} from 'antd'
import { semanticColors } from '../../../../theme'
import { getTaskStatusConfig } from '../../../../constants'
import type { CollectTask } from '../../../../types'
import { formatUTCToLocal } from '../../../../utils/datetime'

const { Text } = Typography

interface TaskDetailModalProps {
  open: boolean
  task: CollectTask | null
  onClose: () => void
}

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({ open, task, onClose }) => {
  return (
    <Modal
      title="任务详情"
      open={open}
      onCancel={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
      width={800}
    >
      {task && (
        <>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="任务编码">{task.task_code}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge
                status={getTaskStatusConfig(task.status).status}
                text={getTaskStatusConfig(task.status).label}
              />
            </Descriptions.Item>
            <Descriptions.Item label="技术领域">{task.tech_domain_name}</Descriptions.Item>
            <Descriptions.Item label="时间范围">
              {task.start_year}年 ~ {task.end_year ? `${task.end_year}年` : '至今'}
            </Descriptions.Item>
            <Descriptions.Item label="当前阶段">{task.current_step || '-'}</Descriptions.Item>
            <Descriptions.Item label="进度">
              <Progress
                percent={task.progress_percent}
                status={
                  task.status === 'failed'
                    ? 'exception'
                    : task.status === 'completed'
                      ? 'success'
                      : 'active'
                }
                style={{ minWidth: 120 }}
              />
            </Descriptions.Item>
          </Descriptions>

          <Card title="采集统计" size="small" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={4}>
                <Statistic title="采集论文" value={task.total_records || 0} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="获取作者"
                  value={task.result_summary?.total_authors || task.processed_records || 0}
                />
              </Col>
              <Col span={4}>
                <Statistic title="标准化作者" value={task.processed_records || 0} />
              </Col>
              <Col span={4}>
                <Statistic title="标准化院校" value={task.skipped_records || 0} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="入库人才"
                  value={task.success_records || 0}
                  valueStyle={{ color: semanticColors.green }}
                />
              </Col>
              <Col span={4}>
                <Statistic title="更新人才" value={task.result_summary?.updated_talents || 0} />
              </Col>
            </Row>
            {task.result_summary && (
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={4}>
                  <Statistic
                    title="新建人才"
                    value={task.result_summary.created_talents || 0}
                    valueStyle={{ color: semanticColors.blue }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="技术标签"
                    value={task.result_summary.created_tech_tags || 0}
                  />
                </Col>
              </Row>
            )}
          </Card>

          <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="触发时间">
                {formatUTCToLocal(task.triggered_at)}
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {formatUTCToLocal(task.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {formatUTCToLocal(task.completed_at)}
              </Descriptions.Item>
              <Descriptions.Item label="耗时">
                {task.result_summary?.total_duration || '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {task.result_summary?.venue_details && task.result_summary.venue_details.length > 0 && (
            <Card title="采集源详情" size="small" style={{ marginTop: 16 }}>
              <Table
                dataSource={task.result_summary.venue_details}
                rowKey="venue_id"
                size="small"
                pagination={false}
                columns={[
                  {
                    title: '采集源',
                    key: 'venue_id',
                    width: 120,
                    render: (_: unknown, record: { venue_id: number; venue_name: string }) => (
                      <Tooltip title={record.venue_name}>
                        <Text strong>{String(record.venue_id).toUpperCase()}</Text>
                      </Tooltip>
                    ),
                  },
                  { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
                  { title: '获取', dataIndex: 'fetched', key: 'fetched', width: 60, align: 'center' },
                  { title: '入库', dataIndex: 'saved', key: 'saved', width: 60, align: 'center' },
                  { title: '耗时', dataIndex: 'duration', key: 'duration', width: 80 },
                  {
                    title: '错误',
                    dataIndex: 'error',
                    key: 'error',
                    ellipsis: true,
                    render: (e: string) => (e ? <Text type="danger">{e}</Text> : '-'),
                  },
                ]}
              />
            </Card>
          )}

          {task.error_message && (
            <Alert
              type="error"
              message="错误信息"
              description={task.error_message}
              style={{ marginTop: 16 }}
              showIcon
            />
          )}
        </>
      )}
    </Modal>
  )
}

export default TaskDetailModal
