import { useState, useEffect, useCallback, useRef } from 'react'
import { semanticColors } from '../../../theme'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  message,
  Popconfirm,
  Badge,
  Progress,
  Descriptions,
  Empty,
  Spin,
  Alert,
  Row,
  Col,
  Statistic,
} from 'antd'
import {
  StopOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import type { OSCollectTask } from '../../../types'
import { formatUTCToLocal } from '../../../utils/datetime'
import { getErrorMessage } from './utils'

const { Text } = Typography

const getTaskStatusConfig = (status: string) => {
  const map: Record<string, { label: string; status: 'success' | 'processing' | 'error' | 'warning' | 'default'; color: string; icon: React.ReactNode }> = {
    pending: { label: '等待中', status: 'default', color: semanticColors.textGray, icon: <ClockCircleOutlined /> },
    running: { label: '运行中', status: 'processing', color: semanticColors.blue, icon: <ThunderboltOutlined /> },
    completed: { label: '已完成', status: 'success', color: semanticColors.green, icon: <CheckCircleOutlined /> },
    failed: { label: '失败', status: 'error', color: semanticColors.red, icon: <CloseCircleOutlined /> },
    cancelled: { label: '已取消', status: 'warning', color: semanticColors.gold, icon: <CloseCircleOutlined /> },
  }
  return map[status] || { label: status, status: 'default', color: semanticColors.textGray, icon: null }
}

const OSCollectTaskSubTab: React.FC = () => {
  const [tasks, setTasks] = useState<OSCollectTask[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<OSCollectTask | null>(null)
  const runningTaskIdsRef = useRef<Set<number>>(new Set())

  const loadTasks = useCallback(
    async (p?: number) => {
      const target = p ?? page
      setLoading(true)
      try {
        const response = await api.openSource.listCollectTasks({ page: target, page_size: 20 })
        const newTasks = response.data.items || []
        setTasks(newTasks)
        setTotal(response.data.total || 0)
        setPage(target)
        const currentRunningIds = new Set<number>(
          newTasks.filter((t: OSCollectTask) => t.status === 'running').map((t: OSCollectTask) => t.task_id)
        )
        runningTaskIdsRef.current = currentRunningIds
      } catch {
        message.error('加载采集任务失败')
      } finally {
        setLoading(false)
      }
    },
    [page]
  )

  useEffect(() => {
    loadTasks(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadTasks])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (tasks.some((t) => t.status === 'running')) {
      const interval = setInterval(() => {
        loadTasks()
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [tasks, loadTasks])

  const handleCancelTask = async (taskId: number) => {
    try {
      await api.openSource.cancelCollectTask(taskId)
      message.success('任务已取消')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, '取消失败'))
    }
  }

  const handleDeleteTask = async (taskId: number) => {
    try {
      await api.openSource.deleteCollectTask(taskId)
      message.success('任务记录已删除')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, '删除失败'))
    }
  }

  const handleViewTask = (task: OSCollectTask) => {
    setSelectedTask(task)
    setDetailModalVisible(true)
  }

  const columns = [
    {
      title: '任务编码',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = getTaskStatusConfig(status)
        return (
          <Tag color={cfg.color} icon={cfg.icon}>
            {cfg.label}
          </Tag>
        )
      },
    },
    {
      title: '当前步骤',
      dataIndex: 'current_step',
      key: 'current_step',
      render: (step: string) => step || '-',
    },
    {
      title: '进度',
      dataIndex: 'progress_percent',
      key: 'progress_percent',
      width: 160,
      render: (percent: number, record: OSCollectTask) => (
        <Progress
          percent={percent}
          size="small"
          status={
            record.status === 'failed'
              ? 'exception'
              : record.status === 'completed'
                ? 'success'
                : 'active'
          }
        />
      ),
    },
    {
      title: '处理记录',
      key: 'records',
      width: 140,
      render: (_: unknown, record: OSCollectTask) => (
        <Text>
          {record.processed_records} / {record.total_records}
        </Text>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: OSCollectTask) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewTask(record)}>
            详情
          </Button>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title="确定取消此任务？"
              onConfirm={() => handleCancelTask(record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
          {['completed', 'failed', 'cancelled'].includes(record.status) && (
            <Popconfirm
              title="确定删除此任务记录？"
              description="删除后不可恢复"
              onConfirm={() => handleDeleteTask(record.task_id)}
              okText="确定"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <Spin spinning={loading}>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="task_id"
          pagination={{
            current: page,
            pageSize: 20,
            total,
            showTotal: t => `共 ${t} 条记录`,
            onChange: p => loadTasks(p),
          }}
          locale={{ emptyText: <Empty description="暂无采集任务" /> }}
        />
      </Spin>

      {/* Task Detail Modal */}
      <Modal
        title="任务详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={
          <Button onClick={() => setDetailModalVisible(false)}>关闭</Button>
        }
        width={700}
      >
        {selectedTask && (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务编码">{selectedTask.task_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge
                  status={getTaskStatusConfig(selectedTask.status).status}
                  text={getTaskStatusConfig(selectedTask.status).label}
                />
              </Descriptions.Item>
              <Descriptions.Item label="当前步骤">{selectedTask.current_step || '-'}</Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress
                  percent={selectedTask.progress_percent}
                  status={
                    selectedTask.status === 'failed'
                      ? 'exception'
                      : selectedTask.status === 'completed'
                        ? 'success'
                        : 'active'
                  }
                  style={{ minWidth: 120 }}
                />
              </Descriptions.Item>
            </Descriptions>

            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={8}>
                <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
                  <Statistic title="总记录数" value={selectedTask.total_records} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
                  <Statistic title="已处理" value={selectedTask.processed_records} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
                  <Statistic
                    title="成功率"
                    value={
                      selectedTask.total_records > 0
                        ? Math.round((selectedTask.processed_records / selectedTask.total_records) * 100)
                        : 0
                    }
                    suffix="%"
                  />
                </Card>
              </Col>
            </Row>

            <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="创建时间">
                  {formatUTCToLocal(selectedTask.created_at)}
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  {formatUTCToLocal(selectedTask.started_at)}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {formatUTCToLocal(selectedTask.completed_at)}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {selectedTask.config_json && (
              <Card title="采集配置" size="small" style={{ marginTop: 16 }}>
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedTask.config_json, null, 2)}
                </pre>
              </Card>
            )}

            {selectedTask.error_message && (
              <Alert
                type="error"
                message="错误信息"
                description={selectedTask.error_message}
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
          </>
        )}
      </Modal>
    </Card>
  )
}

export default OSCollectTaskSubTab
