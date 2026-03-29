/**
 * TaskDetailModal - 任务详情弹窗组件
 *
 * 职责：
 * - 显示任务基本信息
 * - 显示采集统计
 * - 显示时间信息
 * - 显示采集源详情
 * - 显示执行日志
 */
import { Modal, Descriptions, Badge, Progress, Card, Space, Typography, Table, Timeline, Alert, Button, Popconfirm } from 'antd'
import { ReloadOutlined, DeleteOutlined, LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { CollectTask, TaskStatusConfig, CollectModeConfig } from '../../types'

const { Text } = Typography

export interface TaskDetailModalProps {
  visible: boolean
  task: CollectTask | null
  taskStatusMap: Record<string, TaskStatusConfig>
  collectModeMap: Record<string, CollectModeConfig>
  onRefresh: () => void
  onCancelTask: (taskId: number) => void
  onDeleteTask: (taskId: number) => void
  onClose: () => void
}

const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  visible,
  task,
  taskStatusMap,
  collectModeMap,
  onRefresh,
  onCancelTask,
  onDeleteTask,
  onClose,
}) => {
  if (!task) return null

  const renderFooter = () => {
    if (task.status === 'running') {
      return (
        <Space>
          <Button onClick={onRefresh}>
            <ReloadOutlined /> 刷新状态
          </Button>
          <Popconfirm
            title="确定取消此任务？"
            onConfirm={() => {
              onCancelTask(task.task_id)
              onClose()
            }}
            okText="确定"
            cancelText="取消"
          >
            <Button danger>取消任务</Button>
          </Popconfirm>
        </Space>
      )
    }

    if (['completed', 'failed', 'cancelled'].includes(task.status)) {
      return (
        <Space>
          <Button onClick={onClose}>关闭</Button>
          <Popconfirm
            title="确定删除此任务记录？"
            description="删除后不可恢复"
            onConfirm={() => onDeleteTask(task.task_id)}
            okText="确定删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>删除任务</Button>
          </Popconfirm>
        </Space>
      )
    }

    return <Button onClick={onClose}>关闭</Button>
  }

  // Venue status icon mapping
  const venueStatusConfig: Record<string, { icon: React.ReactNode; color: string }> = {
    running: { icon: <LoadingOutlined spin />, color: '#1890ff' },
    completed: { icon: <CheckCircleOutlined />, color: '#52c41a' },
    timeout: { icon: <ClockCircleOutlined />, color: '#faad14' },
    error: { icon: <CloseCircleOutlined />, color: '#ff4d4f' },
  }

  return (
    <Modal
      title="任务详情"
      open={visible}
      onCancel={onClose}
      footer={renderFooter()}
      width={800}
    >
      {/* 基本信息 */}
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="任务编码">{task.task_code}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Badge
            status={taskStatusMap[task.status]?.status}
            text={taskStatusMap[task.status]?.label}
          />
        </Descriptions.Item>
        <Descriptions.Item label="技术要素">{task.tech_element_name}</Descriptions.Item>
        <Descriptions.Item label="采集模式">
          {collectModeMap[task.collect_mode]?.label}
        </Descriptions.Item>
        <Descriptions.Item label="进度" span={2}>
          <Progress
            percent={task.progress_percent}
            status={task.status === 'failed' ? 'exception' : task.status === 'completed' ? 'success' : 'active'}
          />
        </Descriptions.Item>
        <Descriptions.Item label="当前步骤" span={2}>
          {task.status === 'running' ? (
            <Text>
              <LoadingOutlined spin style={{ marginRight: 8 }} />
              {task.current_step || '-'}
            </Text>
          ) : (
            task.current_step || '-'
          )}
        </Descriptions.Item>
      </Descriptions>

      {/* 统计信息 */}
      <Card title="采集统计" size="small" style={{ marginTop: 16 }}>
        <Space size="large">
          <div>
            <Text type="secondary">采集论文</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>{task.total_records}</div>
          </div>
          <div>
            <Text type="secondary">入库人才</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{task.success_records}</div>
          </div>
          <div>
            <Text type="secondary">标准化院校机构</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>{task.skipped_records}</div>
          </div>
          <div>
            <Text type="secondary">标准化作者</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>{task.processed_records}</div>
          </div>
        </Space>
      </Card>

      {/* 时间信息 */}
      <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="触发时间">
            {new Date(task.triggered_at).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {task.started_at ? new Date(task.started_at).toLocaleString() : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="完成时间">
            {task.completed_at ? new Date(task.completed_at).toLocaleString() : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="耗时">
            {task.result_summary?.total_duration || '-'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 采集源详情 */}
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
                dataIndex: 'venue_name',
                key: 'venue_name',
                width: 200,
                ellipsis: true,
              },
              {
                title: '状态',
                dataIndex: 'status',
                key: 'status',
                width: 80,
                render: (status: string) => {
                  const config = venueStatusConfig[status] || { icon: null, color: undefined }
                  return (
                    <Text style={{ color: config.color }}>
                      {config.icon} {status}
                    </Text>
                  )
                },
              },
              {
                title: '获取',
                dataIndex: 'fetched',
                key: 'fetched',
                width: 60,
                align: 'center',
              },
              {
                title: '入库',
                dataIndex: 'saved',
                key: 'saved',
                width: 60,
                align: 'center',
              },
              {
                title: '耗时',
                dataIndex: 'duration',
                key: 'duration',
                width: 80,
              },
              {
                title: '错误',
                dataIndex: 'error',
                key: 'error',
                ellipsis: true,
                render: (error: string) => error ? <Text type="danger">{error}</Text> : '-',
              },
            ]}
          />
        </Card>
      )}

      {/* 执行日志 */}
      {task.execution_logs && task.execution_logs.length > 0 && (
        <Card title="执行日志" size="small" style={{ marginTop: 16 }}>
          <Timeline
            items={task.execution_logs.map((log) => ({
              color: log.level === 'error' ? 'red' : log.level === 'warning' ? 'orange' : 'blue',
              children: (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text strong={log.level === 'error'}>{log.level.toUpperCase()}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </Text>
                  </div>
                  <div>{log.message}</div>
                  {log.details != null && (
                    <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                      {typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details)}
                    </div>
                  )}
                </div>
              ),
            }))}
          />
        </Card>
      )}

      {/* 错误信息 */}
      {task.error_message && (
        <Alert
          type="error"
          message="错误信息"
          description={task.error_message}
          style={{ marginTop: 16 }}
          showIcon
        />
      )}
    </Modal>
  )
}

export default TaskDetailModal
