import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Popconfirm,
  Badge,
  Progress,
  Tooltip,
  Empty,
  Spin,
} from 'antd'
import { StopOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import '../../../../i18n/namespaces/system-config'
import { getTaskStatusConfig } from '../../../../constants'
import type { CollectTask } from '../../../../types'
import { formatUTCToLocal } from '../../../../utils/datetime'

const { Text } = Typography

interface TaskListPanelProps {
  loading: boolean
  tasks: CollectTask[]
  taskPage: number
  taskTotal: number
  onPageChange: (page: number) => void
  onViewTask: (task: CollectTask) => void
  onCancelTask: (taskId: number) => void
  onDeleteTask: (taskId: number) => void
}

const TaskListPanel: React.FC<TaskListPanelProps> = ({
  loading,
  tasks,
  taskPage,
  taskTotal,
  onPageChange,
  onViewTask,
  onCancelTask,
  onDeleteTask,
}) => {
  const { t } = useTranslation(['systemConfig', 'common'])

  const yearLabel = (year: number | null | undefined) =>
    year == null ? t('collectConfig.taskList.present') : t('collectConfig.taskList.year', { year })

  const taskColumns = [
    {
      title: t('collectConfig.taskList.colTaskCode'),
      dataIndex: 'task_code',
      key: 'task_code',
      width: 180,
    },
    {
      title: t('collectConfig.taskList.colTechDomain'),
      dataIndex: 'tech_domain_name',
      key: 'tech_domain_name',
    },
    {
      title: t('collectConfig.taskList.colVenues'),
      key: 'venues',
      render: (_: unknown, record: CollectTask) => {
        const sources = record.venue_snapshot || []
        if (sources.length === 0) return <Text type="secondary">-</Text>
        const displayVenues = sources.slice(0, 5)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map(v => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {sources.length > 5 && <Tag>+{sources.length - 5}</Tag>}
          </Space>
        )
      },
    },
    {
      title: t('collectConfig.taskList.colTimeRange'),
      key: 'time_range',
      render: (_: unknown, record: CollectTask) => (
        <Text>
          {t('collectConfig.taskList.timeRange', {
            start: yearLabel(record.start_year),
            end: yearLabel(record.end_year),
          })}
        </Text>
      ),
    },
    {
      title: t('collectConfig.taskList.colStatus'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const item = getTaskStatusConfig(status)
        return (
          <Badge
            status={item.status}
            text={t(`collectConfig.status.${status}`, { defaultValue: status })}
          />
        )
      },
    },
    {
      title: t('collectConfig.taskList.colProgress'),
      dataIndex: 'progress_percent',
      key: 'progress_percent',
      width: 150,
      render: (percent: number, record: CollectTask) => (
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
      title: t('collectConfig.taskList.colStats'),
      key: 'records',
      render: (_: unknown, record: CollectTask) => (
        <Space direction="vertical" size={0}>
          <Text>{t('collectConfig.taskList.papers', { n: record.total_records })}</Text>
          <Text>
            {t('collectConfig.taskList.talents')}:{' '}
            <Text type="success">{record.success_records}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: t('collectConfig.taskList.colTriggeredAt'),
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: t('collectConfig.taskList.colActions'),
      key: 'actions',
      width: 150,
      render: (_: unknown, record: CollectTask) => (
        <Space>
          <Tooltip title={t('collectConfig.taskList.viewDetail')}>
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewTask(record)}
            />
          </Tooltip>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title={t('collectConfig.taskList.cancelConfirm')}
              onConfirm={() => onCancelTask(record.task_id)}
              okText={t('common:actions.confirm')}
              cancelText={t('common:actions.cancel')}
            >
              <Button type="link" size="small" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
          {['completed', 'failed', 'cancelled'].includes(record.status) && (
            <Popconfirm
              title={t('collectConfig.taskList.deleteConfirm')}
              description={t('collectConfig.taskList.deleteIrreversible')}
              onConfirm={() => onDeleteTask(record.task_id)}
              okText={t('common:actions.confirm')}
              cancelText={t('common:actions.cancel')}
              okButtonProps={{ danger: true }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
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
          columns={taskColumns}
          rowKey="task_id"
          pagination={{
            current: taskPage,
            pageSize: 10,
            total: taskTotal,
            showTotal: count => t('collectConfig.taskList.total', { n: count }),
            onChange: onPageChange,
          }}
          locale={{
            emptyText: <Empty description={t('collectConfig.taskList.empty')} />,
          }}
        />
      </Spin>
    </Card>
  )
}

export default TaskListPanel
