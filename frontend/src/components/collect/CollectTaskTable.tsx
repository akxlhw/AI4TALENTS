/**
 * CollectTaskTable - 采集任务表格组件
 *
 * 职责：
 * - 显示采集任务列表
 * - 显示任务状态、进度
 * - 提供查看、取消、删除操作
 */
import { Table, Typography, Space, Button, Tooltip, Badge, Progress, Empty, Popconfirm } from 'antd'
import { EyeOutlined, StopOutlined, DeleteOutlined } from '@ant-design/icons'
import type { CollectTask, TaskStatusConfig } from '../../types'

const { Text } = Typography

export interface CollectTaskTableProps {
  data: CollectTask[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  taskStatusMap: Record<string, TaskStatusConfig>
  onViewTask: (task: CollectTask) => void
  onCancelTask: (taskId: number) => void
  onDeleteTask: (taskId: number) => void
  onPageChange: (page: number) => void
}

const CollectTaskTable: React.FC<CollectTaskTableProps> = ({
  data,
  loading,
  total,
  page,
  pageSize,
  taskStatusMap,
  onViewTask,
  onCancelTask,
  onDeleteTask,
  onPageChange,
}) => {
  const columns = [
    {
      title: '任务编码',
      dataIndex: 'task_code',
      key: 'task_code',
      width: 220,
    },
    {
      title: '技术要素',
      dataIndex: 'tech_element_name',
      key: 'tech_element_name',
    },
    {
      title: '时间范围',
      key: 'time_range',
      render: (_: unknown, record: CollectTask) => (
        <Text>{record.start_year}年 ~ {record.end_year ? `${record.end_year}年` : '至今'}</Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const item = taskStatusMap[status] || { label: status, color: 'default', status: 'default' as const }
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
          status={record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '采集统计',
      key: 'records',
      render: (_: unknown, record: CollectTask) => (
        <Space direction="vertical" size={0}>
          <Text>论文: {record.total_records}</Text>
          <Text>人才: <Text type="success">{record.success_records}</Text></Text>
          <Text>院校机构: {record.skipped_records}</Text>
        </Space>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => new Date(date).toLocaleString(),
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
          {record.status === 'running' && (
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
    <Table
      dataSource={data}
      columns={columns}
      rowKey="task_id"
      loading={loading}
      pagination={{
        current: page,
        pageSize,
        total,
        showTotal: (t) => `共 ${t} 个任务`,
        onChange: onPageChange,
      }}
      locale={{
        emptyText: <Empty description="暂无采集任务" />,
      }}
    />
  )
}

export default CollectTaskTable
