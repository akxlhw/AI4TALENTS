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
import { useTranslation } from 'react-i18next'
import { api } from '../../../services/api'
import '../../../i18n/namespaces/system-config'
import type { OSCollectTask } from '../../../types'
import { formatDBLocal, formatUTCToLocal } from '../../../utils/datetime'
import { getErrorMessage } from './utils'

const { Text } = Typography

// Status labels are i18n keys (systemConfig.osTasks.status.*) resolved with
// t() at render time; this map only carries badge/color/icon presentation.
const getTaskStatusConfig = (status: string) => {
  const map: Record<
    string,
    {
      status: 'success' | 'processing' | 'error' | 'warning' | 'default'
      color: string
      icon: React.ReactNode
    }
  > = {
    pending: { status: 'default', color: semanticColors.textGray, icon: <ClockCircleOutlined /> },
    running: { status: 'processing', color: semanticColors.blue, icon: <ThunderboltOutlined /> },
    completed: { status: 'success', color: semanticColors.green, icon: <CheckCircleOutlined /> },
    failed: { status: 'error', color: semanticColors.red, icon: <CloseCircleOutlined /> },
    cancelled: { status: 'warning', color: semanticColors.gold, icon: <CloseCircleOutlined /> },
    rate_limited: {
      status: 'warning',
      color: semanticColors.orange,
      icon: <ClockCircleOutlined />,
    },
  }
  return map[status] || { status: 'default' as const, color: semanticColors.textGray, icon: null }
}

const OSCollectTaskSubTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
  const [tasks, setTasks] = useState<OSCollectTask[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<OSCollectTask | null>(null)
  const runningTaskIdsRef = useRef<Set<number>>(new Set())

  const loadTasks = useCallback(
    async (p?: number, silent = false) => {
      const target = p ?? page
      // Silent mode (auto-refresh) skips the Spin overlay so polling doesn't
      // flash the whole table every few seconds while tasks are running.
      if (!silent) setLoading(true)
      try {
        const response = await api.openSource.listCollectTasks({
          page: target,
          page_size: pageSize,
        })
        const newTasks = response.data.items || []
        setTasks(newTasks)
        setTotal(response.data.total || 0)
        setPage(target)
        const currentRunningIds = new Set<number>(
          newTasks
            .filter((t: OSCollectTask) => t.status === 'running')
            .map((t: OSCollectTask) => t.task_id)
        )
        runningTaskIdsRef.current = currentRunningIds
      } catch {
        message.error(t('osTasks.messages.loadFailed'))
      } finally {
        if (!silent) setLoading(false)
      }
    },
    [page, pageSize, t]
  )

  useEffect(() => {
    loadTasks(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadTasks])

  // Auto-refresh while any visible task is running. Deps on the boolean (not
  // the tasks array) keep the interval from being torn down on every poll.
  const hasRunning = tasks.some(t => t.status === 'running')
  useEffect(() => {
    if (!hasRunning) return
    const interval = setInterval(() => {
      loadTasks(undefined, true)
    }, 3000)
    return () => clearInterval(interval)
  }, [hasRunning, loadTasks])

  const handleCancelTask = async (taskId: number) => {
    try {
      await api.openSource.cancelCollectTask(taskId)
      message.success(t('osTasks.messages.cancelled'))
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, t('osTasks.messages.cancelFailed')))
    }
  }

  const handleDeleteTask = async (taskId: number) => {
    try {
      await api.openSource.deleteCollectTask(taskId)
      message.success(t('osTasks.messages.deleted'))
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, t('osTasks.messages.deleteFailed')))
    }
  }

  const handleViewTask = (task: OSCollectTask) => {
    setSelectedTask(task)
    setDetailModalVisible(true)
  }

  const columns = [
    {
      title: t('osTasks.columns.taskCode'),
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: t('osTasks.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = getTaskStatusConfig(status)
        return (
          <Tag color={cfg.color} icon={cfg.icon}>
            {t(`osTasks.status.${status}`, { defaultValue: status })}
          </Tag>
        )
      },
    },
    {
      title: t('osTasks.columns.currentStep'),
      dataIndex: 'current_step',
      key: 'current_step',
      render: (step: string) => step || '-',
    },
    {
      title: t('osTasks.columns.progress'),
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
      title: t('osTasks.columns.records'),
      key: 'records',
      width: 140,
      render: (_: unknown, record: OSCollectTask) => (
        <Text>
          {record.processed_records} / {record.total_records}
        </Text>
      ),
    },
    {
      title: t('osTasks.columns.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatDBLocal(date),
    },
    {
      title: t('osTasks.columns.actions'),
      key: 'actions',
      width: 150,
      render: (_: unknown, record: OSCollectTask) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewTask(record)}
          >
            {t('common:actions.detail')}
          </Button>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title={t('osTasks.cancelConfirm')}
              onConfirm={() => handleCancelTask(record.task_id)}
              okText={t('common:actions.confirm')}
              cancelText={t('common:actions.cancel')}
            >
              <Button type="link" size="small" danger icon={<StopOutlined />}>
                {t('common:actions.cancel')}
              </Button>
            </Popconfirm>
          )}
          {['completed', 'failed', 'cancelled', 'rate_limited'].includes(record.status) && (
            <Popconfirm
              title={t('osTasks.deleteConfirm')}
              description={t('osTasks.deleteIrreversible')}
              onConfirm={() => handleDeleteTask(record.task_id)}
              okText={t('common:actions.confirm')}
              cancelText={t('common:actions.cancel')}
              okButtonProps={{ danger: true }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                {t('common:actions.delete')}
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
            pageSize,
            total,
            showTotal: count => t('common:pagination.total', { n: count }),
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            // Single entry point: antd fires BOTH onShowSizeChange and
            // onChange on a size change, and two handlers racing setState
            // caused page/pageSize to fight. Routing everything through one
            // handler keeps exactly one request per interaction.
            onChange: (p, size) => {
              if (size !== pageSize) {
                setPage(1)
                setPageSize(size)
              } else {
                loadTasks(p)
              }
            },
          }}
          locale={{ emptyText: <Empty description={t('osTasks.empty')} /> }}
        />
      </Spin>

      {/* Task Detail Modal */}
      <Modal
        title={t('osTasks.detail.title')}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={
          <Button onClick={() => setDetailModalVisible(false)}>{t('common:actions.close')}</Button>
        }
        width={700}
      >
        {selectedTask && (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label={t('osTasks.detail.taskCode')}>
                {selectedTask.task_name}
              </Descriptions.Item>
              <Descriptions.Item label={t('osTasks.detail.status')}>
                <Badge
                  status={getTaskStatusConfig(selectedTask.status).status}
                  text={t(`osTasks.status.${selectedTask.status}`, {
                    defaultValue: selectedTask.status,
                  })}
                />
              </Descriptions.Item>
              <Descriptions.Item label={t('osTasks.detail.currentStep')}>
                {selectedTask.current_step || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('osTasks.detail.progress')}>
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
                  <Statistic
                    title={t('osTasks.detail.totalRecords')}
                    value={selectedTask.total_records}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
                  <Statistic
                    title={t('osTasks.detail.processed')}
                    value={selectedTask.processed_records}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" bordered={false} style={{ background: semanticColors.bgGray }}>
                  <Statistic
                    title={t('osTasks.detail.successRate')}
                    value={
                      selectedTask.total_records > 0
                        ? Math.round(
                            (selectedTask.processed_records / selectedTask.total_records) * 100
                          )
                        : 0
                    }
                    suffix="%"
                  />
                </Card>
              </Col>
            </Row>

            <Card title={t('osTasks.detail.timeInfo')} size="small" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label={t('osTasks.detail.createdAt')}>
                  {formatDBLocal(selectedTask.created_at)}
                </Descriptions.Item>
                <Descriptions.Item label={t('osTasks.detail.startedAt')}>
                  {formatUTCToLocal(selectedTask.started_at)}
                </Descriptions.Item>
                <Descriptions.Item label={t('osTasks.detail.completedAt')}>
                  {formatUTCToLocal(selectedTask.completed_at)}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {selectedTask.config_json && (
              <Card title={t('osTasks.detail.config')} size="small" style={{ marginTop: 16 }}>
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(selectedTask.config_json, null, 2)}
                </pre>
              </Card>
            )}

            {selectedTask.error_message && (
              <Alert
                type="error"
                message={t('osTasks.detail.errorMessage')}
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
