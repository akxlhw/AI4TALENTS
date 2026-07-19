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
  const taskColumns = [
    { title: '任务编码', dataIndex: 'task_code', key: 'task_code', width: 180 },
    { title: '技术领域', dataIndex: 'tech_domain_name', key: 'tech_domain_name' },
    {
      title: '顶刊顶会',
      key: 'venues',
      render: (_: unknown, record: CollectTask) => {
        const sources = record.venue_snapshot || []
        if (sources.length === 0) return <Text type="secondary">-</Text>
        const displayVenues = sources.slice(0, 5)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
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
      title: '时间范围',
      key: 'time_range',
      render: (_: unknown, record: CollectTask) => (
        <Text>
          {record.start_year}年 ~ {record.end_year ? `${record.end_year}年` : '至今'}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const item = getTaskStatusConfig(status)
        return <Badge status={item.status} text={item.label} />
      },
    },
    {
      title: '进度',
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
      title: '采集统计',
      key: 'records',
      render: (_: unknown, record: CollectTask) => (
        <Space direction="vertical" size={0}>
          <Text>论文: {record.total_records}</Text>
          <Text>
            人才: <Text type="success">{record.success_records}</Text>
          </Text>
        </Space>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: CollectTask) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onViewTask(record)}
            />
          </Tooltip>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title="确定取消此任务？"
              onConfirm={() => onCancelTask(record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
          {['completed', 'failed', 'cancelled'].includes(record.status) && (
            <Popconfirm
              title="确定删除此任务记录？"
              description="删除后不可恢复"
              onConfirm={() => onDeleteTask(record.task_id)}
              okText="确定"
              cancelText="取消"
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
            showTotal: (t) => `共 ${t} 个任务`,
            onChange: onPageChange,
          }}
          locale={{ emptyText: <Empty description="暂无采集任务" /> }}
        />
      </Spin>
    </Card>
  )
}

export default TaskListPanel
